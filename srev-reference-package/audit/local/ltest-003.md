---
kind: local-test-entry
id: LTEST-003
title: UAC Packet ReadProcessMemory Access Denied
status: runtime-capture-open-no-source-change
owner: Sandboxie/core/svc/serviceserver2.cpp
paths:
  - Sandboxie/core/svc/serviceserver2.cpp
  - Sandboxie/core/dll/secure.c
spec: docs/plan/local/ltest-003-uac-packet-readprocessmemory-access-denied.md
schema: n/a
checker: docs/plan/local/check-ltest-003.py
runtime_gate: Windows Notepad++ installer elevation smoke with UAC packet owner, proxy process, handle rights, token flags, VirtualQueryEx page state, and COMRuntime 18221 correlation captured before any behavior change
---
### LTEST-003: UAC Packet ReadProcessMemory Access Denied

| Field | Content |
|---|---|
| Severity | [medium] |
| Status | runtime capture open; no source change |
| Evidence | Runtime log showed `SBIE2218 [84 / 00000005]` followed by `SBIE2219 Start.exe [DefaultBox]` while `Start.exe /elevate` was launching `npp.8.5.6.Installer.x64.exe`. Windows Application log showed repeated COMRuntime 18221 RPCSS access-denied warnings for `C:\temp\Sandboxie-Plus\Start.exe` at the same time. |
| Data | `SECURE_UAC_PACKET`, `pkt_addr`, `pkt_len`, `RunUacSlave3`, `ReadProcessMemory`, `ERROR_ACCESS_DENIED`, `COMRuntime 18221`, `Start.exe /elevate`, and `DefaultBox`. |
| Topology | `Start.exe /elevate -> secure.c Secure_HandleElevation builds packet -> MSGID_SERVICE_UAC -> serviceserver2.cpp UacHandler2 -> UAC proxy -> RunUacSlave3 -> ReadProcessMemory(pkt_addr)`. |
| Logic Risk | Patching this by loosening config or mutating certificate/test state would hide a real UAC bridge ownership problem. The correct next step is runtime capture of packet ownership, proxy identity, handle rights, token state, and page state. |
| Fix | None yet. This is a local-only runtime capture entry. |
| Acceptance Gate | `docs/plan/local/check-ltest-003.py` validates the local ledger, spec, source coordinates, runtime evidence, hypothesis, capture plan, and no-source-change boundary. |
