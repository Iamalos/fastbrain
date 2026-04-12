"""kb_log.py — Shared log helper for all kb_* scripts."""

from datetime import date
from pathlib import Path


def append_log(vault: Path, operation: str, title: str) -> None:
    """
    Append one entry to wiki/log.md.

    Format (grep-parseable, Karpathy-style):
        ## [YYYY-MM-DD] operation | Title

    Operations: ingest, ingest-note, compile, compile-note, query, lint
    """
    log_path = vault / "wiki" / "log.md"

    if not log_path.exists():
        log_path.write_text(
            "# Knowledge Base Log\n\n"
            "> Append-only. Format: `## [YYYY-MM-DD] operation | Title`\n"
            "> Grep examples:\n"
            ">   grep 'ingest' wiki/log.md\n"
            ">   grep '2026-04' wiki/log.md\n\n",
            encoding="utf-8",
        )

    entry = f"## [{date.today()}] {operation} | {title}\n"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)
