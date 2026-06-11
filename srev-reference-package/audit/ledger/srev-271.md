---
kind: srev-ledger-entry
id: SREV-271
title: FileNameInformation Volume Relative Owner
status: patched-comment-topology-after-official-filename-volume-and-srev-143-review-no-behavior-change
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-271-file-name-info-volume-relative-owner.md
schema: docs/plan/srev-271-file-name-info-volume-relative-owner.schema.json
checker: docs/plan/check-srev-271.py
runtime_gate: Windows mounted-folder/no-drive-letter/volume-GUID/drive-letter/UNC FileNameInformation matrix
---

### SREV-271: FileNameInformation Volume Relative Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official FileNameInformation, volume, mounted-folder, and SREV-143 review; no behavior change |
| Evidence | `File_NtQueryInformationFile` intercepts `FileNameInformation` and writes a `FILE_NAME_INFORMATION`-compatible output buffer. The local hook asks `File_GetName` for the true path, then normalizes Sandboxie path topology back to the name shape callers expect. Covered comment-risk sites described mounted-folder paths and a `todo: fix-me` GUID fallback, but did not name the owner boundary. |
| Data | `File_NtQueryInformationFile`, `FileNameInformation`, `FILE_NAME_INFORMATION.FileNameLength`, `File_GetName`, `TruePath`, `File_FindPermLinksForMatchPath`, `FILE_LINK.dst_len`, `File_Mup`, `SbieDll_TranslateNtToDosPath`, `File_GetGuidForPath`, `FILE_GUID.len`, `File_DrivesAndLinks_CritSec`, and the final returned name buffer. |
| Schema | `FILE_NAME_INFO_VOLUME_RELATIVE_OWNER` says `File_NtQueryInformationFile` owns the presentation shape for intercepted `FileNameInformation` output; returned disk names are root-relative to the caller-visible volume identity, not raw Sandboxie link storage paths; mounted-folder matches from `File_FindPermLinksForMatchPath` must strip the destination prefix and release `File_DrivesAndLinks_CritSec`; if NT-to-DOS translation fails but `File_GetGuidForPath` finds a known volume identity, the returned name strips the GUID/device prefix and releases the same lock; this SREV changes comments and proof only, while SREV-143 still owns permanent-link and GUID metadata correctness. |
| Topology | `open file handle -> File_NtQueryInformationFile(FileNameInformation) -> File_GetName true path -> mounted-folder / MUP / DOS-drive / GUID classification -> root-relative returned FileNameInformation payload`. Mounted-folder flow strips `file_link->dst_len`; GUID fallback strips `guid->len`. |
| Logic Risk | The source was doing the right style of topology conversion but described it as symptom prose and a `todo`. That invites future changes to treat this as a formatting cleanup instead of a volume-identity boundary. Removing either strip without reproving mounted-folder, no-drive-letter volume, and GUID paths would return an internal mount location instead of the caller-visible relative name. |
| Official Shape | Microsoft documents `NtQueryInformationFile(FileNameInformation)` as returning `FILE_NAME_INFORMATION`, where full paths begin with one backslash and can be root-relative to the volume; `FILE_NAME_INFORMATION.FileNameLength` is a byte count; and volume GUID paths / mounted folders are alternate volume identities. |
| Fix | Comment-only source clarification. The mounted-folder block now names SREV-271 and says the returned name is root-relative to the target volume. The GUID fallback block no longer carries `todo: fix-me`; it says the branch handles NT paths with no DOS drive presentation by stripping a known volume identity prefix. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-271.py` validates the draft-07 schema, official references, SREV-143 adjacency, source comment owners, mounted-folder prefix stripping, GUID fallback prefix stripping, `File_DrivesAndLinks_CritSec` release paths, removal of stale `todo: fix-me` wording from this block, and the ledger fragment; `docs/plan/check-srev-271.sh` is the targeted wrapper. Runtime gate: Windows mounted-folder volume, no-drive-letter volume, volume GUID path, ordinary drive-letter path, and UNC/MUP matrix for `NtQueryInformationFile(FileNameInformation)`, proving returned names remain root-relative where required and do not leak Sandboxie internal mount-location prefixes. |
