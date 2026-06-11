---
kind: srev-ledger-entry
id: SREV-013
title: Relative Path Canonicalizer Uses Unsigned Index For Parent Traversal
status: patched-source-level-after-official-relative-symlink-shape-and-local-canonicaliz
owner: "Sandboxie/core/dll/file_dir.c:3210"
spec: docs/plan/srev-013-relative-symlink-canonicalizer.md
schema: docs/plan/srev-013-relative-symlink-canonicalizer.schema.json
checker: docs/plan/check-srev-013.sh
runtime_gate: "relative symlink targets `target`, `.\\target`, `..\\target`, excessive `..\\..\\...`, and root/base edge cases are exercised"
---
### SREV-013: Relative Path Canonicalizer Uses Unsigned Index For Parent Traversal

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official relative-symlink shape and local canonicalizer analysis; needs Windows runtime proof |
| Evidence | Explorer Ohm reports `Sandboxie/core/dll/file_dir.c:3210` checks `j >= 0` while `j` is `ULONG`; relative symlink handling reaches it from `file_dir.c:3323-3326` and `file_link.c:1067-1072`. |
| Data | Base absolute path plus relative reparse target containing `..\`. |
| Schema | Parent traversal must stop at a defined root floor; unsigned index underflow is not a valid root check. |
| Topology | Reparse/link target normalization creates the path that Sandboxie policy later evaluates. |
| Logic Risk | Excess parent traversal can underflow and write outside the result buffer or produce a policy path different from intended target. |
| Official Shape | `docs/plan/srev-013-relative-symlink-canonicalizer.md` records MS-FSCC symlink relative-path and dot-directory semantics. |
| Fix | `File_CanonizePath` now treats the relative target as length-bounded, bounds all dot-segment lookahead, computes a root floor, fails if `..` climbs above it, and `File_SetReparsePoint` fails closed when relative target canonicalization cannot produce an absolute path. |
| Acceptance Gate | `docs/plan/check-srev-013.sh` proves the unsigned `j >= 0` check is gone, bounded lookahead is present, and relative canonicalization failure no longer falls through as if the original relative buffer were an absolute target. Windows gate: relative symlink targets `target`, `.\target`, `..\target`, excessive `..\..\...`, and root/base edge cases are exercised. |
