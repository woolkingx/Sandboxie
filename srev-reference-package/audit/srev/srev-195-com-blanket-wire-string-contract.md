# SREV-195: COM Blanket Wire String Contract

## Scope

Entry declaration surface:

```text
Sandboxie/core/svc/comserver.h
```

Implementation owner:

```text
Sandboxie/core/svc/comserver.cpp
```

Wire owner:

```text
Sandboxie/core/svc/comwire.h
```

DLL producer/consumer:

```text
Sandboxie/core/dll/com.c
```

This entry covers the COM proxy security blanket request/reply path exposed by
`ComServer` declarations and implemented by `QueryBlanketHandler`,
`SetBlanketHandler`, `QueryBlanketSlave`, and `SetBlanketSlave`.

## Official Shape

Microsoft documents `CoSetProxyBlanket` as taking an optional `OLECHAR *`
`pServerPrincName`. `COLE_DEFAULT_PRINCIPAL` asks DCOM to pick a principal name.
When the caller supplies a real principal name, the local wire must carry a
bounded, NUL-terminated string before forwarding it to COM as `OLECHAR *`.

Microsoft documents `CoQueryProxyBlanket` as returning `pServerPrincName` as a
callee-allocated string; the caller must release it with `CoTaskMemFree`.

References:

- https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-cosetproxyblanket
- https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-coqueryproxyblanket

## Local Data

Relevant wire records:

- `COM_SET_BLANKET_REQ`
- `COM_SET_BLANKET_RPL`
- `COM_QUERY_BLANKET_REQ`
- `COM_QUERY_BLANKET_RPL`

Relevant fields:

- `DefaultServerPrincName`
- `ServerPrincName[128]`
- `COM_SLAVE_MAP::BufferLength`
- `COM_SLAVE_MAP::Buffer`

## Topology

Legal `SetBlanket` flow:

```text
DLL IClientSecurity::SetBlanket hook
-> COM_SET_BLANKET_REQ fixed wire record
-> SbieSvc SetBlanketHandler fixed length gate
-> NUL terminator gate unless DefaultServerPrincName is set
-> COM_SLAVE_MAP
-> slave SetBlanketSlave repeats terminator gate
-> CoSetProxyBlanket
```

Legal `QueryBlanket` flow:

```text
DLL IClientSecurity::QueryBlanket hook
-> COM_QUERY_BLANKET_REQ
-> SbieSvc QueryBlanketHandler
-> slave QueryBlanketSlave
-> CoQueryProxyBlanket
-> bounded copy into COM_QUERY_BLANKET_RPL::ServerPrincName
-> CoTaskMemFree
-> COM_SLAVE_MAP::BufferLength = sizeof(COM_QUERY_BLANKET_RPL)
-> parent validates BufferLength before copying reply fields
```

## Risk

Before this fix, `SetBlanketHandler` accepted a fixed
`COM_SET_BLANKET_REQ::ServerPrincName[128]` array without proving that it
contained a terminator. `SetBlanketSlave` then passed it directly to
`CoSetProxyBlanket` as an `OLECHAR *`. A malformed pipe caller could make COM
scan past the fixed wire field.

`QueryBlanketSlave` wrote a fixed `COM_QUERY_BLANKET_RPL` into the shared map
but did not set `pMap->BufferLength` to the produced fixed reply size.
`QueryBlanketHandler` then copied reply fields without checking the slave's
reply shape. The current in-process slave normally writes the expected fields,
but the map crossing still lacked an explicit shape proof.

## Fix

- Add `ComServer_HasWcharTerminator`.
- In `SetBlanketHandler`, reject non-default principal names that do not
  terminate inside `ServerPrincName[128]`.
- In `SetBlanketSlave`, repeat the same gate before calling `CoSetProxyBlanket`.
- In `QueryBlanketSlave`, set `pMap->BufferLength` to
  `sizeof(COM_QUERY_BLANKET_RPL)` after building the reply.
- In `QueryBlanketHandler`, require that exact `BufferLength` before copying
  reply fields.

## Acceptance Gate

Source-level gate:

```bash
python3 docs/plan/check-srev-195.py
bash docs/plan/check-srev-195.sh
python3 docs/plan/check-core-coverage.py
```

Runtime gate:

```text
Windows SbieSvc/DLL build plus COM QueryBlanket/SetBlanket smoke for default
principal, explicit terminated principal, unterminated principal rejection, and
QueryBlanket reply copy shape.
```
