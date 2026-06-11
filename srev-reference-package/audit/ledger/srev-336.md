---
kind: srev-ledger-entry
id: SREV-336
title: IPC DBWIN Trace Suppression
status: patched-comment-topology-after-official-debug-output-debugview-review-no-behavior-change
owner: Sandboxie/core/drv/ipc.c
spec: docs/plan/srev-336-ipc-dbwin-trace-suppression.md
schema: docs/plan/srev-336-ipc-dbwin-trace-suppression.schema.json
checker: docs/plan/check-srev-336.py
runtime_gate: Windows DebugView OutputDebugString and Sandboxie IPC trace matrix
---

### SREV-336: IPC DBWIN Trace Suppression

| Field | Content |
|---|---|
| Severity | [low] |
| Status | patched comment/topology after official debug-output and DebugView review; no behavior change |
| Evidence | `Ipc_InitPaths` includes `DBWinMutex`, `DBWIN_BUFFER`, `DBWIN_BUFFER_READY`, and `DBWIN_DATA_READY` in the default IPC open list. `Ipc_CheckGenericObject` applies IPC policy first, computes a trace letter only when `TRACE_ALLOW` or `TRACE_DENY` requests logging, extracts the final path component from `Name->Buffer`, and clears `letter` for the same DBWIN object names. The old comment framed this as a generic third-party workaround. |
| Data | `OutputDebugStringW`, Sysinternals DebugView, `DbgPrint`, `Ipc_InitPaths`, default IPC open list, `Ipc_CheckGenericObject`, `TRACE_ALLOW`, `TRACE_DENY`, `Name->Buffer`, `DBWinMutex`, `DBWIN_BUFFER`, `DBWIN_BUFFER_READY`, `DBWIN_DATA_READY`, `letter = 0`, `MONITOR_IPC`, `MONITOR_OPEN`, and `MONITOR_DENY`. |
| Schema | `IPC_DBWIN_TRACE_SUPPRESSION` says Windows `OutputDebugString` owns debugger output emission; Sysinternals DebugView owns tool-level capture of `OutputDebugString` and `DbgPrint`; DBWIN object names are observed local transport objects and not public Windows API schema; Sandboxie default IPC open list governs DBWIN object access policy; `Ipc_CheckGenericObject` suppresses only monitor trace noise by clearing the trace letter; the suppression block must not alter the already computed IPC access status; this SREV changes comments and proof only. |
| Topology | `application OutputDebugString / driver DbgPrint -> debugger or DebugView capture path -> DBWIN transport IPC objects observed by Sandboxie -> Sandboxie default open IPC list governs access -> Ipc_CheckGenericObject suppresses monitor trace noise only`. Trace path: `Ipc_CheckGenericObject -> policy status -> trace letter -> DBWIN final path component -> letter = 0 -> no monitor IPC event`. |
| Logic Risk | Treating the block as a generic workaround hides that access policy and trace emission are separate owners. Future work could mistake this block for DBWIN access control or let the DBWIN object names drift away from the default open-list entries. |
| Official Shape | Microsoft documents `OutputDebugStringW` as sending a string to the debugger for display. Microsoft Sysinternals documents DebugView as capturing Win32 `OutputDebugString`, kernel-mode `DbgPrint`, and kernel `DbgPrint` variants. The DBWIN object names are local observed transport names in this source tree, not public Windows API schema. |
| Fix | Comment-only source clarification. The source now names SREV-336 and states that the block suppresses DBWIN/DebugView transport objects from IPC trace noise while those objects remain governed by the default open list. No access status, trace flag, object-name comparison, default IPC list, or monitor record format changed. |
| Acceptance Gate | `docs/plan/check-srev-336.py` validates the draft-07 schema, official references, matching DBWIN object names in the default open list and trace suppression block, trace-only `letter = 0` behavior after policy status is computed, stale workaround wording removal from the trace block, SREV-146 / SREV-236 debug-output adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-336.sh` is the targeted wrapper. Runtime gate: Windows DebugView / `OutputDebugString` / Sandboxie IPC trace matrix proving that DBWIN transport chatter is suppressed from monitor logs while non-DBWIN allow/deny IPC events still emit trace records and DBWIN access policy remains unchanged. |
