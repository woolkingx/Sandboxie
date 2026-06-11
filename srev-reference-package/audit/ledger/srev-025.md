---
kind: srev-ledger-entry
id: SREV-025
title: SAMR SetSecurityObject Needed By SandboxieCrypto Has No Trusted-Image Gate
status: patched-source-level-after-official-ms-samr-opnum-analysis-needs-windows-sandbox
owner: "Sandboxie/core/drv/ipc_sam.c:106"
spec: docs/plan/srev-025-samr-set-security-object.md
schema: docs/plan/srev-025-samr-set-security-object.schema.json
checker: docs/plan/check-srev-025.sh
runtime_gate: SandboxieCrypto completes the needed SAM call; non-Sandboxie sandboxed callers remain denied; other SAM mutation opnums stay denied
---
### SREV-025: SAMR SetSecurityObject Needed By SandboxieCrypto Has No Trusted-Image Gate

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official MS-SAMR opnum analysis; needs Windows SandboxieCrypto/SAMR runtime proof |
| Evidence | `Sandboxie/core/drv/ipc_sam.c:106` blocked opnum `0x02` with a source comment saying `SandboxieCrypto.exe` needs this sometimes and suggesting `if(proc->image_sbie) break;`. |
| Data | SAMR RPC opnum extracted from `\RPC Control\samss lpc` request. |
| Schema | MS-SAMR opnum 2 is `SamrSetSecurityObject`, a security-descriptor update operation for server/domain/user/group/alias objects. |
| Topology | Sandboxed process RPC request crosses driver IPC SAM endpoint policy before reaching SAM. `proc->image_sbie` marks images loaded from the Sandboxie install directory. |
| Logic Risk | Denying opnum 2 for all callers breaks trusted SandboxieCrypto compatibility; allowing it broadly would expose a SAM security-descriptor mutation path to ordinary sandboxed clients. |
| Official Shape | `docs/plan/srev-025-samr-set-security-object.md` records Microsoft MS-SAMR `SamrSetSecurityObject` opnum and object-scope semantics. |
| Fix | Opnum 2 now bypasses the deny list only when `proc->image_sbie` is true. Ordinary sandboxed clients still fall through to the existing mutating-SAM deny path. |
| Acceptance Gate | `docs/plan/check-srev-025.sh` proves the old fixme is gone and opnum 2 has a `proc->image_sbie` trusted-image exception before the deny-list fallthrough. Windows gate: SandboxieCrypto completes the needed SAM call; non-Sandboxie sandboxed callers remain denied; other SAM mutation opnums stay denied. |
