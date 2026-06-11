---
kind: srev-ledger-entry
id: SREV-019
title: Rename/Link Target Length Is Truncated From ULONG To USHORT Before Policy Parse
status: patched-source-level-after-official-rename-link-and-minifilter-buffer-shape-anal
owner: "Sandboxie/core/drv/file_flt.c:809"
spec: docs/plan/srev-019-rename-link-length-spec.md
schema: docs/plan/srev-019-rename-link-length-spec.schema.json
checker: docs/plan/check-srev-019.sh
runtime_gate: long rename/link attempts and malformed InfoBuffers fail closed while ordinary rename/link operations still pass the existing policy path
---
### SREV-019: Rename/Link Target Length Is Truncated From ULONG To USHORT Before Policy Parse

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official rename/link and minifilter buffer-shape analysis; needs Windows runtime proof |
| Evidence | Explorer Hypatia reports `Sandboxie/core/drv/file_flt.c:809` and `file_flt.c:824` cast `FileNameLength` from `ULONG` to `USHORT` into `UNICODE_STRING.Length`. |
| Data | `FILE_RENAME_INFORMATION.FileNameLength` / `FILE_LINK_INFORMATION.FileNameLength`. |
| Schema | Policy parser length must match the target path length Windows will apply. |
| Topology | Sandboxed `SetInformation` rename/link request crosses into minifilter path policy. |
| Logic Risk | Length wrap can make Sandboxie evaluate a shorter/different target path than the filesystem operation. |
| Official Shape | `docs/plan/srev-019-rename-link-length-spec.md` records Microsoft `FILE_RENAME_INFORMATION`, `FILE_LINK_INFORMATION`, minifilter `SetFileInformation.Length`, and `InfoBuffer` shape. |
| Fix | `File_RenameOperation` now rejects zero, over-`MAXUSHORT`, odd-byte, and out-of-buffer target-name lengths before constructing the local `UNICODE_STRING` used by the policy parser. |
| Acceptance Gate | `docs/plan/check-srev-019.sh` proves the range/buffer gates precede the `USHORT` cast for both rename and hard-link targets. Windows gate: long rename/link attempts and malformed InfoBuffers fail closed while ordinary rename/link operations still pass the existing policy path. |
