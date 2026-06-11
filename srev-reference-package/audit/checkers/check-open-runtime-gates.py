#!/usr/bin/env python3
from pathlib import Path
import re
import sys

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]
LEDGER_DIR = ROOT / "docs/plan/ledger"


FRONT_MATTER_RE = re.compile(r"\A---\n(?P<meta>.*?)\n---\n", re.S)
STATUS_RE = re.compile(r"^\| Status \| (?P<status>.*?) \|$", re.M)


EXPECTED_CAPTURE_CONTRACTS = {
    "SREV-015": {
        "playbook": "docs/plan/srev-015-138-alpc-runtime-capture-playbook.md",
        "schema": "docs/plan/srev-015-138-alpc-runtime-capture.schema.json",
        "checker": "docs/plan/check-srev-015-138-alpc-runtime-capture.sh",
    },
    "SREV-022": {
        "playbook": "docs/plan/srev-022-027-kernel-runtime-capture-playbook.md",
        "schema": "docs/plan/srev-022-027-kernel-runtime-capture.schema.json",
        "checker": "docs/plan/check-srev-022-027-kernel-runtime-capture.sh",
    },
    "SREV-027": {
        "playbook": "docs/plan/srev-022-027-kernel-runtime-capture-playbook.md",
        "schema": "docs/plan/srev-022-027-kernel-runtime-capture.schema.json",
        "checker": "docs/plan/check-srev-022-027-kernel-runtime-capture.sh",
    },
    "SREV-092": {
        "playbook": "docs/plan/srev-092-322-user-lifecycle-runtime-capture-playbook.md",
        "schema": "docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json",
        "checker": "docs/plan/check-srev-092-322-user-lifecycle-runtime-capture.sh",
    },
    "SREV-138": {
        "playbook": "docs/plan/srev-015-138-alpc-runtime-capture-playbook.md",
        "schema": "docs/plan/srev-015-138-alpc-runtime-capture.schema.json",
        "checker": "docs/plan/check-srev-015-138-alpc-runtime-capture.sh",
    },
    "SREV-322": {
        "playbook": "docs/plan/srev-092-322-user-lifecycle-runtime-capture-playbook.md",
        "schema": "docs/plan/srev-092-322-user-lifecycle-runtime-capture.schema.json",
        "checker": "docs/plan/check-srev-092-322-user-lifecycle-runtime-capture.sh",
    },
    "SREV-326": {
        "playbook": "docs/plan/srev-326-327-secure-runtime-capture-playbook.md",
        "schema": "docs/plan/srev-326-327-secure-runtime-capture.schema.json",
        "checker": "docs/plan/check-srev-326-327-secure-runtime-capture.sh",
    },
    "SREV-327": {
        "playbook": "docs/plan/srev-326-327-secure-runtime-capture-playbook.md",
        "schema": "docs/plan/srev-326-327-secure-runtime-capture.schema.json",
        "checker": "docs/plan/check-srev-326-327-secure-runtime-capture.sh",
    },
}


def parse_front_matter(text: str) -> dict[str, str]:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}

    meta: dict[str, str] = {}
    for line in match.group("meta").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        meta[key.strip()] = value
    return meta


def status_line(text: str) -> str:
    match = STATUS_RE.search(text)
    if not match:
        return ""
    return match.group("status")


def open_kind(status: str) -> str | None:
    lower = status.lower()
    if "runtime" in lower and "design still open" in lower:
        return "runtime-design-open"
    if "runtime capture" in lower:
        return "named-runtime-capture"
    return None


def combined_status_counts(ledger: str) -> dict[str, int]:
    counts = {
        "runtime_design_open": 0,
        "named_runtime_capture": 0,
    }
    for line in ledger.splitlines():
        if not line.startswith("| Status |"):
            continue
        lower = line.lower()
        if "runtime" in lower and "design still open" in lower:
            counts["runtime_design_open"] += 1
        if "runtime capture" in lower:
            counts["named_runtime_capture"] += 1
    return counts


def path_exists(value: str) -> bool:
    if not value:
        return False
    return (ROOT / value).exists()


def has_runtime_matrix(body: str) -> bool:
    lower = body.lower()
    return (
        "runtime capture matrix" in lower
        or "runtime matrix" in lower
        or "localdumps matrix" in lower
        or "deferred logger matrix" in lower
    )


def expected_capture_contract(entry_id: str) -> dict[str, str]:
    return EXPECTED_CAPTURE_CONTRACTS.get(entry_id, {})


def main() -> int:
    open_entries: list[dict[str, str]] = []
    errors: list[str] = []
    combined_counts = combined_status_counts(read_combined_ledger(ROOT))

    for path in sorted(LEDGER_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        meta = parse_front_matter(text)
        status = status_line(text)
        kind = open_kind(status)
        if not kind:
            continue

        entry_id = meta.get("id", path.stem.upper())
        entry = {
            "id": entry_id,
            "kind": kind,
            "title": meta.get("title", ""),
            "owner": meta.get("owner", ""),
            "spec": meta.get("spec", ""),
            "schema": meta.get("schema", ""),
            "checker": meta.get("checker", ""),
            "runtime_gate": meta.get("runtime_gate", ""),
            "status": status,
        }
        open_entries.append(entry)

        for key in ["title", "owner", "spec", "schema", "checker", "runtime_gate"]:
            if not entry[key]:
                errors.append(f"{entry_id}: missing front-matter {key}")
        for key in ["spec", "schema", "checker"]:
            if entry[key] and not path_exists(entry[key]):
                errors.append(f"{entry_id}: missing {key} path {entry[key]}")
        if not has_runtime_matrix(text):
            errors.append(f"{entry_id}: missing concrete runtime/capture matrix text")

        capture_contract = expected_capture_contract(entry_id)
        if not capture_contract:
            errors.append(f"{entry_id}: missing expected shared capture contract map")
        for key, contract_path in capture_contract.items():
            if not path_exists(contract_path):
                errors.append(f"{entry_id}: missing shared capture {key} path {contract_path}")
            if contract_path not in text:
                errors.append(
                    f"{entry_id}: ledger missing shared capture {key} {contract_path}"
                )

    design_open = [entry for entry in open_entries if entry["kind"] == "runtime-design-open"]
    capture_open = [entry for entry in open_entries if entry["kind"] == "named-runtime-capture"]

    if combined_counts["runtime_design_open"] != len(design_open):
        errors.append(
            "combined ledger runtime_design_open count mismatch: "
            f"{combined_counts['runtime_design_open']} != {len(design_open)}"
        )
    if combined_counts["named_runtime_capture"] != len(capture_open):
        errors.append(
            "combined ledger named_runtime_capture count mismatch: "
            f"{combined_counts['named_runtime_capture']} != {len(capture_open)}"
        )

    print("OPEN_RUNTIME_GATES")
    print(f"runtime_design_open={len(design_open)}")
    print(f"named_runtime_capture={len(capture_open)}")
    print(f"total_open={len(open_entries)}")
    print()
    print("| ID | Kind | Owner | Runtime Gate |")
    print("|---|---|---|---|")
    for entry in open_entries:
        runtime_gate = entry["runtime_gate"].replace("|", "\\|")
        print(
            f"| {entry['id']} | {entry['kind']} | `{entry['owner']}` | {runtime_gate} |"
        )

    if errors:
        print()
        print("OPEN_RUNTIME_GATE_ERRORS")
        for error in errors:
            print(error)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
