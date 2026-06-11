---
kind: srev-ledger-entry
id: SREV-071
title: IPC Async Start Handoff
status: patched-source-level-after-official-createthread-process-information-wait-handle
owner: Sandboxie/core/dll/ipc_start.c
spec: docs/plan/srev-071-ipc-async-start-handoff.md
schema: docs/plan/srev-071-ipc-async-start-handoff.schema.json
checker: docs/plan/check-srev-071.py
runtime_gate: "normal async service-start handoff, payload allocation failure, `CreateThread` failure, server process early-exit detection, and DcomLaunch follow-up wait"
---
### SREV-071: IPC Async Start Handoff

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official CreateThread/PROCESS_INFORMATION/wait-handle shape and local async handoff analysis; needs Windows IPC service-start runtime proof |
| Evidence | `Sandboxie/core/dll/ipc_start.c` async mode packages `TruePath`, `service`, `hServerEvent`, and `hServerProcess` into a four-slot payload and passes it as `CreateThread` `lpParameter`. Microsoft documents `CreateThread` as returning a thread handle on success and `NULL` on failure, and documents created process/thread handles as requiring `CloseHandle` when finished. Before this patch, the async path wrote into the payload without checking allocation success; if `CreateThread` failed, the payload was not freed and the event/process handles were not transferred to a worker or closed by the synchronous wait path. |
| Data | Async handoff payload, `hServerEvent`, `hServerProcess`, `CreateThread` return handle, worker-thread ownership transfer, and synchronous wait/cleanup fallback. |
| Schema | `IPC_ASYNC_START_HANDOFF` says the async worker owns payload and wait handles only after payload allocation succeeds and `CreateThread` returns a non-null thread handle. If either gate fails, the current call owns cleanup and must use the synchronous wait path. |
| Topology | Server process start produces event/process handles; successful async handoff transfers them to `Ipc_StartServer_Thread`; failed async handoff keeps them in the current call and falls through to the existing wait/close path. |
| Logic Risk | Async startup is an optimization, not a legal excuse to lose handle ownership. Allocation or thread creation failure should not leak `hServerEvent`, leak `hServerProcess`, or skip service-start observation. |
| Official Shape | `docs/plan/srev-071-ipc-async-start-handoff.md` records Microsoft `CreateThread`, `PROCESS_INFORMATION`, and `WaitForMultipleObjects` references. `docs/plan/srev-071-ipc-async-start-handoff.schema.json` records the JSON Schema draft-07 local `IPC_ASYNC_START_HANDOFF` contract. |
| Fix | The async branch now checks `Dll_AllocTemp` before writing payload slots. If payload allocation fails, it sets `Async = FALSE`. If `CreateThread` fails, it frees the payload and sets `Async = FALSE`. The original wait/cleanup block is now entered via `if (! Async)`, so fallback waits on the service event/process and closes owned handles. |
| Acceptance Gate | `docs/plan/check-srev-071.py` validates the draft-07 schema, official references, payload allocation gate, CreateThread failure fallback, payload cleanup, synchronous wait fallback, handle cleanup, and ledger entry; `docs/plan/check-srev-071.sh` is the matrix wrapper. Windows gate: normal async service-start handoff, payload allocation failure, `CreateThread` failure, server process early-exit detection, and DcomLaunch follow-up wait. |
