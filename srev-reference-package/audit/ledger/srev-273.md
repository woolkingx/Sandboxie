---
kind: srev-ledger-entry
id: SREV-273
title: File Final Path Volume-Name Owner
status: patched-comment-topology-after-official-final-path-volume-name-review-no-behavior-change
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-273-file-final-path-volume-name-owner.md
schema: docs/plan/srev-273-file-final-path-volume-name-owner.schema.json
checker: docs/plan/check-srev-273.py
runtime_gate: Windows GetFinalPathNameByHandleW mounted-folder volume-name matrix
---

### SREV-273: File Final Path Volume-Name Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official final-path volume-name review; no behavior change |
| Evidence | `File_GetFinalPathNameByHandleW_2` builds caller-visible final path strings for Sandboxie's DLL hook. Its permanent-link branch had example-path comments explaining that a mounted-folder true path may refer to the mount location rather than the target volume, then described a non-DOS conversion back to the target device and a DOS drive-letter presentation. The comments did not name the API owner or the volume-name flag contract. |
| Data | `File_GetFinalPathNameByHandleW_2`, `TruePath`, `dwFlags`, `VOLUME_NAME_DOS`, `VOLUME_NAME_GUID`, `VOLUME_NAME_NONE`, `VOLUME_NAME_NT`, `File_Mup`, `File_FindPermLinksForMatchPath`, `File_FixPermLinksForMatchPath`, `File_GetDriveForPath`, `FILE_LINK.src_len`, `FILE_LINK.dst_len`, `suffix`, `suffix2`, `drive_letter`, and final path construction. |
| Schema | `FILE_FINAL_PATH_VOLUME_NAME_OWNER` says `File_GetFinalPathNameByHandleW_2` owns caller-visible final-path presentation for the Sandboxie DLL hook; `GetFinalPathNameByHandleW` volume-name flags select the returned volume identity; `VOLUME_NAME_DOS` returns a drive-letter path, `VOLUME_NAME_NT` returns the NT device object path, `VOLUME_NAME_NONE` returns a path with no drive information, and GUID output remains delegated to `File_GetFinalPathNameByHandleW_3`; mounted-folder permanent-link matches use the target device identity for NT/NONE output and the mounted-location drive identity plus mounted-folder suffix for DOS output; this SREV changes comments and proof only. |
| Topology | `open file handle -> Sandboxie true NT path -> File_GetFinalPathNameByHandleW_2(dwFlags) -> MUP / GUID / permanent-link / ordinary-drive classification -> caller-visible final path string`. In the permanent-link branch, NT/NONE routes through `File_FixPermLinksForMatchPath` and strips `file_link->src_len`; DOS routes through `File_GetDriveForPath(TruePath)` or `File_GetDriveForPath(file_link->src)` and may append `suffix2 = TruePath + file_link->dst_len`. |
| Logic Risk | Without the owner comment, a future edit could treat the mounted-folder block as raw path cleanup and collapse target-device identity and mounted-location drive identity. That would break the `GetFinalPathNameByHandleW` flag contract even if the resulting string looked plausible for one caller. |
| Official Shape | Microsoft documents `GetFinalPathNameByHandleW` volume-name flags as selecting drive-letter, volume GUID, no-drive, or NT device object output. Microsoft documents mounted folders as an association between a volume and a directory on another volume. Microsoft volume naming docs describe drive-letter paths, volume GUID paths, and volume mount points. |
| Fix | Comment-only source clarification. The mounted-folder block now names SREV-273 and states that `GetFinalPathNameByHandleW` volume-name flags select the caller-visible identity: target device for NT/NONE output and mounted-location drive for DOS output. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-273.py` validates the draft-07 schema, official references, source comment owner, mounted-folder permanent-link branch, NT/NONE target-device route, DOS mounted-location drive route, SREV-143/SREV-223/SREV-271 adjacency, stale example-path comment removal, and the ledger fragment; `docs/plan/check-srev-273.sh` is the targeted wrapper. Runtime gate: Windows mounted-folder matrix for `GetFinalPathNameByHandleW(VOLUME_NAME_DOS)`, `GetFinalPathNameByHandleW(VOLUME_NAME_NT)`, `GetFinalPathNameByHandleW(VOLUME_NAME_NONE)`, and `GetFinalPathNameByHandleW(VOLUME_NAME_GUID)`, covering drive-letter, mounted-folder, no-drive-letter, volume-GUID, and UNC/MUP inputs. |
