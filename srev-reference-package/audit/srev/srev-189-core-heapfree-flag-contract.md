# SREV-189 Core HeapFree Flag Contract

| Field | Content |
|---|---|
| Stage | schema -> boundary -> action -> verify |
| Input Artifact | `Sandboxie/core` `HeapFree` call sites discovered while reviewing the `ServiceServer` service broker topology. |
| Output Artifact | Draft-07 schema, source-level checker, split ledger fragment, and source readback proving `HeapFree` no longer receives `HEAP_GENERATE_EXCEPTIONS`. |
| Owner | `Sandboxie/core` Win32 heap free call sites. |
| Acceptance Gate | `docs/plan/check-srev-189.py`, `docs/plan/check-srev-189.sh`, core coverage, full SREV/KPATH matrix, and `git diff --check`. |

## Data

The review entered through `Sandboxie/core/svc/serviceserver.h`, whose concrete
service-broker implementation lives in `Sandboxie/core/svc/serviceserver.cpp`.
`ServiceServer::ListHandler` allocated `buf` with `HeapAlloc(GetProcessHeap(),
0, buf_len)`, then freed it with `HeapFree(GetProcessHeap(),
HEAP_GENERATE_EXCEPTIONS, buf)`.

The same API-shape mismatch appeared across these core files:

- `Sandboxie/core/dll/ipstore_impl.cpp`
- `Sandboxie/core/dll/scm_create.c`
- `Sandboxie/core/dll/support.c`
- `Sandboxie/core/dll/sysinfo.c`
- `Sandboxie/core/svc/DriverAssist.cpp`
- `Sandboxie/core/svc/GuiServer.cpp`
- `Sandboxie/core/svc/ProcessServer.cpp`
- `Sandboxie/core/svc/UserServer.cpp`
- `Sandboxie/core/svc/netapiserver.cpp`
- `Sandboxie/core/svc/sbieiniserver.cpp`
- `Sandboxie/core/svc/serviceserver.cpp`
- `Sandboxie/core/svc/serviceserver2.cpp`

## Official API Shape

Microsoft documents `HeapFree` as accepting `HEAP_NO_SERIALIZE` as the named
heap-free option. The same page describes `lpMem` as the block returned by
`HeapAlloc` or `HeapReAlloc`, and says `HeapFree` returns zero on failure.

Microsoft documents `HEAP_GENERATE_EXCEPTIONS` on `HeapAlloc`, where it changes
allocation failure behavior. It is not documented as a `HeapFree` option.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapfree`
- `https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapalloc`

## Boundary

The boundary is local process heap ownership inside Sandboxie core. Allocation
flags and free flags are not the same schema:

```text
HeapAlloc(..., HEAP_GENERATE_EXCEPTIONS, size) -> allocation failure policy
HeapFree(..., 0, ptr)                          -> normal serialized free
```

`HEAP_NO_SERIALIZE` is not used here because these call sites use the process
heap. Microsoft warns against using `HEAP_NO_SERIALIZE` with the process heap.

## Topology

The legal flow is:

```text
core owner allocates process-heap memory
-> pointer lifetime crosses local helper logic
-> owner releases with HeapFree(GetProcessHeap() or heap, 0, ptr)
```

The illegal flow was:

```text
core owner releases with HeapFree(..., HEAP_GENERATE_EXCEPTIONS, ptr)
```

That passes an allocation-only flag into a free API field.

## Logic Risk

The old calls relied on undocumented behavior for an API control field. If
`HeapFree` rejects or changes handling of unsupported flags, service broker and
DLL cleanup paths can leak memory or fail to release temporary buffers. Even if
current Windows versions tolerate the bit, the code is not using the official
contract.

## Fix

All `HeapFree` calls under `Sandboxie/core` that passed
`HEAP_GENERATE_EXCEPTIONS` now pass `0`. Allocation call sites are unchanged.
No buffer sizes, lifetimes, service policy, token logic, or broker behavior were
otherwise changed.

## Runtime Gate

Linux source checks can prove the call-site contract. A Windows runtime gate is
still useful: exercise the service-list, boxed-service create/start, GUI/User
helper, NetAPI, ProcessServer, and DLL cleanup paths under Application Verifier
or heap instrumentation and confirm there are no heap-free failures or leaks
caused by these releases.
