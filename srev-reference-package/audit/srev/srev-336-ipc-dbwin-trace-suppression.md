# SREV-336: IPC DBWIN Trace Suppression

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/ipc.c`, Microsoft `OutputDebugStringW` documentation, Microsoft Sysinternals DebugView documentation, SREV-146, SREV-236 |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `Ipc_CheckGenericObject` DBWIN/DebugView trace-noise suppression |
| Acceptance gate | Targeted checker validates official references, default DBWIN open-list adjacency, trace-only suppression logic, stale workaround wording removal, and ledger fragment |

## Data

`Ipc_InitPaths` includes the DebugView/DBWIN objects in the default IPC open
list:

- `DBWinMutex`;
- `DBWIN_BUFFER`;
- `DBWIN_BUFFER_READY`;
- `DBWIN_DATA_READY`.

`Ipc_CheckGenericObject` then applies normal IPC policy first and computes a
trace letter only when `TRACE_ALLOW` or `TRACE_DENY` asks for logging. The
DBWIN block only clears that trace letter for the same object names after
extracting the final path component from `Name->Buffer`. It does not alter the
object access status.

## Official Shape

Microsoft documents `OutputDebugStringW` as sending a string to the debugger
for display. If no application debugger is attached and the system debugger is
active, the system debugger may display the string through `DbgPrint`; if no
debugger path is active, the call does nothing.

Microsoft's Sysinternals DebugView documentation describes DebugView as a tool
that captures Win32 `OutputDebugString`, kernel-mode `DbgPrint`, and kernel
`DbgPrint` variants.

The DBWIN object names are not documented here as a Windows API contract. In
this SREV they are treated as observed DebugView/DBWIN transport objects already
named by Sandboxie's default IPC open list and trace suppression block.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-outputdebugstringw`
- `https://learn.microsoft.com/en-us/sysinternals/downloads/debugview`

## Boundary

```text
application OutputDebugString / driver DbgPrint
  -> debugger or DebugView capture path
  -> DBWIN transport IPC objects observed by Sandboxie
  -> Sandboxie default open IPC list governs access
  -> Ipc_CheckGenericObject suppresses monitor trace noise only
```

The public API owner is the Windows debugging API. DebugView owns its capture
tool behavior. Sandboxie's driver owns IPC policy and, separately, the monitor
trace emission decision. This SREV keeps those owners separate: DBWIN access
remains a policy/open-list matter; the local block only prevents high-volume
debug transport chatter from hiding useful IPC policy events.

## Topology

```text
Ipc_CheckGenericObject
  -> compute status from open/closed/read/normal path policy
  -> if ipc_trace requests allow/deny records, compute letter
  -> if final component is a DBWIN object, clear letter
  -> if letter remains, emit monitor IPC event
```

## Logic Risk

The stale workaround wording made a trace-noise decision look like a policy
workaround. Future work could mistake this block for DBWIN access control and
move the object list out of sync with the default open-list entries. The correct
shape is narrower: policy is decided before the trace block, and this block
only suppresses monitor records for the same observed DBWIN transport objects.

## Fix

Comment-only source clarification. The source now names SREV-336 and states
that the block suppresses DBWIN/DebugView transport objects from IPC trace
noise, while those objects remain governed by the default open list. No access
status, trace flag, object-name comparison, default IPC list, or monitor record
format changed.

## Acceptance Gate

`docs/plan/check-srev-336.py` validates the draft-07 schema, official
references, matching DBWIN object names in the default open list and trace
suppression block, trace-only `letter = 0` behavior after policy status is
computed, stale workaround wording removal from the trace block, SREV-146 /
SREV-236 debug-output adjacency, combined ledger entry, and split ledger
fragment.

Runtime gate: Windows DebugView / `OutputDebugString` / Sandboxie IPC trace
matrix proving that DBWIN transport chatter is suppressed from monitor logs
while non-DBWIN allow/deny IPC events still emit trace records and DBWIN access
policy remains unchanged.
