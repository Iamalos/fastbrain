# Lint Procedure

Health-check the wiki. Find structural problems and LLM-detected quality issues, then heal them.

## Automated Checks (structural, no LLM)

Run via CLI: `python kb_lint.py`

Detects:
- **Orphan articles** — `wiki/concepts/*.md` with zero incoming `[[wikilinks]]` from other files
- **Dead wikilinks** — `[[Target]]` where no `Target.md` exists in the vault *(planned)*
- **Missing sources** — frontmatter `sources:` entries pointing at nonexistent `raw/` files *(planned)*

## LLM-Driven Checks (require reading articles)

Run these periodically or after a batch of new content.

### Stale content
- Compare article's `last_updated` date vs source file's `date_ingested`
- Flag articles where a source is newer than the article — recompile needed

### Inconsistencies
- Load groups of related articles (shared tags or wikilinks)
- Check for contradictory factual claims across articles
- Inconsistent terminology (same concept named differently)

### Missing coverage
- Find concepts referenced in 3+ articles but lacking their own article
- Check if relevant raw sources exist — if yes, compile; if no, mark as a research gap

### Filed-back query absorption
- Scan `outputs/queries/` for recent answers
- Check if insights in those answers have been absorbed into the wiki articles listed in `informed_by:`
- If not, flag those articles for update — this is the core compounding mechanism

### Format violations
- H1 title matches filename
- Lead paragraph present
- Sources section at bottom
- At least 5 outgoing wikilinks

## Lint Report Format

```
## [YYYY-MM-DD] lint | Health score N/100

ORPHAN ARTICLES (N)
  - article-slug — 0 incoming links
    → SUGGEST: Add refs from related-article-1.md, related-article-2.md

MISSING COVERAGE (N)
  - "Concept Name" referenced in 4 articles, no article exists
    → SUGGEST: Create wiki/concepts/concept-name.md

INCONSISTENCIES (N)
  - article-1 vs article-2: contradictory claim about X
    → RESOLVE: Check source, pick canonical version

FILED-BACK INSIGHTS (N)
  - outputs/queries/2026-04-05-question.md has synthesis not yet in concept-article.md
    → ABSORB: Update concept-article.md with the insight
```

Report saved to `outputs/lint_report_YYYY-MM-DD.md`.

## Heal Workflow

For each issue surfaced:
1. **Orphan** → add incoming wikilinks from related articles, or delete if out of scope
2. **Dead link** → create the missing article or rewrite the link
3. **Missing coverage + sources exist** → compile the new article
4. **Missing coverage + no sources** → add to research gaps in `CLAUDE.md`
5. **Inconsistency** → verify against source, fix all affected articles
6. **Stale content** → re-read source, update article
7. **Filed-back insight** → absorb into the relevant wiki article

## After Lint

Append log entry: `## [YYYY-MM-DD] lint | Health score N/100`
