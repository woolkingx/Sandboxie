---
kind: srev-ledger-entry
id: SREV-272
title: File Query-By-Name Delete-Mark Class Gate
status: patched-comment-topology-after-official-query-by-name-output-class-review-no-behavior-change
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-272-file-query-by-name-delete-mark-class-gate.md
schema: docs/plan/srev-272-file-query-by-name-delete-mark-class-gate.schema.json
checker: docs/plan/check-srev-272.py
runtime_gate: Windows NtQueryInformationByName class matrix with copy-path delete-marker cases
---

### SREV-272: File Query-By-Name Delete-Mark Class Gate

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official query-by-name output-class review; no behavior change |
| Evidence | `File_NtQueryInformationByName` first queries the sandbox copy path. If that copy-path query succeeds or returns a status other than name/path-not-found, it leaves before trying the true path. The source had a bare `// todo` above a commented-out legacy delete-mark check that treated `FileInformation` as if it always had a `CreationTime` member. |
| Data | `File_NtQueryInformationByName`, `FileInformationClass`, `FileInformation`, `Length`, `CopyPath`, `__sys_NtQueryInformationByName`, `File_Delete_v2`, `IS_DELETE_MARK`, `FILE_BASIC_INFORMATION.CreationTime`, and the copy-path leave-before-true-path decision. |
| Schema | `FILE_QUERY_BY_NAME_DELETE_MARK_CLASS_GATE` says `NtQueryInformationByName` output layout is owned by `FileInformationClass`; delete-mark filtering may inspect `CreationTime` only for classes whose output schema has a compatible `CreationTime` member and when `Length` covers that field; `FileInformation` must not be treated as `FILE_BASIC_INFORMATION` for all query-by-name classes; the current commented legacy check remains disabled until a class-specific parser is added; this SREV changes comments and proof only, while copy-path/true-path routing and delete-v2 policy are unchanged. |
| Topology | `caller NtQueryInformationByName -> ObjectAttributes / FileInformationClass / output buffer -> Sandboxie copy-path query -> class-specific output layout -> future delete-mark parser only after class + Length proof -> leave on copy-path result or continue to true-path fallback`. |
| Logic Risk | Re-enabling the old check blindly would couple the delete-marker policy to the wrong schema. Some query-by-name classes do not expose `CreationTime` in the same position, and a short `Length` can make even a compatible class unsafe to inspect. Leaving the bare `todo` also hides the reason the code is disabled and invites a future accidental `PVOID` reinterpretation. |
| Official Shape | Microsoft documents `NtQueryInformationByName` as returning file information by name without opening the file; `FileInformation` is a caller-supplied buffer whose structure is determined by `FileInformationClass`. Microsoft documents `FILE_BASIC_INFORMATION` as a distinct structure with `CreationTime`, other timestamps, and file attributes. |
| Fix | Comment-only source clarification. The bare `// todo` now names SREV-272 and states that delete-mark filtering for `NtQueryInformationByName` requires a class-specific output parser and a length gate before treating `FileInformation` as a structure with `CreationTime`. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-272.py` validates the draft-07 schema, official references, source comment owner, disabled legacy check, copy-path query topology, absence of the bare `// todo`, and the ledger fragment; `docs/plan/check-srev-272.sh` is the targeted wrapper. Runtime gate: Windows `NtQueryInformationByName` matrix for supported `FileInformationClass` values, including copy-path delete-marker cases, proving any future class-specific parser hides deleted copy-path entries without reading outside the returned buffer or misclassifying unsupported classes. |
