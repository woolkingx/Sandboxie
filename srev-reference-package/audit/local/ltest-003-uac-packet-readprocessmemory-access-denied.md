# LTEST-003: UAC Packet ReadProcessMemory Access Denied

## Stage Gate

| Field | Content |
|---|---|
| Stage | perceive -> boundary -> topology -> verify |
| Input artifact | Runtime `SBIE2218 [84 / 00000005]`, `SBIE2219 Start.exe [DefaultBox]`, COMRuntime 18221 events, and `Sandboxie/core/svc/serviceserver2.cpp` |
| Output artifact | Local-only runtime capture plan for the UAC packet readback failure |
| Owner | `Sandboxie/core/svc/serviceserver2.cpp` owns the service-side `SECURE_UAC_PACKET` readback; `Sandboxie/core/dll/secure.c` owns packet construction in the sandboxed caller |
| Acceptance gate | Capture proves which process owns the packet address, which UAC proxy process reads it, which token/handle rights are present, and why `ReadProcessMemory` returns `ERROR_ACCESS_DENIED` before any source behavior change |

## Runtime Evidence

Observed Sandboxie messages:

```text
SbieSvc.exe: SBIE2218 Failed to get elevated privileges: [84 / 00000005]
SbieSvc.exe: SBIE2219 Request was issued by program Start.exe [DefaultBox]
```

VM process readback showed:

```text
Start.exe /env:00000000_SBIE_CURRENT_DIRECTORY="C:\Users\vboxuser\Downloads" /env:=Refresh /elevate "C:\Users\vboxuser\Downloads\npp.8.5.6.Installer.x64.exe"
```

Windows Application log showed repeated COMRuntime 18221 warnings at the same
time, with `C:\temp\Sandboxie-Plus\Start.exe` denied while attempting to connect
to the `RPCSS` service for a COM server.

Current VM config evidence:

```ini
[GlobalSettings]
Test=true
LogMessageEvents=y

[DefaultBox]
Enabled=y
Template=SkipHook
ConfigLevel=10
```

This is not the LTEST-002 SandMan supporter-warning gate. It is a service/core
UAC elevation bridge failure.

## Source Coordinates

`ServiceServer::RunUacSlave3` uses the UAC proxy side to read a
`SECURE_UAC_PACKET` from the caller process:

```text
errlvl = 0x84
ReadProcessMemory(hProcess, pkt_addr, pkt, pkt_len, &copy_len)
```

`ReportError2218` logs the pair:

```text
SBIE2218 [errlvl / GetLastError]
SBIE2219 imagename [boxname]
```

`Sandboxie/core/dll/secure.c` builds the packet in `Secure_HandleElevation` and
sends `pkt_addr` plus `pkt_len` through `MSGID_SERVICE_UAC`.

## Hypothesis To Test

H: `Start.exe /elevate` reaches the Sandboxie UAC bridge, but the UAC proxy
process cannot legally read the caller-owned `SECURE_UAC_PACKET` memory.

Condition C: Run the Notepad++ installer through `Start.exe /elevate` in
`DefaultBox` with `[GlobalSettings] Test=true`.

Predicted E: The UAC proxy reaches `RunUacSlave3`, `OpenProcess` succeeds or
returns a handle, then `ReadProcessMemory` fails at `errlvl=0x84` with
`ERROR_ACCESS_DENIED`, while COMRuntime 18221 records RPCSS COM access denial for
`Start.exe`.

## Capture Plan

1. Capture `idProcess`, `pkt_addr`, `pkt_len`, current process image, current
   process box name, and whether `RunUacSlave3` chose `SbieApi_OpenProcess` or
   plain `OpenProcess`.
2. Capture the granted process access mask for `hProcess` before
   `ReadProcessMemory`.
3. Capture caller token integrity/elevation/appcontainer flags for `Start.exe`
   and the UAC proxy process.
4. Capture the first failing page state around `pkt_addr` with
   `VirtualQueryEx` before `ReadProcessMemory`.
5. Only after the capture, decide whether the correct route is a handle-rights
   fix, a packet transport redesign, a config fallback such as `NoUACProxy`, or
   a documented limitation for elevated installers.

## Non-Goals

- Do not bypass this by mutating certificate state.
- Do not fold this into SREV/KPATH until a clean upstream-shareable source fix
  exists.
- Do not change UAC behavior before official AppInfo/RPC and process-memory API
  shapes are rechecked.
- Do not treat `Test=true` as a Windows UAC or COM permission bypass.

## Acceptance Gate

`docs/plan/local/check-ltest-003.py` validates this local-only capture record,
the source coordinates, the observed runtime messages, and the explicit
No-source-change boundary.
