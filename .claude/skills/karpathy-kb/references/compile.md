# Compile Procedure

Read uncompiled raw sources and create or update wiki concept articles.

## Interactive Compile (MCP session)

1. **Read `wiki/_index.md`** — understand what's already in the wiki before touching anything
2. **Find uncompiled sources** — list files in `raw/` with `compiled: false` in frontmatter
3. **For each source**, in order:
   - Read the source file fully
   - Identify 2–6 key concepts it covers
   - For each concept: create `wiki/concepts/<slug>.md` or update if it exists
   - Write dense, well-linked articles (target 1000–3000 words for thorough coverage)
   - Use `[[wikilinks]]` liberally — target 10+ per article
   - Include frontmatter: `title`, `tags`, `sources`, `last_updated`
4. **Backlink audit** (mandatory after each new article):
   - Search other concept articles for mentions of the new article's title
   - Add `[[New Article]]` at first occurrence in each file that mentions it
   - This is what makes the graph bidirectional — don't skip it
5. **Update `wiki/_index.md`**:
   - Add new concept entries under `## Concepts`
   - Add source entry under `## Recent Sources`
   - Update `Last compiled`, `Sources: N`, `Concepts: M` stats
6. **Mark source as compiled**: change `compiled: false` → `compiled: true`
7. **Append log entry**: `## [YYYY-MM-DD] compile | source-slug → concept1, concept2`
8. **Update `wiki/_meta.md`** stats

## CLI Compile

```bash
# Compile all uncompiled sources
python kb_compile.py

# Recompile everything (force)
python kb_compile.py --force

# Use a different model
python kb_compile.py --model claude-opus-4-6
```

## Article Quality Standards

Every concept article should have:
- **H1 title** matching the filename slug
- **Lead paragraph** — 2–4 sentences: what is it, why it matters, scope
- **Core sections** (H2) — substantive content with code, tables, diagrams where useful
- **Sources and Further Reading** — all cited `raw/` sources + related concept links
- **Frontmatter**: `title`, `tags`, `sources` (list of raw/ paths), `last_updated`

Compile foundational articles first — articles that many others will link to.

## When Sources Touch Multiple Topics

A single source may contribute to many existing articles (not just create new ones). Read related existing concepts and update them with new information from the source. Cross-referencing across sources is where the wiki's value compounds.
