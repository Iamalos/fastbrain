#!/usr/bin/env python3
"""
kb_ingest.py — Clip a web URL and save it to the knowledge base raw/ directory.

Usage:
    python kb_ingest.py <url> [--tags tag1,tag2] [--vault /mnt/d/core]
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import anthropic

from kb_log import append_log

VAULT = Path("/mnt/d/core")
MODEL = "claude-sonnet-4-6"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:80]


def fetch_as_markdown(url: str) -> tuple[str, str]:
    """Fetch URL via Playwright and return (title, markdown_content)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = page.title() or "Untitled"

        # Extract main content — prefer <article>, <main>, fall back to <body>
        content = page.evaluate("""() => {
            const sel = ['article', 'main', '[role="main"]', '.post-content',
                         '.article-content', '.entry-content', 'body'];
            for (const s of sel) {
                const el = document.querySelector(s);
                if (el) return el.innerText;
            }
            return document.body.innerText;
        }""")

        browser.close()
        return title, content


def download_images(url: str, vault: Path) -> list[str]:
    """Download images from the page and return list of local paths."""
    from playwright.sync_api import sync_playwright

    images_dir = vault / "raw" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        img_urls = page.evaluate("""() => {
            return Array.from(document.querySelectorAll('article img, main img'))
                .map(i => i.src).filter(s => s.startsWith('http')).slice(0, 10);
        }""")

        for i, img_url in enumerate(img_urls):
            try:
                ext = img_url.split("?")[0].rsplit(".", 1)[-1][:4] or "jpg"
                fname = images_dir / f"{slugify(url[:40])}-{i}.{ext}"
                resp = page.request.get(img_url, timeout=10000)
                resp.dispose() if not resp.ok else fname.write_bytes(resp.body())
                if resp.ok:
                    saved.append(str(fname.relative_to(vault)))
            except Exception:
                pass

        browser.close()
    return saved


def interactive_discuss(content: str, title: str, client: anthropic.Anthropic) -> None:
    """Call Claude to discuss key takeaways, then pause before saving."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                f"I just fetched this article: '{title}'\n\n"
                f"{content[:6000]}\n\n"
                "Please discuss:\n"
                "1. The 3-5 most important takeaways\n"
                "2. What concepts this connects to\n"
                "3. Any surprising or counterintuitive points\n"
                "Keep it conversational, ~200 words."
            )
        }]
    )
    print("\n--- Key Takeaways Discussion ---")
    print(response.content[0].text)
    print("--------------------------------")
    input("\nPress Enter to save to vault, or Ctrl+C to abort ... ")


def save_to_vault(url: str, title: str, content: str, tags: list[str], vault: Path, images: list[str]) -> Path:
    slug = slugify(title)
    out_path = vault / "raw" / "web" / f"{slug}.md"

    img_section = ""
    if images:
        img_section = "\n## Images\n" + "\n".join(f"![[{p}]]" for p in images) + "\n"

    frontmatter = f"""---
title: "{title}"
source: "{url}"
date_ingested: "{date.today()}"
type: web_article
tags: [{", ".join(tags)}]
compiled: false
---

"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(frontmatter + content + img_section, encoding="utf-8")
    return out_path


def update_meta(vault: Path) -> None:
    meta_path = vault / "wiki" / "_meta.md"
    if not meta_path.exists():
        return
    text = meta_path.read_text(encoding="utf-8")
    raw_count = len(list((vault / "raw").rglob("*.md")))
    text = re.sub(r"- \*\*Sources ingested\*\*: \d+", f"- **Sources ingested**: {raw_count}", text)
    meta_path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Clip a web URL into the knowledge base")
    parser.add_argument("url", help="URL to clip")
    parser.add_argument("--tags", default="", help="Comma-separated tags")
    parser.add_argument("--vault", default=str(VAULT), help="Vault root path")
    parser.add_argument("--no-images", action="store_true", help="Skip image download")
    parser.add_argument("--interactive", action="store_true", help="Discuss key takeaways with Claude before saving")
    args = parser.parse_args()

    vault = Path(args.vault)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    print(f"Fetching {args.url} ...")
    try:
        title, content = fetch_as_markdown(args.url)
    except Exception as e:
        print(f"Error fetching page: {e}", file=sys.stderr)
        sys.exit(1)

    if args.interactive:
        interactive_discuss(content, title, anthropic.Anthropic())

    images = []
    if not args.no_images:
        print("Downloading images ...")
        try:
            images = download_images(args.url, vault)
        except Exception:
            pass  # images are optional

    out_path = save_to_vault(args.url, title, content, tags, vault, images)
    update_meta(vault)
    append_log(vault, "ingest", title)

    print(f"Saved: {out_path}")
    print(f"Title: {title}")
    if tags:
        print(f"Tags: {', '.join(tags)}")
    print("\nRun `python kb_compile.py` to compile this into the wiki.")


if __name__ == "__main__":
    main()
