---
name: karpathy-kb
description: Manage the personal Karpathy-style LLM knowledge base in Obsidian at /mnt/d/core. Use this skill when the user asks to ingest a URL, compile sources, query the wiki, lint the knowledge base, or do anything with the wiki, vault, or knowledge base. Triggers on: "add to wiki", "ingest", "compile", "query the wiki", "lint", "knowledge base", "update the wiki".
---

# Karpathy Knowledge Base Skill

A personal LLM-maintained wiki in Obsidian. Raw sources → compiled concept articles → Q&A → lint. The wiki compounds: every answer and every source makes future answers better.

## Vault and Scripts

- **Vault**: `/mnt/d/core` (Obsidian, WSL path)
- **Scripts**: `/home/iamalos/nbs/projwiki/kb_*.py`
- **CLAUDE.md**: `CLAUDE.md` in the vault root — read it first when starting a session

## Two Modes

**Interactive (this session)** — use MCP tools directly, do NOT call the Python scripts:
- Read/write via `mcp__obsidian__*` tools
- Fetch web content via Playwright MCP
- Always read `wiki/_index.md` before any compile or query work

**CLI (batch/automated)** — run from terminal:
```bash
python kb_ingest.py <url> [--tags tag1,tag2] [--interactive]
python kb_compile.py [--force]
python kb_query.py "question" [--format md|marp|bullet] [--file-into-wiki]
python kb_lint.py
```

## Four Procedures

Read the reference file for the procedure you need:

| Task | Reference | CLI |
|------|-----------|-----|
| Add a URL or note to the vault | [references/ingest.md](references/ingest.md) | `kb_ingest.py` |
| Compile raw sources into wiki articles | [references/compile.md](references/compile.md) | `kb_compile.py` |
| Answer a question against the wiki | [references/query.md](references/query.md) | `kb_query.py` |
| Health-check the wiki | [references/lint.md](references/lint.md) | `kb_lint.py` |

For vault structure, frontmatter schemas, and linking conventions, see [references/vault-conventions.md](references/vault-conventions.md).

For a blank wiki article template, see [assets/wiki-article-template.md](assets/wiki-article-template.md).

## Log Every Operation

After every ingest, compile, query, or lint — append one entry to `wiki/log.md`:

```
## [YYYY-MM-DD] operation | Short description
```

Operations: `ingest`, `ingest-note`, `compile`, `compile-note`, `query`, `lint`, `promote`

The Python scripts do this automatically. When working interactively via MCP, append the log entry manually using `mcp__obsidian__patch_note` or `mcp__obsidian__write_note` in append mode.

## When NOT to Use This Skill

- General markdown editing unrelated to the wiki
- Code documentation or project READMEs
- Daily journaling or to-do lists
