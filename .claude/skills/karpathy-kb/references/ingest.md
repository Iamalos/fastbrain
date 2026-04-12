# Ingest Procedure

Add a new source to `raw/` so it can be compiled into the wiki.

## Source Types and Destinations

| Source | Folder | `type` value |
|--------|--------|--------------|
| Web article / blog post | `raw/web/` | `web_article` |
| Paper or document | `raw/papers/` | `paper` |
| Manually written note | `raw/notes/` | `note` |

## Interactive Ingest (MCP session)

1. **Fetch the page** via Playwright MCP (`mcp__plugin_playwright_playwright__browser_navigate` + `browser_snapshot`)
2. **Extract content** — prefer `<article>` or `<main>` elements
3. **Download images** (optional) — save to `raw/images/` and embed as `![[raw/images/filename]]`
4. **Save to vault** via `mcp__obsidian__write_note` with full frontmatter:

```yaml
---
title: "Article Title"
source: "https://..."
date_ingested: "YYYY-MM-DD"
type: web_article
tags: [tag1, tag2]
compiled: false
---
```

5. **Discuss key takeaways** (recommended) — before moving on, briefly discuss with the user:
   - 3–5 most important takeaways
   - What concepts this connects to in the existing wiki
   - Any surprising or counterintuitive points
6. **Append log entry**: `## [YYYY-MM-DD] ingest | Article Title`
7. **Update `wiki/_meta.md`** source count

## CLI Ingest

```bash
# Standard ingest
python kb_ingest.py https://example.com/article --tags ml,attention

# With interactive discussion before saving
python kb_ingest.py https://example.com/article --tags ml --interactive

# Skip image download
python kb_ingest.py https://example.com/article --no-images
```

## Manual Note Ingest

Create a file directly in `raw/notes/<slug>.md` with:

```yaml
---
title: "My Note Title"
date_ingested: "YYYY-MM-DD"
type: note
tags: [tag1, tag2]
compiled: false
---

Note content here...
```

No `source:` field needed. Set `compiled: false` — compile workflow picks it up automatically.

## After Ingest

Run compile to process the new source into wiki articles. If ingesting in batch, finish all ingests first, then compile once.
