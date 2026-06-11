#!/usr/bin/env python3
from pathlib import Path
import os
import re
import sys


ENTRY_RE = re.compile(r"^### ((?:SREV|KPATH)-[0-9A-Z]+):", re.M)
H2_RE = re.compile(r"^## ", re.M)


def _fragment_id(text: str) -> str | None:
    match = re.search(r"^id:\s*([A-Z]+-[0-9A-Z]+)\s*$", text, re.M)
    if match:
        return match.group(1)
    match = ENTRY_RE.search(text)
    return match.group(1) if match else None


def _strip_fragment_entries(text: str, fragment_ids: set[str]) -> str:
    if not fragment_ids:
        return text

    matches = list(ENTRY_RE.finditer(text))
    if not matches:
        return text

    parts: list[str] = []
    cursor = 0
    for index, match in enumerate(matches):
        entry_id = match.group(1)
        next_starts = []
        if index + 1 < len(matches):
            next_starts.append(matches[index + 1].start())
        next_h2 = H2_RE.search(text, match.end())
        if next_h2:
            next_starts.append(next_h2.start())
        end = min(next_starts) if next_starts else len(text)

        parts.append(text[cursor:match.start()])
        if entry_id not in fragment_ids:
            parts.append(text[match.start():end])
        cursor = end

    parts.append(text[cursor:])
    return "".join(parts)


def read_combined_ledger(root: Path) -> str:
    plan_dir = root / "docs/plan"
    main = (plan_dir / "systematic-code-review-ledger.md").read_text(
        encoding="utf-8", errors="ignore"
    )
    ledger_dir = plan_dir / "ledger"
    fragments: list[str] = []
    fragment_ids: set[str] = set()
    if ledger_dir.exists():
        for path in sorted(ledger_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            entry_id = _fragment_id(text)
            if entry_id:
                fragment_ids.add(entry_id)
            fragments.append(text)

    parts = [_strip_fragment_entries(main, fragment_ids)]
    parts.extend(fragments)
    return "\n".join(parts)


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    try:
        print(read_combined_ledger(root), end="")
    except BrokenPipeError:
        sys.stdout = open(os.devnull, "w")
        raise SystemExit(0)
