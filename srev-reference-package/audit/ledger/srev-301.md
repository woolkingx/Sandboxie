---
kind: srev-ledger-entry
id: SREV-301
title: IPC Firefox Section View Protection Boundary
status: source-level classified after official section-view protection shape; comment-only source clarification, no behavior change
owner: Sandboxie/core/dll/ipc.c
spec: docs/plan/srev-301-ipc-firefox-section-view-protection-boundary.md
schema: docs/plan/srev-301-ipc-firefox-section-view-protection-boundary.schema.json
checker: docs/plan/check-srev-301.py
runtime_gate: Windows Firefox 146+ section-protection matrix with image-section and non-Firefox negative controls
---

### SREV-301: IPC Firefox Section View Protection Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official section-view protection shape; comment-only source clarification, no behavior change |
| Evidence | `Ipc_NtMapViewOfSection` has a Firefox 146+ branch for remote process maps where `Protect == PAGE_EXECUTE_READ`. It queries `SectionBasicInformation`, excludes image sections through `SEC_IMAGE`, and requests `PAGE_EXECUTE_READWRITE` for the native `NtMapViewOfSection` call. The old comment said a later `NtProtectVirtualMemory` call would produce `STATUS_SECTION_PROTECTION` and carried a disabled `BAM` monitor line, but did not name the section-protection owner or runtime matrix. |
| Data | `Ipc_NtMapViewOfSection`, `DLL_IMAGE_MOZILLA_FIREFOX`, `ProcessHandle`, `NtCurrentProcess`, `INVALID_HANDLE_VALUE`, `PAGE_EXECUTE_READ`, `NtQuerySection`, `SectionBasicInformation`, `SEC_IMAGE`, `PAGE_EXECUTE_READWRITE`, `__sys_NtMapViewOfSection`, and SREV-283. |
| Schema | `IPC_FIREFOX_SECTION_VIEW_PROTECTION_BOUNDARY` says `Ipc_NtMapViewOfSection` owns only the Firefox remote non-image section view protection policy; `ZwMapViewOfSection` owns requested view protection compatibility with the section page protection; `NtQuerySection(SectionBasicInformation)` owns the local `SEC_IMAGE` exclusion evidence; SREV-283 owns the adjacent `WriteProcessMemory` suppression for `NtMapViewOfSection` export-address targets; this SREV changes comments and proof only. |
| Topology | `Firefox image type -> remote ProcessHandle -> PAGE_EXECUTE_READ predicate -> NtQuerySection SectionBasicInformation -> non-image section predicate -> PAGE_EXECUTE_READWRITE request -> __sys_NtMapViewOfSection`. |
| Logic Risk | The previous wording described an observed symptom but not the API boundary. A future patch could treat the branch as a generic Firefox permission escalation, or remove it as stale, without testing the real `section creation protection -> requested view protection -> child-side local patch write -> STATUS_SECTION_PROTECTION` matrix. |
| Official Shape | Microsoft documents `ZwMapViewOfSection` as mapping a section view and requiring non-image `Win32Protect` to be compatible with the section's page protection; incompatible protection can return `STATUS_SECTION_PROTECTION`. Microsoft documents `ZwQuerySection` as returning section object information, and the local source uses `SectionBasicInformation` to read `SEC_IMAGE`. |
| Fix | The source comment now names SREV-301, the Firefox 146+ remote non-image section boundary, the child-side local patch-byte intent, and the Windows section-protection runtime matrix. It removes symptom-only `bug out` wording and the disabled `BAM` monitor line. No Firefox image-type check, remote-process check, `PAGE_EXECUTE_READ` predicate, `NtQuerySection` call, `SEC_IMAGE` exclusion, `PAGE_EXECUTE_READWRITE` rewrite, or native `__sys_NtMapViewOfSection` call changed. |
| Acceptance Gate | `docs/plan/check-srev-301.py` validates the draft-07 schema, official references, source comment owner, unchanged Firefox/non-image predicate, unchanged `PAGE_EXECUTE_READWRITE` rewrite, SREV-283 adjacency, stale wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-301.sh` is the targeted wrapper. Runtime gate: Windows Firefox 146+ section-protection matrix with image-section and non-Firefox negative controls. |
