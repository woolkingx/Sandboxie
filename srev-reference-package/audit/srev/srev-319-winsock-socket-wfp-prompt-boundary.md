# SREV-319: Winsock Socket WFP Prompt Boundary

## Data

`Sandboxie/core/dll/net.c` hooks `WSASocketW`. When the driver WFP feature is
enabled and the image-level `AllowNetworkAccess` setting says network access is
not currently allowed, the hook may query the driver-side internet-access state
and may ask the interactive box manager for a manual bypass before creating the
socket.

The relevant data nodes are:

```text
WSASocketW af/type/protocol/lpProtocolInfo/g/dwFlags
WSA_WFPisEnabled / WSA_WFPisBlocking
AllowNetworkAccess
PromptForInternetAccess
SbieApi_CheckInternetAccess
File_InternetBlockade_ManualBypass
driver path-list / WFP internet-access state
provider-owned SOCKET result
```

## Official Shape

Microsoft documents `WSASocketW` as creating a socket descriptor associated with
a transport-service provider. On success it returns a `SOCKET`; otherwise it
returns `INVALID_SOCKET` and the caller retrieves provider-owned error state
through `WSAGetLastError`. The input tuple `af`, `type`, `protocol`, optional
`lpProtocolInfo`, group, and flags is passed to the transport provider selection
path.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winsock2/nf-winsock2-wsasocketw
```

Microsoft's WFP documentation describes the filter engine as the network traffic
filtering component that performs filter arbitration and returns permit/block
actions to the shim that invoked it. Driver callouts register with the filter
engine so the engine can call classify functions while processing connections or
packets.

```text
https://learn.microsoft.com/en-us/windows/win32/fwp/about-windows-filtering-platform
https://learn.microsoft.com/en-us/windows-hardware/drivers/network/filter-engine
https://learn.microsoft.com/en-us/windows-hardware/drivers/network/callout-driver
```

## Schema

Local schema:

```text
docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.schema.json
```

Contract id:

```text
WINSOCK_SOCKET_WFP_PROMPT_BOUNDARY
```

Sandboxie's DLL hook may query and refresh the local driver policy state before
socket creation, but it does not own the `WSASocketW` creation result. The
actual blocked-traffic decision is owned by the WFP driver path after the socket
exists.

## Topology

```text
application WSASocketW call
-> Sandboxie DLL prompt/manual-bypass policy refresh
-> original provider WSASocketW
-> driver WFP classify/filter enforcement on later traffic
```

SREV-190 owns the ABI shape for `P_WSASocketW` and the detour declaration.
SREV-239 owns the driver WFP module topology. SREV-319 owns only the DLL-side
socket-creation comment and proof boundary between prompt refresh and driver
enforcement.

## Logic Risk

The old comment said the hook always allowed socket creation so the process
would not crash or behave unexpectedly. That phrasing mixed a compatibility
motivation with the actual ownership boundary. The legal boundary is simpler:
`WSASocketW` creation remains provider-owned, while Sandboxie's prompt/manual
bypass refreshes driver state and the WFP driver owns later traffic enforcement.

## Fix

The source comment now names the owner split directly:

```text
socket creation remains provider-owned
prompt/manual-bypass only updates driver internet-access state
the WFP driver enforces blocked traffic after the socket exists
```

No source behavior changed.

## Acceptance Gate

`docs/plan/check-srev-319.py` validates the draft-07 schema, official Microsoft
references, `WSA_WSASocketW` prompt/manual-bypass topology, provider call
preservation, stale compatibility wording removal, local `SbieApi`/manual-bypass
evidence, SREV-190 ABI adjacency, SREV-239 WFP topology adjacency, and split
ledger fragment.

Windows gate: with WFP enabled, socket creation still follows provider-owned
`WSASocketW` behavior; denied network traffic is blocked by the driver WFP path;
prompt/manual-bypass success refreshes driver path lists and avoids repeated
prompting for the same process path.
