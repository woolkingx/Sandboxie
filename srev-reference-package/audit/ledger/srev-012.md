---
kind: srev-ledger-entry
id: SREV-012
title: Reparse Point Buffer Parser Trusts Embedded Offsets And Lengths
status: patched-source-level-after-official-fsctl-reparse-schema-analysis-needs-windows-
owner: "Sandboxie/core/dll/file_dir.c:3317"
spec: docs/plan/srev-012-reparse-buffer-spec.md
schema: docs/plan/srev-012-reparse-buffer-spec.schema.json
checker: docs/plan/check-srev-012.sh
runtime_gate: malformed symlink/mount-point buffers fall through to native validation or fail without DLL-side out-of-bounds reads; valid absolute symlink and mount-point creation still rewrites target paths
---
### SREV-012: Reparse Point Buffer Parser Trusts Embedded Offsets And Lengths

| Field | Content |
|---|---|
| Severity | [blocker] |
| Status | patched source-level after official FSCTL/reparse schema analysis; needs Windows runtime proof |
| Evidence | Explorer Ohm reports `Sandboxie/core/dll/file_dir.c:3317` reads `REPARSE_DATA_BUFFER` path offsets/lengths before proving they fit in `DataLen`, then copies `PrintNameLength + sizeof(WCHAR)` at `file_dir.c:3425`. |
| Data | Caller-provided `REPARSE_DATA_BUFFER` from `FSCTL_SET_REPARSE_POINT`. |
| Schema | Tag-specific minimum size, even offsets/lengths, and `offset + length <= DataLen - header` must hold before path parsing or copying. |
| Topology | Sandboxed process buffer crosses into reparse-point rewrite hook before native `NtFsControlFile`. |
| Logic Risk | Malformed path-buffer offsets can cause out-of-bounds reads or policy decisions over an illegal path shape. |
| Official Shape | `docs/plan/srev-012-reparse-buffer-spec.md` records Microsoft FSCTL, `REPARSE_DATA_BUFFER`, `FsRtlValidateReparsePointBuffer`, symlink, and mount-point shape. |
| Fix | `File_SetReparsePoint` now checks fixed tag-specific fields are present, `ReparseDataLength` fits inside `DataLen`, substitute/print name byte ranges are WCHAR-aligned and inside `PathBuffer`, generated reparse data fits the maximum reparse buffer size, and old print-name copying synthesizes its own output terminator instead of reading one from caller memory. |
| Acceptance Gate | `docs/plan/check-srev-012.sh` proves the parser has a local range gate and no longer copies `PrintNameLength + sizeof(WCHAR)` from the caller print name. Windows gate: malformed symlink/mount-point buffers fall through to native validation or fail without DLL-side out-of-bounds reads; valid absolute symlink and mount-point creation still rewrites target paths. |
