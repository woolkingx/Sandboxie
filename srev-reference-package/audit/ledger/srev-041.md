---
kind: srev-ledger-entry
id: SREV-041
title: API Copy Box Name Fixed String
status: patched-source-level-after-official-probeforread-and-local-box-isvalidname-shape
owner: "Sandboxie/core/drv/api.c:1021-1034"
spec: docs/plan/srev-041-api-copy-box-name.md
schema: docs/plan/srev-041-api-copy-box-name.schema.json
checker: docs/plan/check-srev-041.py
runtime_gate: explicit box-name APIs with normal, empty, invalid-character, and overlong unterminated names
---
### SREV-041: API Copy Box Name Fixed String

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official ProbeForRead and local Box_IsValidName shape analysis; needs Windows explicit-box-name malformed-input proof |
| Evidence | `Sandboxie/core/drv/api.c:1021-1034` probed `(BOXNAME_COUNT - 2)` WCHARs, copied with `wcsncpy` into a zeroed local `BOXNAME_COUNT` buffer, and then called `Box_IsValidName`. An overlong unterminated user box name could therefore be truncated into a different local box name before validation. |
| Data | User-provided explicit box-name C-strings passed to process and config APIs, copied into a kernel-owned `BOXNAME_COUNT` buffer. |
| Schema | Box name input is a user pointer, readable under the existing fixed cap with WCHAR alignment, non-empty, NUL-terminated before `BOXNAME_COUNT - 2`, and valid under `Box_IsValidName`. Overlong unterminated input is invalid, not truncated. |
| Topology | API helpers own user-to-kernel box-name copying; process/config logic receives only validated local box names before lookup, process start, or policy checks. |
| Logic Risk | Silent truncation can make downstream logic operate on a different box name than the caller supplied, crossing from user input shape into box topology with altered identity. |
| Official Shape | `docs/plan/srev-041-api-copy-box-name.md` records Microsoft `ProbeForRead` and local `Box_IsValidName` references. `docs/plan/srev-041-api-copy-box-name.schema.json` records the small helper schema. |
| Fix | `Api_CopyBoxNameFromUser` now rejects NULL, empty, and overlong unterminated input, probes with WCHAR alignment, copies until the first NUL, and removes `wcsncpy` truncation before `Box_IsValidName`. |
| Acceptance Gate | `docs/plan/check-srev-041.py` validates the schema, source helper shape, removal of `wcsncpy`, and current caller surface; `docs/plan/check-srev-041.sh` is the matrix wrapper. Windows gate: explicit box-name APIs with normal, empty, invalid-character, and overlong unterminated names. |
