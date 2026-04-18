#!/usr/bin/env python3
"""
kb_compile.py — Incrementally compile new raw/ sources into the wiki.

Usage:
    python kb_compile.py [--vault /mnt/d/core] [--model claude-opus-4-6] [--force]

Claude reads each uncompiled raw source, extracts concepts, and creates/updates
wiki/concepts/*.md articles with backlinks. The _index.md is regenerated each run.
"""

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

import anthropic

from kb_log import append_log
from kb_state import mark_compiled_hash, needs_recompile, record_cost

VAULT = Path("/mnt/d/core")
MODEL = "claude-sonnet-4-6"

COMPILE_SYSTEM = """You are a knowledge base compiler. You read source documents and maintain a wiki of concept articles.

Wiki conventions:
- Each concept has its own file in wiki/concepts/<concept-slug>.md
- Concept files use Obsidian [[wikilinks]] to link to related concepts
- Every concept file has frontmatter: title, tags, sources (list of raw/ paths)
- The _index.md has one-line summaries of every concept and every source

When given a source document, you:
1. Identify 2-6 key concepts it covers
2. For each concept, return the full article content (create or update as needed)
3. Return an UPDATE_INDEX action with the updated _index.md content

Respond ONLY with JSON in this exact format:
{
  "concepts": [
    {
      "slug": "concept-slug",
      "title": "Concept Title",
      "content": "full markdown content with frontmatter"
    }
  ],
  "index_additions": [
    "- [[concepts/concept-slug]] — one-line summary"
  ],
  "source_summary": "one-line summary of this source document"
}"""


def read_file(path: Path) -> str:
    try: return path.read_text(encoding="utf-8")
    except Exception: return ""


def get_uncompiled_sources(vault: Path) -> list[Path]:
    """Return sources that are new (compiled: false) or changed since last compile."""
    sources = []
    for md in (vault / "raw").rglob("*.md"):
        if needs_recompile(vault, md): sources.append(md)
    return sources


def get_existing_concepts(vault: Path) -> dict[str, str]:
    """Return {slug: content} for all existing concept articles."""
    concepts_dir = vault / "wiki" / "concepts"
    result = {}
    for f in concepts_dir.glob("*.md"):
        result[f.stem] = read_file(f)
    return result


def compile_source(client: anthropic.Anthropic, source_path: Path, vault: Path, existing_concepts: dict) -> dict:
    source_content = read_file(source_path)

    # Build context: existing index + relevant existing concepts
    index_content = read_file(vault / "wiki" / "_index.md")

    # List existing concepts so Claude knows what already exists
    existing_list = "\n".join(f"- {slug}" for slug in existing_concepts.keys()) if existing_concepts else "(none yet)"

    prompt = f"""Existing wiki concepts:
{existing_list}

Current _index.md:
{index_content[:3000]}

New source to compile ({source_path.relative_to(vault)}):
{source_content[:8000]}

Compile this source into the wiki. Update or create concept articles as needed.
Return JSON as specified."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=16384,
        system=COMPILE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    usage = response.usage
    record_cost(vault, "compile", usage.input_tokens, usage.output_tokens)

    text = response.content[0].text.strip()
    # Extract JSON from response (handle markdown code blocks)
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    import json
    return json.loads(text)


def apply_concept(vault: Path, concept: dict) -> None:
    concepts_dir = vault / "wiki" / "concepts"
    slug = concept["slug"]
    path = concepts_dir / f"{slug}.md"
    path.write_text(concept["content"], encoding="utf-8")
    print(f"  Wrote: wiki/concepts/{slug}.md")


def update_index(vault: Path, source_path: Path, source_summary: str, index_additions: list[str]) -> None:
    index_path = vault / "wiki" / "_index.md"
    text = index_path.read_text(encoding="utf-8")

    rel_path = source_path.relative_to(vault)
    source_link = f"- [[{rel_path.with_suffix('')}]] — {source_summary} ({date.today()})"

    # Add concept entries
    for addition in index_additions:
        if addition.strip() and addition.strip() not in text:
            text = text.replace("<!-- Claude maintains this section. Format: - [[concept]] — one-line summary -->",
                                f"<!-- Claude maintains this section. Format: - [[concept]] — one-line summary -->\n{addition}")

    # Add source entry (skip if already present)
    if source_link not in text:
        text = re.sub(
            r"(## Recent Sources\n)",
            rf"\1{source_link}\n",
            text,
            count=1,
        )

    # Update stats
    concept_count = len(list((vault / "wiki" / "concepts").glob("*.md")))
    source_count = len(list((vault / "raw").rglob("*.md")))
    text = re.sub(r"Last compiled: .*", f"Last compiled: {datetime.now().strftime('%Y-%m-%d %H:%M')}", text)
    text = re.sub(r"Sources: \d+", f"Sources: {source_count}", text)
    text = re.sub(r"Concepts: \d+", f"Concepts: {concept_count}", text)

    index_path.write_text(text, encoding="utf-8")


def mark_compiled(vault: Path, source_path: Path) -> None:
    text = source_path.read_text(encoding="utf-8")
    text = text.replace("compiled: false", "compiled: true")
    source_path.write_text(text, encoding="utf-8")
    mark_compiled_hash(vault, source_path)


def update_meta(vault: Path) -> None:
    meta_path = vault / "wiki" / "_meta.md"
    if not meta_path.exists(): return
    text = meta_path.read_text(encoding="utf-8")
    concept_count = len(list((vault / "wiki" / "concepts").glob("*.md")))
    source_count = len(list((vault / "raw").rglob("*.md")))
    text = re.sub(r"- \*\*Sources ingested\*\*: \d+", f"- **Sources ingested**: {source_count}", text)
    text = re.sub(r"- \*\*Concepts compiled\*\*: \d+", f"- **Concepts compiled**: {concept_count}", text)
    text = re.sub(r"- \*\*Last compile\*\*: .*", f"- **Last compile**: {datetime.now().strftime('%Y-%m-%d %H:%M')}", text)
    meta_path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Compile new raw sources into the wiki")
    parser.add_argument("--vault", default=str(VAULT), help="Vault root path")
    parser.add_argument("--model", default=MODEL, help="Claude model to use")
    parser.add_argument("--force", action="store_true", help="Recompile already-compiled sources")
    args = parser.parse_args()

    vault = Path(args.vault)
    client = anthropic.Anthropic()

    if args.force:
        # Mark all sources as uncompiled and clear hashes
        from kb_state import load_state, save_state
        state = load_state(vault)
        state["compiled_hashes"] = {}
        save_state(vault, state)
        for md in (vault / "raw").rglob("*.md"):
            text = md.read_text(encoding="utf-8")
            if "compiled: true" in text:
                md.write_text(text.replace("compiled: true", "compiled: false"), encoding="utf-8")

    sources = get_uncompiled_sources(vault)
    if not sources:
        print("No new sources to compile.")
        return

    print(f"Found {len(sources)} source(s) to compile.")
    existing_concepts = get_existing_concepts(vault)

    for i, source in enumerate(sources, 1):
        print(f"\n[{i}/{len(sources)}] Compiling: {source.relative_to(vault)}")
        try:
            result = compile_source(client, source, vault, existing_concepts)

            for concept in result.get("concepts", []):
                apply_concept(vault, concept)
                existing_concepts[concept["slug"]] = concept["content"]

            update_index(vault, source, result.get("source_summary", ""), result.get("index_additions", []))
            mark_compiled(vault, source)

            concept_slugs = [c["slug"] for c in result.get("concepts", [])]
            log_title = f"{source.stem} → {', '.join(concept_slugs[:3])}"
            operation = "compile-note" if source.parts[-2] == "notes" else "compile"
            append_log(vault, operation, log_title)
            print(f"  Compiled successfully.")

        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            continue

    update_meta(vault)

    from kb_state import load_state
    state = load_state(vault)
    costs = state["costs"]
    print(f"\nDone. Wiki updated at {vault}/wiki/")
    print(f"Cumulative API cost: ${costs['total_cost_usd']:.4f} "
          f"({costs['total_input_tokens']:,} in / {costs['total_output_tokens']:,} out tokens)")


if __name__ == "__main__":
    main()
