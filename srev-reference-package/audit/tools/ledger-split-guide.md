# Ledger Split Guide

This guide defines how to split `docs/plan/systematic-code-review-ledger.md`
into numbered Markdown fragments without changing source code or checker code.

## Goal

Keep the historical ledger readable while making later SREV/KPATH entries
script-addressable.

The main ledger remains the historical index:

```text
docs/plan/systematic-code-review-ledger.md
```

Numbered entries live under:

```text
docs/plan/ledger/
```

## File Naming

Use lowercase file names and preserve the review id:

```text
docs/plan/ledger/srev-135.md
docs/plan/ledger/srev-136.md
docs/plan/ledger/kpath-006.md
```

One file contains one review entry only.

## Required File Header

Every split file must start with YAML front matter:

```yaml
---
kind: srev-ledger-entry
id: SREV-135
title: MountManager Reparse Buffer And Query Defaults
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/svc/MountManagerHelpers.cpp
spec: docs/plan/srev-135-mountmanager-reparse-buffer-and-query-defaults.md
schema: docs/plan/srev-135-mountmanager-reparse-buffer-and-query-defaults.schema.json
checker: docs/plan/check-srev-135.py
runtime_gate: Windows mount-point and ImDisk runtime proof
---
```

For KPATH entries, use:

```yaml
kind: kpath-ledger-entry
id: KPATH-006
```

Required fields:

| Field | Meaning |
|---|---|
| `kind` | `srev-ledger-entry` or `kpath-ledger-entry` |
| `id` | Review id, for example `SREV-135` |
| `title` | Title after the ledger heading |
| `status` | Short machine-friendly status slug |
| `owner` | Primary owner path |
| `spec` | Spec Markdown path, if present |
| `schema` | Schema JSON path, if present |
| `checker` | Checker path, if present |
| `runtime_gate` | Short human-readable runtime proof still required |

Use an empty string only when a field truly has no artifact:

```yaml
schema: ""
checker: ""
```

## Body Format

After the front matter, preserve the normal ledger entry exactly:

```markdown
### SREV-135: MountManager Reparse Buffer And Query Defaults

| Field | Content |
|---|---|
| Severity | [major] |
| Status | ... |
| Evidence | ... |
| Data | ... |
| Schema | ... |
| Topology | ... |
| Logic Risk | ... |
| Official Shape | ... |
| Fix | ... |
| Acceptance Gate | ... |
```

Do not rename table fields while splitting. The existing field names are part of
the human review contract.

## Main Ledger Index Format

Replace moved entries in `systematic-code-review-ledger.md` with an index:

```markdown
## Split Ledger Fragments

Starting at SREV-135, new review ledger entries live in per-number files under
`docs/plan/ledger/` to keep this historical ledger from growing without bound.

| Entry | Fragment |
|---|---|
| SREV-135 | `docs/plan/ledger/srev-135.md` |
| SREV-136 | `docs/plan/ledger/srev-136.md` |
```

Do not leave duplicate full entries in both the main ledger and the fragment.
Duplication makes scripts double-count review entries.

## Split Procedure

1. Pick a contiguous range, for example `SREV-135..SREV-150`.
2. For each entry, copy the complete `### SREV-NNN...` block into
   `docs/plan/ledger/srev-NNN.md`.
3. Add the required YAML front matter.
4. Replace the moved blocks in the main ledger with index rows.
5. Confirm there is only one full body for each moved id:

```bash
rg -n "^### SREV-135:" docs/plan/systematic-code-review-ledger.md docs/plan/ledger
```

Expected result: one match in `docs/plan/ledger/srev-135.md`.

## No-Code Rule

This split task is documentation-only. Do not change:

```text
Sandboxie/
docs/plan/check-*.py
docs/plan/check-*.sh
```

If existing scripts cannot read fragments yet, stop after preparing the split
format and ask the code owner to update readers separately.

## Sanity Checks

Run read-only checks after each split batch:

```bash
rg -n "^---$|^kind: |^id: |^### (SREV|KPATH)-" docs/plan/ledger
rg -n "docs/plan/ledger/" docs/plan/systematic-code-review-ledger.md
```

Optional duplicate-id check:

```bash
python3 - <<'PY'
from pathlib import Path
import re

paths = [Path("docs/plan/systematic-code-review-ledger.md")]
paths += sorted(Path("docs/plan/ledger").glob("*.md"))

seen = {}
for path in paths:
    text = path.read_text()
    for match in re.finditer(r"^### ((?:SREV|KPATH)-[0-9A-Z]+):", text, re.M):
        seen.setdefault(match.group(1), []).append(str(path))

for review_id, owners in sorted(seen.items()):
    if len(owners) > 1:
        print(review_id, owners)
PY
```

No output means no duplicate full bodies.
