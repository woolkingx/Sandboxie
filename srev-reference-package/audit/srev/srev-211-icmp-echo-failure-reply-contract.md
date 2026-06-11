# SREV-211: ICMP Echo Failure Reply Contract

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/svc/iphlpserver.h` was the top unnamed reviewable core file
after SREV-210. It declares `IpHlpServer`, the SbieSvc broker that proxies
ICMP handles and echo requests for sandboxed processes.

The implementation in `Sandboxie/core/svc/iphlpserver.cpp` loads
`iphlpapi.dll`, stores `IcmpCreateFile`, `Icmp6CreateFile`,
`IcmpCloseHandle`, `IcmpSendEcho2`, `IcmpSendEcho2Ex`, and `Icmp6SendEcho2`,
then handles `MSGID_IPHLP_SEND_ECHO` by calling the selected API and copying
the reply buffer back through `IPHLP_SEND_ECHO_RPL`.

Before this fix, the constructor initialized only the create/close pointers,
leaving the echo function pointer members uninitialized until `LoadLibrary`
succeeded. The send path also converted a zero API return into
`num_replies = 1` even though the status was set from `GetLastError`. The IPv4
reply post-processing then treated the zeroed reply buffer as an array of
`ICMP_ECHO_REPLY` records and rewrote the `Data` pointer offset despite the API
failure.

## Data

`iphlpserver.h`, `iphlpserver.cpp`, `iphlpwire.h`, `IpHlpServer`,
`MSGID_IPHLP_SEND_ECHO`, `IPHLP_SEND_ECHO_REQ`, `IPHLP_SEND_ECHO_RPL`,
`IcmpSendEcho2`, `IcmpSendEcho2Ex`, `Icmp6SendEcho2`, `num_replies`,
`reply_size`, `reply_data`, `GetLastError`, and IPv4 reply pointer adjustment.

## Official Shape

Microsoft documents `IcmpSendEcho2`, `IcmpSendEcho2Ex`, and `Icmp6SendEcho2`
as returning the number of ICMP echo replies stored in `ReplyBuffer` for a
synchronous call. If the function fails, it returns zero and the caller obtains
extended error information from `GetLastError`.

Microsoft documents the IPv4 reply buffer as containing one or more
`ICMP_ECHO_REPLY` structures followed by options and data. Therefore reply-data
pointer normalization is meaningful only for successful IPv4 replies that the
API actually reported.

References:

- `https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmpsendecho2`
- `https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmpsendecho2ex`
- `https://learn.microsoft.com/en-us/windows/win32/api/icmpapi/nf-icmpapi-icmp6sendecho2`
- `https://learn.microsoft.com/en-us/windows/win32/api/ipexport/ns-ipexport-icmp_echo_reply`

## Schema

`ICMP_ECHO_FAILURE_REPLY_CONTRACT` says:

- `iphlpserver.h` owns the service broker declaration boundary.
- `iphlpserver.cpp` owns the ICMP echo API call and reply normalization logic.
- Unavailable API entry points must be represented by NULL state before
  `LoadLibrary` / `GetProcAddress` succeeds.
- A synchronous ICMP API return of zero is an error path, not a one-reply
  success path.
- On error, the broker returns the Win32 status from `GetLastError`, zero
  replies, and zero reply bytes.
- IPv4 reply pointer normalization runs only for successful replies.

## Topology

```text
sandboxed IcmpSendEcho*
-> IPHLP_SEND_ECHO_REQ
-> SbieSvc IpHlpServer
-> selected iphlpapi IcmpSendEcho2/IcmpSendEcho2Ex/Icmp6SendEcho2
-> API return count + GetLastError on zero
-> IPHLP_SEND_ECHO_RPL
-> sandboxed caller copies reply bytes and restores IPv4 Data pointers
```

Failure topology:

```text
IcmpSendEcho* returns 0
-> status = GetLastError()
-> num_replies = 0
-> reply_size = 0
-> no IPv4 Data pointer offset rewrite
```

## Logic Risk

The old path mixed two states: it preserved the failure status but also invented
one reply record. That made the service normalize a zeroed `ICMP_ECHO_REPLY`
record as if it came from the API. The sandboxed client later rewrites IPv4
reply `Data` offsets again before seeing that the status is an error. This
does not match the official synchronous failure shape and can hand callers a
mutated failure buffer that never came from `iphlpapi.dll`.

## Fix

`IpHlpServer` now initializes all six dynamic API pointers to NULL. When the
selected ICMP send API returns zero, the broker stores `GetLastError`, keeps
`num_replies` at zero, and returns zero reply bytes. IPv4 reply pointer
normalization is gated by `ERROR_SUCCESS` and a nonzero reply count.

## Acceptance Gate

`docs/plan/check-srev-211.py` validates the draft-07 schema, official
references, `IpHlpServer` declaration coordinates, source-level initialization
of the echo API pointer state, removal of the fake one-reply error path,
success-only IPv4 reply pointer normalization, split ledger fragment, and
preservation of the `IPHLP_SEND_ECHO_REQ` / `IPHLP_SEND_ECHO_RPL` wire
topology.

Runtime/build gate: Windows SbieSvc/DLL build plus ICMP smoke tests for IPv4,
IPv4 source-address echo, and IPv6 echo. Failure cases such as unreachable
destination, access denial, and deliberately too-small reply buffers must
return zero replies with the expected Win32/IP error and must not expose
rewritten fake reply data.
