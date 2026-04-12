# Query Procedure

Answer a question by reasoning over the wiki, then file the answer back.

## Interactive Query (MCP session)

1. **Read `wiki/_index.md`** — identify which concept articles are relevant to the question
2. **Read relevant articles** — load only the articles identified in step 1
3. **Synthesize answer** — combine information across articles, cite sources with `[[wikilinks]]`
4. **Choose output format**:
   - `md` — full markdown article with headers (default)
   - `marp` — slide deck with `marp: true` frontmatter and `---` separators
   - `bullet` — nested bullets only
5. **Save the answer** to `outputs/queries/YYYY-MM-DD-<slug>.md` with frontmatter:
   ```yaml
   ---
   question: "The question asked"
   date: "YYYY-MM-DD"
   format: md
   type: query_output
   informed_by:
     - "[[concepts/article-1]]"
     - "[[concepts/article-2]]"
   ---
   ```
6. **Append log entry**: `## [YYYY-MM-DD] query | Question text (truncated to 80 chars)`
7. **Update `wiki/_meta.md`** last query timestamp

## CLI Query

```bash
# Standard markdown answer
python kb_query.py "What are the key tradeoffs between X and Y?"

# Save as Marp slide deck
python kb_query.py "Summarize the field of X" --format marp

# File directly into wiki as a concept article
python kb_query.py "Explain the relationship between X and Y" --file-into-wiki
```

## Promoting Answers to Wiki

When a query answer is strong enough to serve as a first-class reference — a comparison table, a synthesis across multiple sources, a novel trade-off analysis — promote it to `wiki/concepts/`:

1. Move or copy the answer file to `wiki/concepts/q-<slug>.md`
2. Add proper concept frontmatter (`sources`, `last_updated`, `tags`)
3. Run a backlink audit: grep other articles for the answer's topic and add wikilinks
4. Update `wiki/_index.md` with the new concept entry
5. Append log entry: `## [YYYY-MM-DD] promote | Answer title`

Promoted answers become equal citizens of the wiki and feed future compilations. This is the compounding mechanism.

## When No Articles Match

If `_index.md` shows no relevant concepts, answer from general knowledge and explicitly note that the wiki lacks coverage on this topic. Consider whether to ingest sources and compile an article before answering.
