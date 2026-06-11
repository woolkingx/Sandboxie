# SREV-127 Named Pipe LPC Name Wire String

## Data

Owner file:

```text
Sandboxie/core/svc/namedpipeserver.cpp
```

Reviewed nodes:

```text
LpcConnectHandler
NAMED_PIPE_LPC_CONNECT_REQ
req->name[64]
_wcsicmp
wcscpy
wcscat
port_name[96]
NtConnectPort
NtAlpcConnectPort
OpenHandler
NAMED_PIPE_OPEN_REQ
```

## Schema

`NAMEDPIPE_LPC_NAME_WIRE_STRING` defines these local contracts:

- `NAMED_PIPE_LPC_CONNECT_REQ::name` is a fixed-size wire field, not a trusted
  C wide string until the server terminates it.
- `LpcConnectHandler` validates the full fixed request header before writing the
  local terminator into `req->name`.
- `LpcConnectHandler` writes `L'\0'` to the last element of `req->name` before
  `_wcsicmp`, `wcscpy`, or `wcscat` consumes it.
- The existing allow-list remains limited to `ntsvcs` and `plugplay`.
- The existing `\RPC Control\` object path composition, old LPC vs ALPC branch,
  info buffer validation, and proxy-handle ownership are unchanged.
- `OpenHandler` remains the nearby precedent for terminating fixed wire string
  fields before string operations.

## Topology

```text
sandboxed caller
  -> NAMED_PIPE_LPC_CONNECT_REQ fixed wire buffer
  -> LpcConnectHandler length gate
  -> req->name[last] = L'\0'
  -> _wcsicmp allow-list check
  -> "\\RPC Control\\" + req->name
  -> NtConnectPort or NtAlpcConnectPort
```

The fixed wire field crosses from counted message memory into CRT
null-terminated string operations only after the local terminator gate.

## Logic Risk

`NAMED_PIPE_LPC_CONNECT_REQ::name` has a fixed array shape. A malicious or
malformed caller can fill all 64 WCHAR slots without a terminator while still
passing `req->h.length >= sizeof(NAMED_PIPE_LPC_CONNECT_REQ)`. The old
`LpcConnectHandler` then passed `req->name` directly to `_wcsicmp` and, for
allowed names, `wcscat`. Those functions operate on null-terminated strings, so
the server could read past the wire field while deciding whether the broker may
connect to `\RPC Control\ntsvcs` or `\RPC Control\plugplay`.

The correct local repair is the same schema gate already used by `OpenHandler`:
after the fixed request has been proven present, force the last element of the
wire string field to NUL before any CRT string operation. This does not expand
the allow-list or change LPC/ALPC connection behavior.

## Official Shape

- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/stricmp-wcsicmp-mbsicmp-stricmp-l-wcsicmp-l-mbsicmp-l?view=msvc-170
- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-wcscpy-mbscpy?view=msvc-170

## Fix

`LpcConnectHandler` now writes:

```c
req->name[ARRAYSIZE(req->name) - 1] = L'\0';
```

immediately after the request-size validation succeeds and before `_wcsicmp`
tests the allow-list. No allow-list entries, `port_name` prefix, `wcscpy` /
`wcscat` composition, old LPC path, ALPC path, info buffer validation, returned
handle ownership, or cleanup path changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-127.py
bash docs/plan/check-srev-127.sh
```

Runtime/build gate still required:

- Windows service build for `namedpipeserver.cpp`.
- LPC connect positive smoke for `ntsvcs` and `plugplay`.
- Negative request with all 64 `name` WCHAR slots nonzero proving no read past
  the wire field and normal deny behavior.
- ALPC branch smoke for supported systems.
- Regression smoke proving `OpenHandler` named-pipe open behavior is unchanged.
