"""kb_state.py — Shared state management for all kb_* scripts.

Tracks compiled file hashes (for change detection) and cumulative API costs.
State is stored in wiki/state.json inside the vault.
"""

import hashlib
import json
from pathlib import Path

# Pricing for claude-sonnet-4-6 (USD per 1M tokens)
PRICE_INPUT_PER_M = 3.00
PRICE_OUTPUT_PER_M = 15.00

STATE_FILE = "wiki/state.json"

_EMPTY_STATE = {
    "compiled_hashes": {},   # {relative_path: sha256[:16]}
    "costs": {
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cost_usd": 0.0,
        "compile_calls": 0,
        "query_calls": 0,
        "lint_calls": 0,
    },
}


def load_state(vault: Path) -> dict:
    path = vault / STATE_FILE
    if not path.exists():
        return json.loads(json.dumps(_EMPTY_STATE))  # deep copy
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(_EMPTY_STATE))


def save_state(vault: Path, state: dict) -> None:
    path = vault / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def file_hash(path: Path) -> str:
    """Return first 16 chars of SHA-256 hash of a file."""
    h = hashlib.sha256(path.read_bytes())
    return h.hexdigest()[:16]


def record_cost(vault: Path, operation: str, input_tokens: int, output_tokens: int) -> float:
    """Add API call cost to state. Returns cost of this call in USD."""
    cost = (input_tokens * PRICE_INPUT_PER_M + output_tokens * PRICE_OUTPUT_PER_M) / 1_000_000

    state = load_state(vault)
    state["costs"]["total_input_tokens"] += input_tokens
    state["costs"]["total_output_tokens"] += output_tokens
    state["costs"]["total_cost_usd"] = round(state["costs"]["total_cost_usd"] + cost, 6)

    call_key = f"{operation}_calls"
    if call_key in state["costs"]:
        state["costs"][call_key] += 1

    save_state(vault, state)
    return cost


def mark_compiled_hash(vault: Path, source_path: Path) -> None:
    """Record the current hash of a compiled source file."""
    rel = str(source_path.relative_to(vault))
    state = load_state(vault)
    state["compiled_hashes"][rel] = file_hash(source_path)
    save_state(vault, state)


def needs_recompile(vault: Path, source_path: Path) -> bool:
    """Return True if file is new (compiled: false) or has changed since last compile."""
    text = source_path.read_text(encoding="utf-8")
    if "compiled: false" in text or 'compiled: "false"' in text:
        return True
    # File is marked compiled — check if it changed
    rel = str(source_path.relative_to(vault))
    state = load_state(vault)
    stored_hash = state["compiled_hashes"].get(rel)
    if stored_hash is None:
        # File says compiled: true but hash missing (e.g. compiled on another machine) — backfill and skip
        mark_compiled_hash(vault, source_path)
        return False
    return file_hash(source_path) != stored_hash
