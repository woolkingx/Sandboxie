#!/usr/bin/env python3
"""Convert SREV-029..043 schemas to draft-07 envelope.

Preserves all existing audit content (contracts, official_references, owner,
api, wire/data fields) and adds the draft-07 envelope required by the
documentation gate. The original structured fields are kept as descriptive
properties so no audit research is lost.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PLAN = Path(__file__).resolve().parent

# Fallback official_references for the three schemas that originally had none.
# All URLs are taken from the SREV-NNN spec markdown file under docs/plan/.
REFS_FALLBACK = {
    "srev-029-crypt-wire": [
        "https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata",
        "https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptunprotectdata",
        "https://learn.microsoft.com/en-us/windows/win32/api/wincrypt/ns-wincrypt-crypt_integer_blob",
        "https://learn.microsoft.com/en-us/windows/desktop/api/WinBase/nf-winbase-localalloc",
    ],
    "srev-030-service-query": [
        "https://learn.microsoft.com/en-us/windows/win32/api/winsvc/nf-winsvc-openservicew",
    ],
    "srev-031-process-low-sid": [
        "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_sid",
        "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlvalidsid",
        "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtllengthsid",
        "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlcopysid",
    ],
}


def title_from_stem(stem: str) -> str:
    # "srev-029-crypt-wire" -> "SREV-029 crypt wire"
    m = re.match(r"srev-(\d+[a-z]?)-(.+)", stem)
    num, rest = m.group(1).upper(), m.group(2).replace("-", " ")
    return f"SREV-{num} {rest}"


def summarize_wire_or_data(src: dict) -> tuple[str, str]:
    """Return (key_name, description) capturing wire/data/request/reply content."""
    parts: list[str] = []
    if "api" in src:
        api = src["api"]
        api_text = api if isinstance(api, str) else ", ".join(api)
        parts.append(f"API: {api_text}")
    if "msgid" in src:
        parts.append(f"MSGID: {src['msgid']}")
    for key in ("wire", "request", "reply", "data"):
        if key in src:
            blob = json.dumps(src[key], ensure_ascii=False, separators=(", ", ": "))
            parts.append(f"{key}: {blob}")
    if "callers" in src:
        callers = src["callers"]
        parts.append("callers: " + (", ".join(callers) if isinstance(callers, list) else str(callers)))
    if "related_schema" in src:
        parts.append(f"related_schema: {src['related_schema']}")
    description = " | ".join(parts) if parts else "Audit contract preserved from original schema"
    return ("audit_contract", description)


def build_new_schema(stem: str, src: dict) -> dict:
    sid = src.get("id", stem.upper())
    owner = src.get("owner", "")
    contracts = src.get("contracts", [])
    refs = src.get("official_references") or REFS_FALLBACK.get(stem, [])
    assert refs, f"{stem}: missing official_references and no fallback"

    contract_key, contract_desc = summarize_wire_or_data(src)

    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://sandboxie.local/schemas/{stem}.schema.json",
        "title": title_from_stem(stem),
        "id": sid,
        "owner": owner,
        "type": "object",
        "properties": {
            contract_key: {
                "type": "string",
                "description": contract_desc,
            },
            "validation_invariants": {
                "type": "string",
                "description": "All contracts listed in the contracts metadata must hold before any data is trusted past the validation boundary",
            },
            "runtime_matrix": {
                "type": "string",
                "description": "Windows runtime gate proves contracts hold under normal and malformed inputs",
            },
        },
        "required": [contract_key, "validation_invariants", "runtime_matrix"],
        "additionalProperties": False,
        "contracts": contracts,
        "official_references": refs,
    }
    return schema


def main() -> int:
    targets = sorted(PLAN.glob("srev-[0-9][0-9][0-9]-*.schema.json"))
    converted = 0
    skipped = 0
    for path in targets:
        existing = json.load(open(path))
        # Only convert files that lack the draft-07 envelope.
        if "$schema" in existing and "draft-07" in existing["$schema"]:
            skipped += 1
            continue
        stem = path.stem.removesuffix(".schema")
        new = build_new_schema(stem, existing)
        path.write_text(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
        converted += 1
        print(f"converted {path.name}")
    print(f"\nconverted={converted} skipped_already_draft07={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
