# SREV-120 Terminal User Token Session Contract

## Data

Owner files:

```text
Sandboxie/core/dll/terminal.c
Sandboxie/core/svc/terminalwire.h
Sandboxie/core/svc/terminalserver.cpp
```

Reviewed nodes:

```text
Terminal_WTSQueryUserToken
GET_USER_TOKEN_REQ
TerminalServer::GetUserToken
WTSQueryUserToken
SessionId
SbieApi_QueryProcess
PipeServer::GetCallerProcessId
DuplicateHandle
API_FILTER_TOKEN
OriginalToken
UnfilteredToken
```

## Schema

`TERMINAL_USER_TOKEN_SESSION_CONTRACT` defines these local contracts:

- `WTSQueryUserToken` is keyed by an explicit Remote Desktop Services
  `SessionId`.
- The sandboxed DLL hook must forward the caller's requested `SessionId` across
  the TerminalServer wire boundary.
- TerminalServer must validate `GET_USER_TOKEN_REQ` by the full request struct
  size, not by bare `MSG_HEADER` size.
- TerminalServer may only satisfy a sandboxed `WTSQueryUserToken` request when
  the requested session equals the caller process session returned by
  `SbieApi_QueryProcess`.
- The service calls `WTSQueryUserToken` with the validated requested session id.
- Token filtering, `OriginalToken` / `UnfilteredToken` policy, handle
  duplication, and close-handle ownership are unchanged.

## Topology

```text
sandboxed process
  -> Terminal_WTSQueryUserToken(SessionId, pToken)
      -> GET_USER_TOKEN_REQ { MSG_HEADER, session_id }
      -> TerminalServer::GetUserToken
          -> PipeServer caller pid
          -> SbieApi_QueryProcess(caller pid) -> caller session
          -> requested session == caller session gate
          -> WTSQueryUserToken(requested session)
          -> optional API_FILTER_TOKEN
          -> DuplicateHandle into caller process
          -> GET_USER_TOKEN_RPL.hToken
```

## Logic Risk

The old hook accepted a `SessionId` parameter but did not place it in the wire
request. The service therefore always derived the session from the caller
process and passed that value to `WTSQueryUserToken`. That hid the official API
shape: a request for a specific session could silently return a token for a
different session.

Passing the requested session directly without a caller-session gate would also
be wrong, because the service runs as the trusted token broker. The legal local
repair is to carry the requested `SessionId` over the wire, then allow it only
when it matches the sandboxed caller's known session.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/nf-wtsapi32-wtsqueryusertoken
- https://learn.microsoft.com/en-us/windows/win32/api/wtsapi32/nf-wtsapi32-wtsenumeratesessionsw
- https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle

## Fix

`GET_USER_TOKEN_REQ` now carries `ULONG session_id`. `Terminal_WTSQueryUserToken`
sets that field from its `SessionId` argument. `TerminalServer::GetUserToken`
now validates `sizeof(GET_USER_TOKEN_REQ)`, resolves the caller session with
`SbieApi_QueryProcess`, rejects mismatched requested sessions with
`ERROR_ACCESS_DENIED`, and calls `WTSQueryUserToken(req->session_id, &hToken)`
only after that gate.

No token filtering policy, `OriginalToken` / `UnfilteredToken` configuration,
`API_FILTER_TOKEN` routing, `DuplicateHandle` target process, token close path,
or reply handle shape changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-120.py
bash docs/plan/check-srev-120.sh
```

Runtime/build gate still required:

- Windows build for `terminal.c`, `terminalwire.h`, and `terminalserver.cpp`.
- Sandboxed `WTSQueryUserToken(Dll_SessionId, ...)` smoke proving the returned
  duplicated token handle is usable and closed by the caller.
- Negative smoke where a sandboxed caller requests a different session and
  receives `ERROR_ACCESS_DENIED`.
- `OriginalToken`, `UnfilteredToken`, and filtered-token policy matrix.
- 32-bit and 64-bit caller/service handle-duplication matrix.
