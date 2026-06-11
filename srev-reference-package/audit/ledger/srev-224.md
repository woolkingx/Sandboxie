---
kind: srev-ledger-entry
id: SREV-224
title: Terminal GetName Reply Terminator
status: patched-source-level-after-local-terminal-wire-reply-contract-review-needs-windows-terminal-runtime-proof
owner: Sandboxie/core/svc/terminalserver.cpp
spec: docs/plan/srev-224-terminal-get-name-reply-terminator.md
schema: docs/plan/srev-224-terminal-get-name-reply-terminator.schema.json
checker: docs/plan/check-srev-224.py
runtime_gate: "Windows service/DLL build plus normal, long-name or fault-injected, and short-name Terminal GetName smokes"
---
### SREV-224: Terminal GetName Reply Terminator

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after local Terminal wire reply contract review; needs Windows Terminal Services runtime proof |
| Evidence | `Sandboxie/core/svc/terminalserver.h` was the top unnamed reviewable core file after SREV-223. It declares `TerminalServer::GetName`, whose implementation in `Sandboxie/core/svc/terminalserver.cpp` builds `TERMINAL_GET_NAME_RPL.name[128]` for the DLL hook in `Sandboxie/core/dll/terminal.c`. Before this SREV, `GetName` copied `wmemcpy(rpl->name, name, 120)` and then wrote `name[120] = L'\0'`. That terminator write affected the service stack scratch buffer after the reply copy, not `rpl->name`. The DLL-side consumer calls `wcscpy(Name, rpl->name)`, so the reply field itself must carry a contained NUL. |
| Data | `terminalserver.h`, `terminalserver.cpp`, `terminalwire.h`, `terminal.c`, `TerminalServer::GetName`, `TERMINAL_GET_NAME_REQ`, `TERMINAL_GET_NAME_RPL`, `TERMINAL_GET_NAME_RPL.name`, `WinStationNameFromLogonIdW`, `Terminal_WinStationNameFromLogonIdW`, and `wcscpy(Name, rpl->name)`. |
| Schema | `TERMINAL_GET_NAME_REPLY_TERMINATOR` says `terminalserver.h` declares the broker entry points while `terminalserver.cpp` owns service-side request handling; `terminalwire.h` owns `TERMINAL_GET_NAME_RPL.name` as a fixed 128-`WCHAR` reply string; the service reply must be NUL-terminated inside `rpl->name` before crossing back to `core/dll/terminal.c`; the DLL-side `Terminal_WinStationNameFromLogonIdW` consumes `rpl->name` with `wcscpy`, so the reply buffer owns the termination gate; and the service must not copy uninitialized stack tail bytes into the reply. |
| Topology | The DLL hook sends `TERMINAL_GET_NAME_REQ` to `TerminalServer::GetName`. The service calls private `WinStationNameFromLogonIdW` into a fixed stack buffer, then serializes a fixed `TERMINAL_GET_NAME_RPL.name[128]` reply. The DLL receives the reply and copies `rpl->name` into the caller-provided `Name` buffer with `wcscpy`. |
| Logic Risk | A terminator written to the wrong buffer does not protect the wire reply. If the private WinStation API returns a long or nonterminated name, or if a shorter name leaves stack tail bytes after its NUL, the reply can become unterminated or leak stack tail into the client-side copy path. The stable owner is the local reply schema because `WinStationNameFromLogonIdW` is a private export without a public buffer-size contract in Microsoft documentation. |
| Official Shape | `docs/plan/srev-224-terminal-get-name-reply-terminator.md` records public Microsoft WTS session-information references for the supported API family and explicitly records that this private WinStation export remains a runtime-proof item. `docs/plan/srev-224-terminal-get-name-reply-terminator.schema.json` records the JSON Schema draft-07 local `TERMINAL_GET_NAME_REPLY_TERMINATOR` contract. |
| Fix | `TerminalServer::GetName` now zeroes the stack `name[128]` buffer before the private WinStation call, zeroes `rpl->name`, copies at most 127 `WCHAR`s into the reply, and writes `rpl->name[127] = L'\0'`. No request id, request size validation, session selection, private WinStation dispatch, error propagation, or DLL-side caller-buffer policy changed. |
| Acceptance Gate | `docs/plan/check-srev-224.py` validates the draft-07 schema, public WTS references, declaration/wire surfaces, service-side zero/copy/terminator source shape, removal of the stale stack-buffer terminator pattern, DLL-side `wcscpy` consumer topology, and ledger entry; `docs/plan/check-srev-224.sh` is the targeted wrapper. Runtime/build gate: Windows service/DLL build for `terminalserver.cpp`, `terminalwire.h`, and `terminal.c`; normal `WinStationNameFromLogonIdW` smoke; long-name or fault-injected reply proving `rpl->name[127]` is NUL before DLL copy; and short-name smoke proving no uninitialized stack tail bytes are copied into the reply. |
