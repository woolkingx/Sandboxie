# Core Coverage Audit

This checkpoint records what the current SREV/KPATH pass proves and what it
does not prove.

## Scope

Owner tree:

```text
Sandboxie/core
```

Current review ledger:

```text
docs/plan/systematic-code-review-ledger.md
```

Coverage checker:

```text
docs/plan/check-core-coverage.py
```

Open runtime gate checker:

```text
docs/plan/check-open-runtime-gates.py
```

## Data

`Sandboxie/core` contains 287 files at this checkpoint. The current SREV/KPATH
pass records 352 ledger entries and proves their local source gates. That is not
equivalent to full file-by-file closure.

The checker reports:

```text
core_files=287
reviewable_core_files=276
ledger_entries=352
reviewable_files_named_in_ledger=276
reviewable_files_not_named_in_ledger=0
comment_risk_hits=0
comment_risk_hits_in_files_not_named_in_ledger=0
patched_source_needs_windows=231
policy_or_runtime_open=0
runtime_design_open=0
named_runtime_capture=0
```

## Schema

Coverage has three separate states:

| State | Meaning |
|---|---|
| ledger-named | A core file is mentioned by an SREV/KPATH record. |
| source-gated | A finding has a checker proving the local source shape. |
| runtime-proved | A Windows/WDK/VM/live gate proves the path behavior. |

Only the second state is broadly available today. Many ledger rows explicitly
still require Windows runtime proof.

## Topology

The current review topology is:

```text
core source -> SREV/KPATH ledger -> source checker -> runtime gate
```

The missing topology is:

```text
all core files -> coverage map -> uncovered risk queue -> SREV/KPATH candidate
```

`check-core-coverage.py` supplies that missing map and keeps the open-risk queue
from being hidden behind passing source gates.

When uncovered comment risks reach zero, the checker prints
`TOP_UNNAMED_REVIEWABLE_FILES` to keep file coverage moving. That queue is a
heuristic risk ranking, not a proof of defect; every selected file still needs
the same official/API shape check before source changes.

## Logic

Do not claim `core/` complete while any of these remain true:

- reviewable core files are not named in the ledger;
- comment-admitted risks are not either resolved or explicitly classified;
- source-gated rows still say `needs Windows ... proof`;
- policy/runtime rows still say `open`, `capture required`, or `design still open`.

The remaining `runtime_design_open` and `named_runtime_capture` rows are tracked
by `check-open-runtime-gates.py`. It validates that each open row still has a
split-ledger front matter owner, spec, schema, checker, runtime gate, and a
concrete runtime/capture matrix.

Current open runtime/capture inventory:

| ID | Kind | Owner | Runtime proof route |
|---|---|---|---|

## Next Candidate Queue

The checker prints uncovered comment-admitted risk lines first. The next SREV
candidate should be selected from that queue only after checking whether an
existing SREV/KPATH already owns the same data shape.

High-signal candidates from the checker output after SREV-352:

| Candidate | Evidence | First gate |
|---|---|---|
| Covered comment-risk queue | `check-core-coverage.py` now reports zero reviewable files not named in the ledger and no comment-risk hits in unnamed files. The next pass should select from covered risk hotspots or open runtime-policy rows rather than unnamed file coverage. | Keep using official/API shape first; do not treat covered source gates as runtime proof. |

These are candidates, not fixes. Each still needs the usual official/API shape
check before a behavior change.
