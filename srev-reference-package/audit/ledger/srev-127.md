---
kind: srev-ledger-entry
id: SREV-127
title: Named Pipe LPC Name Wire String
status: patched-source-level-after-official-crt-wide-string-comparison-copy-shape-needs-
owner: Sandboxie/core/svc/namedpipeserver.cpp
spec: docs/plan/srev-127-namedpipe-lpc-name-wire-string.md
schema: docs/plan/srev-127-namedpipe-lpc-name-wire-string.schema.json
checker: docs/plan/check-srev-127.py
runtime_gate: "Windows service build for `namedpipeserver.cpp`, LPC connect positive smoke for `ntsvcs` and `plugplay`, negative request with all 64 `name` WCHAR slots nonzero proving bounded read and deny behavior, ALPC branch smoke where supported, and regression smoke proving named-pipe `OpenHandler` behavior is unchanged"
---
### SREV-127: Named Pipe LPC Name Wire String

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official CRT wide-string comparison/copy shape; needs Windows service LPC/ALPC runtime proof |
| Evidence | `Sandboxie/core/svc/namedpipeserver.cpp` was the highest-ranked unnamed reviewable core file after SREV-126. `OpenHandler` already terminates `NAMED_PIPE_OPEN_REQ::name` and `server` after validating the full fixed request. `LpcConnectHandler` accepted `NAMED_PIPE_LPC_CONNECT_REQ`, then used `req->name` in `_wcsicmp` allow-list checks and `wcscat(port_name, req->name)` without first forcing the fixed wire array to be null-terminated. Microsoft documents `_wcsicmp` inputs as null-terminated strings and `wcscpy` inputs as null-terminated source strings copied including the terminator. |
| Data | `LpcConnectHandler`, `NAMED_PIPE_LPC_CONNECT_REQ`, `req->name[64]`, `_wcsicmp`, `wcscpy`, `wcscat`, `port_name[96]`, `\\RPC Control\\`, `ntsvcs`, `plugplay`, `NtConnectPort`, `NtAlpcConnectPort`, `info_len`, `info_data`, `OpenHandler`, `NAMED_PIPE_OPEN_REQ`, `req->server`, and `ARRAYSIZE`. |
| Schema | `NAMEDPIPE_LPC_NAME_WIRE_STRING` says `NAMED_PIPE_LPC_CONNECT_REQ::name` is a fixed-size wire field, not a trusted C wide string until the server terminates it; `LpcConnectHandler` validates the full fixed request header before writing the local terminator into `req->name`; `LpcConnectHandler` writes NUL to the last element of `req->name` before `_wcsicmp`, `wcscpy`, or `wcscat` consumes it; the allow-list remains limited to `ntsvcs` and `plugplay`; `\\RPC Control\\` object path composition, old LPC vs ALPC branch, info buffer validation, and proxy-handle ownership are unchanged; `OpenHandler` remains the nearby precedent for terminating fixed wire string fields before string operations. |
| Topology | A sandboxed caller sends `NAMED_PIPE_LPC_CONNECT_REQ` through PipeServer. The service validates `req->h.length >= sizeof(NAMED_PIPE_LPC_CONNECT_REQ)`, terminates `req->name[ARRAYSIZE(req->name)-1]`, applies the `_wcsicmp` allow-list, composes `\\RPC Control\\<name>` into `port_name`, validates `info_len` / `info_data`, then connects through `NtConnectPort` for old LPC or `NtAlpcConnectPort` for ALPC and stores the resulting port in `m_ProxyHandle`. |
| Logic Risk | Fixed wire arrays and CRT wide-string operations have different schemas. A caller can fill all 64 WCHAR slots in `req->name` without a terminator while still satisfying the fixed request length. The old code then let `_wcsicmp` and `wcscat` read past the wire field while deciding whether to broker access to privileged RPC Control LPC endpoints. The correct repair is the same local terminator gate already present in `OpenHandler`, not an allow-list expansion, port-name redesign, or LPC/ALPC behavior change. |
| Official Shape | `docs/plan/srev-127-namedpipe-lpc-name-wire-string.md` records Microsoft `_wcsicmp` and `wcscpy` / wide-string copy references. `docs/plan/srev-127-namedpipe-lpc-name-wire-string.schema.json` records the JSON Schema draft-07 local `NAMEDPIPE_LPC_NAME_WIRE_STRING` contract. |
| Fix | `LpcConnectHandler` now writes `req->name[ARRAYSIZE(req->name) - 1] = L'\0';` immediately after the fixed request-size gate succeeds and before any `_wcsicmp` allow-list checks. No allow-list entries, `\\RPC Control\\` prefix, `wcscpy` / `wcscat` composition, old LPC path, ALPC path, info buffer validation, returned handle ownership, or cleanup path changed. |
| Acceptance Gate | `docs/plan/check-srev-127.py` validates the draft-07 schema, official references, wire schema, `OpenHandler` precedent, `LpcConnectHandler` terminator placement before `_wcsicmp`, preservation of allow-list/path/LPC/ALPC/proxy-handle topology, stale unterminated old shape removal, and ledger entry; `docs/plan/check-srev-127.sh` is the matrix wrapper. Runtime/build gate: Windows service build for `namedpipeserver.cpp`, LPC connect positive smoke for `ntsvcs` and `plugplay`, negative request with all 64 `name` WCHAR slots nonzero proving bounded read and deny behavior, ALPC branch smoke where supported, and regression smoke proving named-pipe `OpenHandler` behavior is unchanged. |
