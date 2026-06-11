---
kind: srev-ledger-entry
id: SREV-097
title: Zw Redirector HAL7600 Skip Contract
status: source-level-classified-after-official-nt-zw-native-service-intel-instruction-re
owner: Sandboxie/core/drv/hook.c
spec: docs/plan/srev-097-zw-redirector-hal7600-skip-contract.md
schema: docs/plan/srev-097-zw-redirector-hal7600-skip-contract.schema.json
checker: docs/plan/check-srev-097.py
runtime_gate: "Windows x86/x64 matrix with clean ntoskrnl Zw stubs, HAL7600-style modified `ZwLockProductActivationKeys` stubs, Driver Verifier import redirection, and service lookup for both Nt and Zw outputs"
---
### SREV-097: Zw Redirector HAL7600 Skip Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official Nt/Zw native-service, Intel instruction-reference, read-only kernel memory, and instruction-cache shape; comment-only source clarification, no behavior change |
| Evidence | `Sandboxie/core/drv/hook.c` maps a service index to both `NtService` and `ZwService` by calling `Hook_GetNtServiceInternal` and `Hook_GetZwServiceInternal`. `Sandboxie/core/drv/hook_32.c` and `Sandboxie/core/drv/hook_64.c` scan ntoskrnl `ZwXxx` redirector bytes. Microsoft documents native services as `Nt`/`Zw` routines serviced by kernel-mode system routines. Intel's official instruction-set reference is the opcode source for the local byte patterns. The HAL7600 branch recognizes `33 C0 C2 08 00` on x86 and `33 C0 C3` on x64, then advances to the next original redirector boundary instead of accepting the replacement stub. |
| Data | `Hook_GetService`, service index, `Hook_GetZwServiceInternal`, x86 `Hook_Find_ZwRoutine_1` / fallback `Hook_Find_ZwRoutine_2`, x64 `Hook_Find_ZwRoutine`, HAL7600 replacement stub bytes, original x86 `ret 8` boundary, original x64 `66 90` padding boundary, and ordinary Zw redirector parser. |
| Schema | `ZW_REDIRECTOR_HAL7600_SKIP_CONTRACT` says `Hook_GetZwServiceInternal` scans kernel Zw redirector bytes only to locate an existing stub; the HAL7600 branch is a scanner skip over a known replacement stub; the 32-bit HAL7600 pattern is `33 C0 C2 08 00` followed by the original `ret 8`; the 64-bit HAL7600 pattern is `33 C0 C3` followed by original `66 90` padding; Sandboxie must not treat the replacement stub as a legal Zw redirector; Sandboxie must not patch kernel code from this scanner branch; ordinary x86/x64 redirector parsing remains unchanged. |
| Topology | `Hook_GetService` resolves the service number from user-mode `DllProc`, resolves the Nt service body, then optionally resolves the Zw redirector. The x86 scanner walks ordered Zw stubs and skips HAL7600's replacement body by finding the preserved original `ret 8` boundary. The x64 scanner derives an ntoskrnl export scan range, skips HAL7600's replacement body by finding the preserved `66 90` boundary, and otherwise parses the ordinary x64 Zw redirector sequence. |
| Logic Risk | The old `$Workaround$` label hid the distinction between a scanner exception and a patching strategy. Treating the replacement stub as a legal redirector returns the wrong address. Treating the branch as permission to patch kernel code conflicts with Microsoft guidance that read-only kernel code writes can bugcheck and with the instruction-cache coherency requirement for executable-code mutation. |
| Official Shape | `docs/plan/srev-097-zw-redirector-hal7600-skip-contract.md` records Microsoft Nt/Zw native-service, Intel instruction-reference, read-only kernel memory, and `FlushInstructionCache` references. `docs/plan/srev-097-zw-redirector-hal7600-skip-contract.schema.json` records the JSON Schema draft-07 local `ZW_REDIRECTOR_HAL7600_SKIP_CONTRACT` contract. |
| Fix | Comment-only source clarification: the vague `$Workaround$ - 3rd party fix` labels in `hook_32.c` and `hook_64.c` were replaced with explicit HAL7600 byte-pattern contracts and a statement that the branch is a scanner skip, not a legal Zw redirector shape and not code-patching permission. No runtime behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-097.py` validates the draft-07 schema, official references, local `Hook_GetService` topology, exact x86/x64 HAL7600 byte-pattern predicates, original-boundary search, stale `$Workaround$` removal, ordinary Zw redirector parsing preservation, and ledger entry; `docs/plan/check-srev-097.sh` is the matrix wrapper. Runtime gate: Windows x86/x64 matrix with clean ntoskrnl Zw stubs, HAL7600-style modified `ZwLockProductActivationKeys` stubs, Driver Verifier import redirection, and service lookup for both Nt and Zw outputs. |
