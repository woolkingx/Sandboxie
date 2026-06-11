#!/usr/bin/env python3
"""Split systematic-code-review-ledger.md into per-id fragment files.

Source ledger is read-only. Fragment files are written under docs/plan/ledger/.
Existing fragment files are overwritten only when the body changed.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "systematic-code-review-ledger.md"
OUT_DIR = ROOT / "ledger"

HEADING_RE = re.compile(r"^### ((?:SREV|KPATH)-[0-9A-Z]+): (.+?)\s*$", re.M)
ROW_RE = re.compile(r"^\| ([^|]+?)\s*\|\s*(.+?)\s*\|\s*$", re.M)
OWNER_PATH_RE = re.compile(r"`(Sandboxie/[^`]+)`")


def extract_entries(text: str) -> list[tuple[str, str, str]]:
    """Return list of (id, title, body) where body starts at the heading line."""
    matches = list(HEADING_RE.finditer(text))
    entries: list[tuple[str, str, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            # Stop at next `## ` section heading after this one.
            tail = text[start:]
            sec = re.search(r"^## ", tail[3:], re.M)
            end = start + 3 + sec.start() if sec else len(text)
        body = text[start:end].rstrip() + "\n"
        entries.append((m.group(1), m.group(2).strip(), body))
    return entries


def field(body: str, name: str) -> str:
    for m in ROW_RE.finditer(body):
        if m.group(1).strip().lower() == name.lower():
            return m.group(2).strip()
    return ""


def owner_path(body: str) -> str:
    # Prefer Evidence row, then Data row, then anywhere.
    for row in ("Evidence", "Data"):
        cell = field(body, row)
        m = OWNER_PATH_RE.search(cell)
        if m:
            return m.group(1)
    m = OWNER_PATH_RE.search(body)
    return m.group(1) if m else ""


def status_slug(body: str) -> str:
    raw = field(body, "Status")
    if not raw:
        return ""
    slug = raw.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug[:80]


def find_artifact(num: str, suffix: str) -> str:
    # Match srev-NNN-*, srev-NNN<letter>-*, srev-NNN.suffix, srev-NNN<letter>.suffix
    direct = sorted(ROOT.glob(f"srev-{num}{suffix}")) + sorted(
        ROOT.glob(f"srev-{num}[a-z]{suffix}")
    )
    suffixed = sorted(ROOT.glob(f"srev-{num}-*{suffix}")) + sorted(
        ROOT.glob(f"srev-{num}[a-z]-*{suffix}")
    )
    matches = direct + suffixed
    paths = [f"docs/plan/{m.name}" for m in matches]
    if not paths:
        return ""
    return paths[0] if len(paths) == 1 else "[" + ", ".join(paths) + "]"


def find_checker(num: str) -> str:
    # Prefer .py; fall back to .sh; include variant letters (006a/006b).
    py = sorted(ROOT.glob(f"check-srev-{num}.py")) + sorted(
        ROOT.glob(f"check-srev-{num}[a-z].py")
    )
    sh = sorted(ROOT.glob(f"check-srev-{num}.sh")) + sorted(
        ROOT.glob(f"check-srev-{num}[a-z].sh")
    )
    picks = py if py else sh
    paths = [f"docs/plan/{m.name}" for m in picks]
    if not paths:
        return ""
    return paths[0] if len(paths) == 1 else "[" + ", ".join(paths) + "]"


def runtime_gate(body: str) -> str:
    cell = field(body, "Acceptance Gate")
    if not cell:
        return ""
    # Newer entries: "Runtime/build gate:" or "Runtime gate:"
    m = re.search(r"Runtime(?:[/ ]build)? gate[:\.]?\s*(.+?)(?:\.\s|\.$|$)", cell, re.I)
    if m:
        return m.group(1).strip().rstrip(".")
    # Older entries: "Windows gate:" / "Windows runtime gate:"
    m = re.search(r"Windows(?: runtime)? gate[:\.]?\s*(.+?)(?:\.\s|\.$|$)", cell, re.I)
    if m:
        return m.group(1).strip().rstrip(".")
    return ""


def yaml_escape(value: str) -> str:
    if not value:
        return '""'
    if re.search(r'[:#`\'"\\\n]|^\s|\s$', value):
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def build_front_matter(entry_id: str, title: str, body: str) -> str:
    kind = "srev-ledger-entry" if entry_id.startswith("SREV") else "kpath-ledger-entry"
    num_match = re.match(r"(?:SREV|KPATH)-(.+)", entry_id)
    num = num_match.group(1) if num_match else ""
    num_lower = num.lower()
    fields = {
        "kind": kind,
        "id": entry_id,
        "title": title,
        "status": status_slug(body),
        "owner": owner_path(body),
        "spec": find_artifact(num_lower, ".md"),
        "schema": find_artifact(num_lower, ".schema.json"),
        "checker": find_checker(num_lower),
        "runtime_gate": runtime_gate(body),
    }
    lines = ["---"]
    for k, v in fields.items():
        lines.append(f"{k}: {yaml_escape(v)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def fragment_path(entry_id: str) -> Path:
    prefix, num = entry_id.split("-", 1)
    return OUT_DIR / f"{prefix.lower()}-{num.lower()}.md"


def main() -> int:
    text = LEDGER.read_text()
    entries = extract_entries(text)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    skipped = 0
    for entry_id, title, body in entries:
        out = fragment_path(entry_id)
        content = build_front_matter(entry_id, title, body) + body
        if out.exists() and out.read_text() == content:
            skipped += 1
            continue
        out.write_text(content)
        written += 1
    print(f"entries={len(entries)} written={written} skipped_unchanged={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
