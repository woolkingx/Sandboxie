#!/usr/bin/env python3
from pathlib import Path
from ledger_reader import read_combined_ledger
import re


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "Sandboxie/core"
REPORT = ROOT / "docs/plan/core-coverage-audit.md"

COMMENT_PATTERN = re.compile(
    r"\b(TODO|FIXME|fixme|todo|HACK|XXX|BUG|workaround|crash|leak|hang|deadlock|"
    r"wrong|unsafe|unimplemented|not implemented|does not work|broken)\b",
    re.IGNORECASE,
)

REVIEWABLE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".asm",
    ".rc",
    ".def",
}

IGNORED_COMMENT_TOKENS = {
    "change",
    "debug",
    "exchange",
}

RISK_TERMS = [
    ("api", 6),
    ("token", 5),
    ("security", 5),
    ("access", 4),
    ("password", 5),
    ("credential", 5),
    ("sid", 5),
    ("acl", 5),
    ("privilege", 5),
    ("impersonat", 5),
    ("createprocess", 4),
    ("deviceiocontrol", 4),
    ("nt", 2),
    ("zw", 2),
    ("hook", 3),
    ("inject", 4),
    ("syscall", 4),
    ("rpc", 4),
    ("alpc", 4),
    ("pipe", 3),
    ("com", 3),
    ("service", 3),
    ("reparse", 4),
    ("mount", 4),
    ("probe", 3),
    ("exception", 2),
    ("handle", 2),
]


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def core_files() -> list[Path]:
    return sorted(path for path in CORE.rglob("*") if path.is_file())


def reviewable(files: list[Path]) -> list[Path]:
    return [path for path in files if path.suffix.lower() in REVIEWABLE_SUFFIXES]


def ledger_entries(text: str) -> list[str]:
    return re.findall(r"^### ((?:SREV|KPATH)-[0-9A-Z]+):", text, flags=re.MULTILINE)


def covered_files(files: list[Path], ledger: str) -> set[str]:
    paths = {rel(path) for path in files}
    return {path for path in paths if path in ledger}


def status_counts(ledger: str) -> dict[str, int]:
    counts = {
        "patched_source_needs_windows": 0,
        "policy_or_runtime_open": 0,
        "runtime_design_open": 0,
        "named_runtime_capture": 0,
    }
    for line in ledger.splitlines():
        if not line.startswith("| Status |"):
            continue
        lower = line.lower()
        if "patched source-level" in lower and "needs windows" in lower:
            counts["patched_source_needs_windows"] += 1
        if "policy" in lower and "open" in lower:
            counts["policy_or_runtime_open"] += 1
        if "runtime" in lower and "design still open" in lower:
            counts["runtime_design_open"] += 1
        if "runtime capture" in lower:
            counts["named_runtime_capture"] += 1
    return counts


def comment_hits(files: list[Path], ledger: str) -> list[tuple[str, int, str, bool]]:
    hits: list[tuple[str, int, str, bool]] = []
    for path in files:
        try:
            lines = read_text(path).splitlines()
        except OSError:
            continue
        covered = rel(path) in ledger
        for number, line in enumerate(lines, start=1):
            match = COMMENT_PATTERN.search(line)
            if not match:
                continue
            token = match.group(1).lower()
            if token in IGNORED_COMMENT_TOKENS:
                continue
            stripped = line.strip()
            if stripped.startswith("#ifdef") or stripped.startswith("#undef"):
                continue
            hits.append((rel(path), number, stripped[:180], covered))
    return hits


def unnamed_file_risk(files: list[Path], ledger: str) -> list[tuple[int, int, str, str]]:
    rows: list[tuple[int, int, str, str]] = []
    for path in files:
        path_text = rel(path)
        if path_text in ledger:
            continue
        try:
            text = read_text(path)
        except OSError:
            continue
        lower = text.lower()
        lines = text.count("\n") + 1
        score = min(lines // 200, 10)
        hits: list[str] = []
        for term, weight in RISK_TERMS:
            count = lower.count(term)
            if count:
                score += min(count, 8) * weight
                hits.append(f"{term}:{count}")
        rows.append((score, lines, path_text, ", ".join(hits[:8])))
    return sorted(rows, reverse=True)


def main() -> None:
    files = core_files()
    review_files = reviewable(files)
    ledger = read_combined_ledger(ROOT)
    entries = ledger_entries(ledger)
    covered = covered_files(review_files, ledger)
    hits = comment_hits(review_files, ledger)
    uncovered_hits = [hit for hit in hits if not hit[3]]
    unnamed_risk = unnamed_file_risk(review_files, ledger)
    counts = status_counts(ledger)
    report = read_text(REPORT)

    print("CORE_COVERAGE_SUMMARY")
    summary = {
        "core_files": len(files),
        "reviewable_core_files": len(review_files),
        "ledger_entries": len(entries),
        "reviewable_files_named_in_ledger": len(covered),
        "reviewable_files_not_named_in_ledger": len(review_files) - len(covered),
        "comment_risk_hits": len(hits),
        "comment_risk_hits_in_files_not_named_in_ledger": len(uncovered_hits),
    }
    summary.update(counts)
    for name, value in summary.items():
        print(f"{name}={value}")
        marker = f"{name}={value}"
        if marker not in report:
            raise SystemExit(f"core coverage failed: report missing {marker}")

    print("\nTOP_UNCOVERED_COMMENT_RISKS")
    for path, line, text, _covered in uncovered_hits[:40]:
        print(f"{path}:{line}: {text}")

    print("\nTOP_COVERED_COMMENT_RISKS")
    for path, line, text, _covered in [hit for hit in hits if hit[3]][:40]:
        print(f"{path}:{line}: {text}")

    print("\nTOP_UNNAMED_REVIEWABLE_FILES")
    for score, lines, path, terms in unnamed_risk[:40]:
        print(f"{score:4d} {lines:5d} {path} {terms}")

    if len(entries) < 48:
        raise SystemExit("core coverage failed: expected at least SREV-001..048 ledger entries")
    if not files:
        raise SystemExit("core coverage failed: no Sandboxie/core files found")


if __name__ == "__main__":
    main()
