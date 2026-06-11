---
kind: srev-ledger-entry
id: SREV-038
title: API Copy String From User Counted String
status: patched-source-level-after-official-unicode-string-probeforread-shape-analysis-n
owner: "Sandboxie/core/drv/api.c:1090-1111"
spec: docs/plan/srev-038-api-copy-string-from-user.md
schema: docs/plan/srev-038-api-copy-string-from-user.schema.json
checker: docs/plan/check-srev-038.py
runtime_gate: "`API_UPDATE_CONF` with normal, empty, odd-length, `Length > MaximumLength`, NULL-buffer/nonzero-length, and embedded-NUL setting values"
---
### SREV-038: API Copy String From User Counted String

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official UNICODE_STRING/ProbeForRead shape analysis; needs Windows API_UPDATE_CONF malformed-input proof |
| Evidence | `Sandboxie/core/drv/api.c:1090-1111` copied a user `UNICODE_STRING64` into a driver-owned NUL-terminated string using `*len = Length + sizeof(WCHAR)` for both user probing and copying, then wrote the terminator at `(*str)[*len / sizeof(WCHAR)]`, one WCHAR past the allocated block. It also did not validate `Length <= MaximumLength`, did not reject nonzero `Length` with a NULL buffer before probing/copying, and returned a C-string projection even if the counted payload contained an embedded NUL. |
| Data | User-mode `UNICODE_STRING64` setting value passed through `Conf_Api_Update` into `Api_CopyStringFromUser`, then stored as a NUL-terminated config setting string. |
| Schema | `UNICODE_STRING64.Length` is bytes, WCHAR-aligned, and `<= MaximumLength`. Nonzero `Length` requires a non-NULL `Buffer`. The helper returns a driver-owned C-string projection, so embedded NUL in the counted payload is invalid. |
| Topology | `API_UPDATE_CONF` crosses from caller-provided update payload into driver config state; `Api_CopyStringFromUser` owns the user-to-driver string boundary, while `Conf_Update` owns config mutation. |
| Logic Risk | A malformed counted string can make the helper read one WCHAR beyond the counted user payload, write the local terminator one WCHAR past the allocation, make config state consume a truncated value, accept an impossible `Length/MaximumLength` pair, or rely on zero-length undefined copy behavior from a NULL pointer. |
| Official Shape | `docs/plan/srev-038-api-copy-string-from-user.md` records Microsoft `UNICODE_STRING` and `ProbeForRead` references. `docs/plan/srev-038-api-copy-string-from-user.schema.json` records the small helper schema. |
| Fix | `Api_CopyStringFromUser` now probes/copies only `UNICODE_STRING64.Length` bytes, writes the terminator at `Length / sizeof(WCHAR)`, validates `Length <= MaximumLength`, rejects nonzero length with NULL `Buffer`, avoids zero-length copy from a NULL user pointer, rejects embedded NUL after copy, and frees/resets the output on malformed embedded-NUL input. |
| Acceptance Gate | `docs/plan/check-srev-038.py` validates the schema, official references, source guard order, embedded-NUL cleanup branch, and `Conf_Api_Update` caller; `docs/plan/check-srev-038.sh` is the matrix wrapper. Windows gate: `API_UPDATE_CONF` with normal, empty, odd-length, `Length > MaximumLength`, NULL-buffer/nonzero-length, and embedded-NUL setting values. |
