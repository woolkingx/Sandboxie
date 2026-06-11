# SREV-224 Terminal GetName Reply Terminator

## Data

Owner files:

```text
Sandboxie/core/svc/terminalserver.h
Sandboxie/core/svc/terminalserver.cpp
Sandboxie/core/svc/terminalwire.h
Sandboxie/core/dll/terminal.c
```

Reviewed nodes:

```text
TerminalServer::GetName
TERMINAL_GET_NAME_REQ
TERMINAL_GET_NAME_RPL
Terminal_WinStationNameFromLogonIdW
WinStationNameFromLogonIdW
wcscpy(Name, rpl->name)
```

## Schema

`TERMINAL_GET_NAME_REPLY_TERMINATOR` defines these local contracts:

- `terminalserver.h` declares the TerminalServer broker entry points;
  `terminalserver.cpp` owns service-side request handling.
- `terminalwire.h` owns `TERMINAL_GET_NAME_RPL.name` as a fixed
  128-`WCHAR` reply string.
- The service reply must be NUL-terminated inside `rpl->name` before it crosses
  the broker boundary back to `core/dll/terminal.c`.
- The DLL-side `Terminal_WinStationNameFromLogonIdW` consumes `rpl->name` with
  `wcscpy`, so the reply buffer, not the service stack scratch buffer, owns the
  termination gate.
- The service does not copy uninitialized stack tail bytes into the reply.
- This SREV does not change request ids, session selection, private
  `WinStationNameFromLogonIdW` dispatch, error propagation, or DLL-side caller
  buffer policy.

## Topology

```text
terminal.c hook
  -> TERMINAL_GET_NAME_REQ
  -> TerminalServer::GetName
  -> private WinStationNameFromLogonIdW(name[128])
  -> TERMINAL_GET_NAME_RPL.name[128]
  -> terminal.c wcscpy(Name, rpl->name)
```

`WinStationNameFromLogonIdW` is a private `winsta.dll` export, so there is no
public Microsoft buffer-size contract for the local typedef in this source tree.
The stable schema owner for this fix is the Sandboxie wire reply itself:
`TERMINAL_GET_NAME_RPL.name` must be a contained C string before the DLL hook
copies it.

## Logic Risk

Before this SREV, `TerminalServer::GetName` copied 120 `WCHAR`s from the stack
buffer into `rpl->name`, then wrote `name[120] = L'\0'`. That terminator write
affected the stack scratch buffer after the copy, not the reply buffer. If the
private API returned a long or nonterminated name, or if the copied span carried
uninitialized stack data after a shorter name, the DLL-side `wcscpy(Name,
rpl->name)` could read beyond `TERMINAL_GET_NAME_RPL.name`.

The minimal legal fix is to zero both fixed buffers, copy at most 127 characters
into the reply, and write the terminator inside `rpl->name`.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/nf-wtsapi32-wtsquerysessioninformationw
- https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/ne-wtsapi32-wts_info_class

These public WTS references document the supported session-information family.
The `WinStationNameFromLogonIdW` export used here is private; therefore the
source-level gate is local wire-schema containment plus a Windows runtime proof.

## Fix

`TerminalServer::GetName` now zeroes the stack `name[128]` buffer before the
private WinStation call, zeroes `rpl->name`, copies at most 127 characters into
the reply, and writes `rpl->name[127] = L'\0'`.

No request id, request size validation, session id, `WinStationNameFromLogonIdW`
call, error status, or DLL-side `wcscpy` behavior changed.

## Acceptance Gate

Source gate:

```bash
bash docs/plan/check-srev-224.sh
python3 docs/plan/check-core-coverage.py
git diff --check
```

Full historical matrix is deferred to the next batch checkpoint or shared
checker/ledger infrastructure change.

Runtime/build gate still required:

- Windows service/DLL build for `terminalserver.cpp`, `terminalwire.h`, and
  `terminal.c`.
- Normal `WinStationNameFromLogonIdW` smoke proving the name still round-trips.
- Long-name or fault-injected private WinStation reply proving
  `TERMINAL_GET_NAME_RPL.name[127]` is NUL before the DLL `wcscpy`.
- Short-name smoke proving no uninitialized stack tail bytes are copied into
  the reply after the NUL.
