---
kind: srev-ledger-entry
id: SREV-039
title: API Copy String To User Counted String
status: patched-source-level-after-official-unicode-string-probeforwrite-shape-analysis-
owner: "Sandboxie/core/drv/api.c:1064-1082"
spec: docs/plan/srev-039-api-copy-string-to-user.md
schema: docs/plan/srev-039-api-copy-string-to-user.schema.json
checker: docs/plan/check-srev-039.py
runtime_gate: "home-path/process/box/config query APIs with normal output, too-small buffers, odd `MaximumLength`, and NULL-buffer/nonzero-length descriptors"
---
### SREV-039: API Copy String To User Counted String

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official UNICODE_STRING/ProbeForWrite shape analysis; needs Windows query API malformed-output-buffer proof |
| Evidence | `Sandboxie/core/drv/api.c:1064-1082` wrote driver strings into user `UNICODE_STRING64` buffers without first proving the helper input `len` was WCHAR-aligned, that nonzero `len` included at least one WCHAR and had a non-NULL source string, or that user `MaximumLength` was WCHAR-aligned before writing a WCHAR string and setting counted `Length`. |
| Data | Driver-owned NUL-terminated WCHAR strings returned through user `UNICODE_STRING64` descriptors by home-path, process-info, box-path, and config-query APIs. |
| Schema | Helper `len` is a byte count including the trailing NUL. Legal nonzero output is WCHAR-aligned, at least `sizeof(WCHAR)`, has a non-NULL source string, fits in aligned `MaximumLength`, and has a non-NULL user `Buffer`. Output `Length` excludes the copied trailing NUL. |
| Topology | Driver query APIs cross from internal path/config/process state into caller-provided output buffers; `Api_CopyStringToUser` owns the write-back shape before user memory is mutated. |
| Logic Risk | A future or malformed caller shape could produce an impossible `UNICODE_STRING64.Length`, write WCHAR data into an odd-sized user buffer contract, or rely on NULL source/user buffers for nonzero output. Existing callers appear to pass legal strings, so this is hardening rather than a confirmed current overflow path. |
| Official Shape | `docs/plan/srev-039-api-copy-string-to-user.md` records Microsoft `UNICODE_STRING` and `ProbeForWrite` references. `docs/plan/srev-039-api-copy-string-to-user.schema.json` records the small helper schema. |
| Fix | `Api_CopyStringToUser` now rejects odd `len`, nonzero `len < sizeof(WCHAR)`, nonzero output with NULL source string, odd user `MaximumLength`, and nonzero output with NULL user `Buffer`; it preserves `STATUS_BUFFER_TOO_SMALL` when output does not fit. |
| Acceptance Gate | `docs/plan/check-srev-039.py` validates the schema, official references, source guard order, and current caller surface; `docs/plan/check-srev-039.sh` is the matrix wrapper. Windows gate: home-path/process/box/config query APIs with normal output, too-small buffers, odd `MaximumLength`, and NULL-buffer/nonzero-length descriptors. |
