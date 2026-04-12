# Vault Conventions

Reference for frontmatter schemas, linking conventions, and log format.

## Vault Structure

```
/mnt/d/core/
├── raw/
│   ├── web/        ← Clipped web articles (immutable after ingest)
│   ├── papers/     ← Papers and documents
│   ├── notes/      ← Manually written notes
│   └── images/     ← Downloaded images from sources
├── wiki/
│   ├── concepts/   ← One .md per concept (Claude-maintained)
│   ├── _index.md   ← Master index (Claude-maintained)
│   ├── _meta.md    ← Stats and timestamps (Claude-maintained)
│   └── log.md      ← Append-only operation log (Claude-maintained)
└── outputs/
    ├── queries/    ← Q&A answers
    └── slides/     ← Marp slide decks
```

## Frontmatter Schemas

### Raw source (web article / paper)
```yaml
---
title: "Article Title"
source: "https://..."
date_ingested: "YYYY-MM-DD"
type: web_article   # or: paper, note
tags: [tag1, tag2]
compiled: false     # set to true after compile
---
```

### Raw source (manual note)
```yaml
---
title: "Note Title"
date_ingested: "YYYY-MM-DD"
type: note
tags: [tag1, tag2]
compiled: false
---
```

### Wiki concept article
```yaml
---
title: "Concept Name"
tags: [tag1, tag2]
sources:
  - "[[raw/web/article-slug]]"
  - "[[raw/papers/paper-slug]]"
last_updated: "YYYY-MM-DD"
---
```

### Query output
```yaml
---
question: "The question asked"
date: "YYYY-MM-DD"
format: md          # or: marp, bullet
type: query_output
informed_by:
  - "[[concepts/article-1]]"
  - "[[concepts/article-2]]"
---
```

## Linking Conventions

- Use Obsidian `[[wikilinks]]` for all internal links
- Link to concepts: `[[concepts/concept-slug]]` or just `[[concept-slug]]`
- Link to raw sources: `[[raw/web/article-slug]]`
- First mention of a concept in an article → always wikilink it
- Target 10+ outgoing wikilinks per concept article

## _index.md Format

```markdown
# Knowledge Base Index
Last compiled: YYYY-MM-DD HH:MM
Sources: N | Concepts: M

## Concepts
<!-- Claude maintains this section. Format: - [[concept]] — one-line summary -->
- [[concepts/concept-slug]] — one-line summary

## Recent Sources
- [[raw/web/article-slug]] — one-line summary (YYYY-MM-DD)
```

Always read `_index.md` first before any compile or query work.

## log.md Format

Append-only. One entry per operation:
```
## [YYYY-MM-DD] operation | Title or description
```

Operations: `ingest`, `ingest-note`, `compile`, `compile-note`, `query`, `lint`, `promote`

Grep examples:
```bash
grep 'ingest' wiki/log.md          # all ingests
grep '2026-04' wiki/log.md         # all April entries
grep 'query' wiki/log.md           # all queries
grep "$(date +%Y-%m-%d)" wiki/log.md  # today
```

The Python scripts append log entries automatically. In interactive MCP sessions, append manually after each operation.
