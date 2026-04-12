#!/usr/bin/env python3
"""
kb_lint.py — Run a health check over the knowledge base wiki.

Usage:
    python kb_lint.py [--vault /mnt/d/core] [--fix]

Checks:
- Orphaned concept articles (no backlinks from other articles)
- Concepts referenced in sources but missing from wiki
- Potential inconsistencies or contradictions across articles
- Suggests new article candidates based on concept co-occurrence
"""

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

import anthropic

from kb_log import append_log

VAULT = Path("/mnt/d/core")
MODEL = "claude-sonnet-4-6"

LINT_SYSTEM = """You are a knowledge base auditor. You check wikis for quality issues.

Given a set of wiki articles, you identify:
1. ORPHANS: Articles with no [[wikilinks]] pointing to them from other articles
2. GAPS: Concepts mentioned in source documents but lacking a dedicated wiki article
3. INCONSISTENCIES: Claims in different articles that contradict each other
4. NEW_ARTICLES: Topics that appear frequently across sources but have no article yet

Respond with JSON:
{
  "orphans": ["slug1", "slug2"],
  "gaps": ["concept mentioned but not in wiki"],
  "inconsistencies": [{"articles": ["slug1", "slug2"], "issue": "description"}],
  "new_article_candidates": [{"slug": "suggested-slug", "reason": "why this article is needed"}],
  "health_score": 0-100,
  "summary": "one paragraph summary of wiki health"
}"""


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def find_wikilinks(text: str) -> set[str]:
    return set(re.findall(r'\[\[([^\]|#]+)', text))


def find_orphans(vault: Path) -> list[str]:
    concepts_dir = vault / "wiki" / "concepts"
    concepts = {f.stem for f in concepts_dir.glob("*.md")}
    referenced = set()

    # Collect all wikilinks across all wiki articles
    for f in concepts_dir.glob("*.md"):
        links = find_wikilinks(read_file(f))
        referenced.update(links)

    # Also check _index.md
    referenced.update(find_wikilinks(read_file(vault / "wiki" / "_index.md")))

    orphans = []
    for slug in concepts:
        # Check if any file links to this concept
        if not any(slug in ref or slug in ref.replace("concepts/", "") for ref in referenced):
            orphans.append(slug)
    return orphans


def run_llm_audit(client: anthropic.Anthropic, vault: Path) -> dict:
    concepts_dir = vault / "wiki" / "concepts"
    concept_files = list(concepts_dir.glob("*.md"))

    if not concept_files:
        return {
            "orphans": [], "gaps": [], "inconsistencies": [],
            "new_article_candidates": [],
            "health_score": 0,
            "summary": "Wiki is empty — no articles to audit."
        }

    # Build a compact representation of all articles
    articles_text = ""
    for f in concept_files[:20]:  # Limit to 20 articles per call
        content = read_file(f)[:1500]
        articles_text += f"\n\n### {f.stem}\n{content}"

    # Sample of raw sources
    raw_samples = ""
    for f in list((vault / "raw").rglob("*.md"))[:5]:
        raw_samples += f"\n\n[Source: {f.stem}]\n{read_file(f)[:500]}"

    prompt = f"""Audit this knowledge base wiki.

Wiki articles:{articles_text}

Sample sources (for gap detection):{raw_samples if raw_samples else "(no sources yet)"}

Identify orphans, gaps, inconsistencies, and new article candidates. Return JSON."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=LINT_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    import json
    return json.loads(text)


def write_lint_report(vault: Path, structural_orphans: list[str], audit: dict) -> Path:
    today = date.today()
    report_path = vault / "outputs" / f"lint_report_{today}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    health = audit.get("health_score", "?")
    color = "🟢" if health >= 80 else "🟡" if health >= 50 else "🔴"

    lines = [
        f"# Wiki Health Report — {today}",
        f"\n**Health Score**: {color} {health}/100",
        f"\n{audit.get('summary', '')}",
        "\n---",
        "\n## Orphaned Articles (no incoming links)",
    ]

    orphans = list(set(structural_orphans + audit.get("orphans", [])))
    if orphans:
        for slug in orphans:
            lines.append(f"- [[concepts/{slug}]] — consider linking from related articles")
    else:
        lines.append("- None found ✓")

    lines.append("\n## Concept Gaps (referenced but no article)")
    gaps = audit.get("gaps", [])
    if gaps:
        for gap in gaps:
            lines.append(f"- **{gap}** — create `wiki/concepts/{gap.lower().replace(' ', '-')}.md`")
    else:
        lines.append("- None found ✓")

    lines.append("\n## Inconsistencies")
    inconsistencies = audit.get("inconsistencies", [])
    if inconsistencies:
        for issue in inconsistencies:
            articles = ", ".join(f"[[concepts/{a}]]" for a in issue.get("articles", []))
            lines.append(f"- {articles}: {issue.get('issue', '')}")
    else:
        lines.append("- None found ✓")

    lines.append("\n## New Article Candidates")
    candidates = audit.get("new_article_candidates", [])
    if candidates:
        for c in candidates:
            lines.append(f"- **[[concepts/{c['slug']}]]** — {c.get('reason', '')}")
    else:
        lines.append("- None suggested")

    lines.append(f"\n---\n*Generated by kb_lint.py at {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def update_meta(vault: Path) -> None:
    meta_path = vault / "wiki" / "_meta.md"
    if not meta_path.exists():
        return
    text = meta_path.read_text(encoding="utf-8")
    text = re.sub(r"- \*\*Last lint\*\*: .*", f"- **Last lint**: {datetime.now().strftime('%Y-%m-%d %H:%M')}", text)
    meta_path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Health check the knowledge base wiki")
    parser.add_argument("--vault", default=str(VAULT), help="Vault root path")
    parser.add_argument("--model", default=MODEL, help="Claude model to use")
    args = parser.parse_args()

    vault = Path(args.vault)
    client = anthropic.Anthropic()

    print("Running structural checks ...")
    structural_orphans = find_orphans(vault)
    if structural_orphans:
        print(f"Found {len(structural_orphans)} orphan(s): {', '.join(structural_orphans)}")

    print("Running LLM audit ...")
    try:
        audit = run_llm_audit(client, vault)
    except Exception as e:
        print(f"LLM audit failed: {e}", file=sys.stderr)
        audit = {"orphans": [], "gaps": [], "inconsistencies": [], "new_article_candidates": [],
                 "health_score": "?", "summary": f"LLM audit failed: {e}"}

    report_path = write_lint_report(vault, structural_orphans, audit)
    update_meta(vault)
    health = audit.get("health_score", "?")
    append_log(vault, "lint", f"Health score {health}/100")

    print(f"\nHealth score: {audit.get('health_score', '?')}/100")
    print(f"Report saved: {report_path}")
    print(f"Open in Obsidian: {report_path.relative_to(vault)}")


if __name__ == "__main__":
    main()
