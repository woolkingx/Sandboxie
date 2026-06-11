---
kind: srev-ledger-entry
id: SREV-190
title: Winsock ABI Function Pointer Contract
status: patched-source-level-after-official-winsock-abi-shape-review-needs-windows-x86-x64-runtime-proof
owner: Sandboxie/core/dll/wsa_defs.h
spec: docs/plan/srev-190-winsock-abi-function-pointer-contract.md
schema: docs/plan/srev-190-winsock-abi-function-pointer-contract.schema.json
checker: docs/plan/check-srev-190.py
runtime_gate: Windows x86 and x64 build plus Winsock socket connect ConnectEx send recv sendto recvfrom bind-IP proxy and DNS-filter runtime proof
---
### SREV-190: Winsock ABI Function Pointer Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official Winsock ABI shape review; needs Windows x86/x64 runtime proof |
| Evidence | `Sandboxie/core/dll/wsa_defs.h` was the top unnamed reviewable core file after SREV-189. It declared local dynamically resolved Winsock function pointers without `WSAAPI`, declared `P_socket` as returning `int`, declared `P_WSASetLastError` as returning `int`, declared `P_getsockname` with a const output address pointer, and declared `P_ConnectEx`/`P_AcceptEx` as `int` returns. `Sandboxie/core/dll/net.c` installs detours with `SBIEDLL_HOOK` and returns `WSA_ConnectEx` through `WSAIoctl(SIO_GET_EXTENSION_FUNCTION_POINTER)`, so these declarations are ABI contracts, not style. |
| Data | `P_WSAStartup`, `P_socket`, `P_WSASocketW`, `P_WSASetLastError`, `P_getsockname`, `P_ConnectEx`, `P_AcceptEx`, `P_GetAdaptersAddresses`, `WSA_*` detour functions, `SBIEDLL_HOOK`, `__sys_*` provider pointers, and `SIO_GET_EXTENSION_FUNCTION_POINTER`. |
| Schema | `WINSOCK_ABI_FUNCTION_POINTER_CONTRACT` says Winsock function pointers must use `WSAAPI`; `P_GetAdaptersAddresses` must use `WINAPI`; `socket` and `WSASocketW` return `SOCKET`; `WSASetLastError` returns `void`; `getsockname` receives a writable output address pointer; `ConnectEx` and `AcceptEx` return `BOOL`; `net.c` detour entry points must use the same calling convention; `ConnectEx` failure paths must return `FALSE`, not `SOCKET_ERROR`. |
| Topology | Legal topology is `official Winsock API shape -> wsa_defs.h function pointer typedef -> net.c detour prototype and definition -> SBIEDLL_HOOK / WSAIoctl extension replacement -> __sys_* original provider call`. |
| Logic Risk | On 32-bit builds, calling a `WSAAPI` provider through a plain C function pointer can corrupt stack ownership. Returning `int` for APIs whose official return is `SOCKET` can truncate socket handles on 64-bit. Returning `SOCKET_ERROR` from a `BOOL` `ConnectEx` detour reports local failure as nonzero success. |
| Official Shape | `docs/plan/srev-190-winsock-abi-function-pointer-contract.md` records Microsoft Winsock, `ConnectEx`, `WSASetLastError`, `getsockname`, and `GetAdaptersAddresses` references. `docs/plan/srev-190-winsock-abi-function-pointer-contract.schema.json` records the JSON Schema draft-07 local `WINSOCK_ABI_FUNCTION_POINTER_CONTRACT` contract. |
| Fix | `wsa_defs.h` now marks Winsock function pointer typedefs with `WSAAPI`, marks `P_GetAdaptersAddresses` with `WINAPI`, uses `SOCKET` returns for `socket`/`WSASocketW`, `void` for `WSASetLastError`, writable `void *name` for `getsockname`, and `BOOL` for `ConnectEx`/`AcceptEx`. The hooked `net.c` detour prototypes and definitions now use `WSAAPI`; `WSA_ConnectEx` now returns `FALSE` on local failure paths and stores the provider result as `BOOL`. |
| Acceptance Gate | `docs/plan/check-srev-190.py` validates the draft-07 schema, official references, `wsa_defs.h` ABI typedefs, absence of unannotated function pointer typedefs in `wsa_defs.h`, `net.c` detour calling convention, `ConnectEx` false-failure shape, and split ledger fragment; `docs/plan/check-srev-190.sh` is the matrix wrapper. Runtime gate: Windows x86 and x64 build plus Winsock socket, connect, ConnectEx, send/recv, sendto/recvfrom, bind-IP, proxy, and DNS-filter runtime proof. |
