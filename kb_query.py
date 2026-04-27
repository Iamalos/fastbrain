#!/usr/bin/env python3
"""
kb_query.py — Ask a question against your knowledge base wiki.

Usage:
    python kb_query.py "What are the key tradeoffs between X and Y?" [--format md|marp|bullet]
    python kb_query.py "Summarize everything about topic Z" --file-into-wiki

Claude reads _index.md to find relevant articles, reads them, then generates
a structured answer saved to outputs/queries/.
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

from kb_log import append_log
from kb_state import record_cost

VAULT = Path("/mnt/d/core")
MODEL = "anthropic/claude-sonnet-4-6"

QUERY_SYSTEM = """You are a knowledge base research assistant. You answer questions by reasoning over a wiki of markdown articles.

Process:
1. Read the _index.md to identify which concept articles are relevant
2. Read those articles in full
3. Synthesize a thorough, well-structured answer

Your answers are saved as markdown files the user views in Obsidian, so:
- Use proper markdown formatting with headers
- Use [[wikilinks]] to reference wiki concepts when relevant
- Be specific and cite sources where possible
- End with a "## Further Reading" section listing relevant concept articles

For Marp format: add "marp: true" frontmatter and use "---" slide separators.
For bullet format: use nested bullet points only, no prose paragraphs."""

INDEX_ANALYSIS_PROMPT = """Given this _index.md and the user's question, list which concept articles to read (by slug).
Return ONLY a JSON array of slugs, e.g.: ["concept-a", "concept-b"]

Question: {question}

_index.md:
{index}"""


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:60]


def find_relevant_concepts(client: OpenAI, question: str, vault: Path) -> list[str]:
    index_content = read_file(vault / "wiki" / "_index.md")
    if not index_content.strip() or "Concepts: 0" in index_content:
        return []

    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": INDEX_ANALYSIS_PROMPT.format(question=question, index=index_content[:4000])
        }]
    )

    text = response.choices[0].message.content.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    import json
    try:
        return json.loads(text)
    except Exception:
        return []


def build_context(vault: Path, slugs: list[str]) -> str:
    parts = []
    concepts_dir = vault / "wiki" / "concepts"
    for slug in slugs:
        path = concepts_dir / f"{slug}.md"
        if path.exists():
            parts.append(f"### {slug}\n{read_file(path)}")
    return "\n\n---\n\n".join(parts)


def generate_answer(client: OpenAI, question: str, context: str, fmt: str, model: str, vault: Path = None) -> str:
    format_instruction = {
        "md": "Write a detailed markdown article answering the question.",
        "marp": "Write a Marp slide deck (marp: true frontmatter, --- slide separators) answering the question.",
        "bullet": "Answer using only nested bullet points, no prose.",
    }.get(fmt, "Write a detailed markdown article.")

    prompt = f"""{format_instruction}

Question: {question}

Relevant knowledge base articles:
{context if context else "(no matching articles found — answer from general knowledge and note the wiki lacks coverage on this topic)"}"""

    response = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": QUERY_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    if vault:
        record_cost(vault, "query", response.usage.prompt_tokens, response.usage.completion_tokens)
    return response.choices[0].message.content


def save_output(vault: Path, question: str, answer: str, fmt: str, file_into_wiki: bool) -> Path:
    slug = slugify(question)
    today = date.today()
    ext = ".md"

    if file_into_wiki:
        out_path = vault / "wiki" / "concepts" / f"q-{slug}.md"
    else:
        out_path = vault / "outputs" / "queries" / f"{today}-{slug}{ext}"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    header = f"""---
question: "{question}"
date: "{today}"
format: {fmt}
type: query_output
---

# {question}

"""
    out_path.write_text(header + answer, encoding="utf-8")
    return out_path


def update_meta(vault: Path) -> None:
    from datetime import datetime
    meta_path = vault / "wiki" / "_meta.md"
    if not meta_path.exists():
        return
    text = meta_path.read_text(encoding="utf-8")
    text = re.sub(r"- \*\*Last query\*\*: .*", f"- **Last query**: {datetime.now().strftime('%Y-%m-%d %H:%M')}", text)
    meta_path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Query the knowledge base wiki")
    parser.add_argument("question", help="Question to answer")
    parser.add_argument("--format", default="md", choices=["md", "marp", "bullet"], help="Output format")
    parser.add_argument("--vault", default=str(VAULT), help="Vault root path")
    parser.add_argument("--model", default=MODEL, help="Claude model to use")
    parser.add_argument("--file-into-wiki", action="store_true", help="Save answer to wiki/concepts/ instead of outputs/")
    args = parser.parse_args()

    vault = Path(args.vault)
    client = OpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url="https://openrouter.ai/api/v1",
    )

    print(f"Question: {args.question}")
    print("Finding relevant articles ...")

    slugs = find_relevant_concepts(client, args.question, vault)
    if slugs:
        print(f"Reading articles: {', '.join(slugs)}")
    else:
        print("No matching articles found — answering from general knowledge.")

    context = build_context(vault, slugs)

    print("Generating answer ...")
    answer = generate_answer(client, args.question, context, args.format, args.model, vault)

    out_path = save_output(vault, args.question, answer, args.format, args.file_into_wiki)
    update_meta(vault)
    wiki_flag = " [→wiki]" if args.file_into_wiki else ""
    append_log(vault, "query", args.question[:80] + wiki_flag)

    from kb_state import load_state
    costs = load_state(vault)["costs"]
    print(f"\nAnswer saved: {out_path}")
    print(f"Open in Obsidian: {out_path.relative_to(vault)}")
    print(f"Cumulative API cost: ${costs['total_cost_usd']:.4f}")


if __name__ == "__main__":
    main()
