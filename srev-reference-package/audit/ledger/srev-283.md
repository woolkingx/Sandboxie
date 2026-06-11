---
kind: srev-ledger-entry
id: SREV-283
title: WriteProcessMemory NTDLL Patch Suppression Owner
status: patched-comment-topology-after-official-writeprocessmemory-review-no-behavior-change
owner: Sandboxie/core/dll/file_misc.c
spec: docs/plan/srev-283-wpm-ntdll-patch-suppression-owner.md
schema: docs/plan/srev-283-wpm-ntdll-patch-suppression-owner.schema.json
checker: docs/plan/check-srev-283.py
runtime_gate: Windows Firefox/Thunderbird matrix inherited from SREV-075 plus target-address regression proof
---

### SREV-283: WriteProcessMemory NTDLL Patch Suppression Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official `WriteProcessMemory` review; no behavior change |
| Evidence | `File_WriteProcessMemory` has a non-compartment Firefox/Thunderbird branch that suppresses writes targeting the local `ntdll` export addresses for `NtSetInformationThread` or `NtMapViewOfSection`, returns success, and preserves `lpNumberOfBytesWritten` through the SREV-075 output gate. The remaining source comment still called the branch a third-party workaround. |
| Data | `File_WriteProcessMemory`, `Dll_CompartmentMode`, `Dll_ImageType`, `DLL_IMAGE_MOZILLA_FIREFOX`, `DLL_IMAGE_MOZILLA_THUNDERBIRD`, `lpBaseAddress`, `GetProcAddress(Dll_Ntdll, "NtSetInformationThread")`, `GetProcAddress(Dll_Ntdll, "NtMapViewOfSection")`, `lpNumberOfBytesWritten`, SREV-075, and `__sys_WriteProcessMemory`. |
| Schema | `WPM_NTDLL_PATCH_SUPPRESSION_OWNER` says `WriteProcessMemory` writes data to memory in a specified process; the target range must be accessible or the operation fails; `lpNumberOfBytesWritten` is optional and NULL may be ignored; `File_WriteProcessMemory` owns only the Firefox/Thunderbird `ntdll` patch suppression branch; the suppression branch is legal only for `NtSetInformationThread` and `NtMapViewOfSection` export-address targets; SREV-075 owns the fake-success output-parameter gate; non-matching writes must flow to the real `__sys_WriteProcessMemory` owner; this SREV changes comments and proof only. |
| Topology | `WriteProcessMemory call -> File_WriteProcessMemory hook -> non-compartment Firefox/Thunderbird image gate -> selected ntdll export-address gate -> fake success with SREV-075 output gate`. All non-matching writes can be hook-traced and then continue to `__sys_WriteProcessMemory`. |
| Logic Risk | Generic workaround wording can hide the narrow owner boundary and lead to expanding the fake-success branch to more image types or target addresses without proof. It can also hide that once Sandboxie bypasses the real API owner, it must preserve `WriteProcessMemory` output semantics through SREV-075. |
| Official Shape | Microsoft documents `WriteProcessMemory` as writing data to memory in a specified process, requiring the target range to be accessible, and treating `lpNumberOfBytesWritten` as optional. |
| Fix | Comment-only source clarification. The source now names SREV-283 and states that the branch suppresses only Firefox/Thunderbird writes to selected `ntdll` export addresses, while SREV-075 owns the fake-success output contract. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-283.py` validates the draft-07 schema, official reference, source predicate, selected `ntdll` exports, SREV-075 output gate adjacency, real fallback preservation, stale workaround wording removal, and ledger fragment; `docs/plan/check-srev-283.sh` is the targeted wrapper. Runtime gate: Windows Firefox/Thunderbird matrix inherited from SREV-075, plus target-address regression proof that only `NtSetInformationThread` and `NtMapViewOfSection` writes enter the fake-success branch while other `WriteProcessMemory` calls reach the real API owner. |
