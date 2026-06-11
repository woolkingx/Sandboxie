# KPATH-005 ALPC Capture Workflow

Goal: prove whether a Sandboxie service-call hang is an OS ALPC/LPC wait, a
stuck SbieSvc handler, or a different blocked resource before changing
Sandboxie timeout behavior.

## Official Baseline

Microsoft documents ALPC as an ETW kernel event surface. The relevant event
types are:

| Event | Meaning |
|---|---|
| `ALPC_Send_Message` | A local procedure call message was sent. |
| `ALPC_Receive_Message` | A local procedure call message was received. |
| `ALPC_Wait_For_Reply` | A caller is waiting for a reply. |
| `ALPC_Wait_For_New_Message` | A server-side thread is waiting for a new message. |
| `ALPC_Unwait` | A wait was canceled or ended. |

Microsoft's debugger documentation also says LPC is now emulated in ALPC, so
modern debugging should use `!alpc` instead of treating old LPC as the true
owner.

References:

- `https://learn.microsoft.com/en-us/windows/win32/etw/alpc`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-lpc`
- `https://learn.microsoft.com/en-us/windows-hardware/test/wpt/windows-performance-recorder`
- `https://learn.microsoft.com/en-us/windows-hardware/test/wpt/stack-wpa`

## Coordinate

| Field | Value |
|---|---|
| Thing | `SbieDll_CallServer` request/reply over Sandboxie service LPC port |
| OS owner | ALPC/LPC kernel subsystem |
| Sandboxie owner | `callsvc.c` owns client request chunks; `PipeServer.cpp` owns service dispatch |
| Boundary | sandboxed process -> kernel port wait -> SbieSvc handler -> reply |
| Correct first proof | ALPC wait event or debugger state |
| Sandboxie-only proof | insufficient by itself; it only maps OS waits to `msgid` / handler |

## Capture Plan

1. Enable Windows Performance Recorder or xperf with kernel ALPC events.
2. Enable stack capture for these ALPC stack points when available:
   `AlpcSendMessage`, `AlpcReceiveMessage`, `AlpcWaitForReply`,
   `AlpcWaitForNewMessage`, and `AlpcUnwait`.
3. Start capture immediately before the Sandboxie hang repro.
4. Reproduce the stuck state without killing SbieSvc.
5. Stop capture and open the ETL in Windows Performance Analyzer.
6. Filter by the sandboxed process, `SbieSvc.exe`, and ALPC wait events.
7. Record:
   - client process id and thread id
   - service process id and thread id
   - ALPC port/object if visible
   - wait type: wait-for-reply or wait-for-new-message
   - call stack at wait
   - whether there is a matching receive/send/unwait transition

## Debugger Plan

If the machine is still responsive enough for debugging:

1. Attach kernel debugger or local live kernel debugging environment.
2. Use `!alpc` to inspect the relevant ALPC ports, messages, and waiting
   threads.
3. Capture stacks for:
   - thread blocked in `NtRequestWaitReplyPort` / ALPC wait-for-reply
   - SbieSvc thread handling or waiting on the matching port
4. Match thread ids and process ids against the ETW capture when possible.

## Decision Gate

| Observation | Interpretation | Next Action |
|---|---|---|
| client waits for reply, SbieSvc handler thread is running/stuck | Sandboxie handler or downstream dependency is likely root cause | add Sandboxie `msgid` / handler correlation, then fix that handler |
| client waits for reply, SbieSvc has no matching receive | port/message routing or disconnected client state | inspect `PipeServer::PortRequest` / client map |
| SbieSvc waits for new message, client is not waiting on Sandboxie port | hang source is probably outside KPATH-005 | return to KPATH-003/KPATH-002/KPATH-004 evidence |
| ALPC wait ends normally but UI remains stuck | ALPC is not the root wait | inspect caller stack after reply |

## Sandboxie Instrumentation Gate

Only after the OS wait state is proven, add temporary or trace-gated records:

- client side: `SbieDll_CallServer` begin/end with `msgid`, length, sequence,
  status, elapsed time, process id, thread id
- service side: `PipeServer::CallTarget` begin/end with `msgid`, target server
  id, caller process id, caller thread id, status, elapsed time

Do not add a universal timeout before this mapping exists. A blind timeout can
turn a valid long broker operation into a compatibility regression while hiding
the actual stuck dependency.
