---
kind: srev-ledger-entry
id: SREV-189
title: Core HeapFree Flag Contract
status: patched-source-level-after-official-heap-api-shape-review-needs-windows-heap-runtime-proof
owner: Sandboxie/core
spec: docs/plan/srev-189-core-heapfree-flag-contract.md
schema: docs/plan/srev-189-core-heapfree-flag-contract.schema.json
checker: docs/plan/check-srev-189.py
runtime_gate: Windows Application Verifier or heap instrumentation across service-list boxed-service GUI User NetAPI ProcessServer and DLL cleanup paths
---
### SREV-189: Core HeapFree Flag Contract

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official heap API shape review; needs Windows heap runtime proof |
| Evidence | `Sandboxie/core/svc/serviceserver.h` was the highest-ranked unnamed reviewable core file after SREV-188. Its service broker implementation in `Sandboxie/core/svc/serviceserver.cpp` released `ServiceServer::ListHandler` enumeration buffers with `HeapFree(GetProcessHeap(), HEAP_GENERATE_EXCEPTIONS, buf)`. A core-wide scan found the same `HeapFree(..., HEAP_GENERATE_EXCEPTIONS, ...)` shape in `Sandboxie/core/dll/ipstore_impl.cpp`, `Sandboxie/core/dll/scm_create.c`, `Sandboxie/core/dll/support.c`, `Sandboxie/core/dll/sysinfo.c`, `Sandboxie/core/svc/DriverAssist.cpp`, `Sandboxie/core/svc/GuiServer.cpp`, `Sandboxie/core/svc/ProcessServer.cpp`, `Sandboxie/core/svc/UserServer.cpp`, `Sandboxie/core/svc/netapiserver.cpp`, `Sandboxie/core/svc/sbieiniserver.cpp`, `Sandboxie/core/svc/serviceserver.cpp`, and `Sandboxie/core/svc/serviceserver2.cpp`. |
| Data | Process-heap pointers, `HeapAlloc`, `HeapFree`, `GetProcessHeap`, private heap handles, `HEAP_GENERATE_EXCEPTIONS`, `HEAP_NO_SERIALIZE`, and core cleanup call sites. |
| Schema | `CORE_HEAPFREE_FLAG_CONTRACT` says `HeapFree` owns release of memory blocks allocated by `HeapAlloc` or `HeapReAlloc`; `HeapFree.dwFlags` uses the heap-free option schema; these process-heap releases must pass `0`; `HEAP_GENERATE_EXCEPTIONS` is an allocation option documented for `HeapAlloc` and must not be passed to `HeapFree`; `HEAP_NO_SERIALIZE` remains disallowed for these process-heap release call sites; this SREV changes only the `HeapFree` flag argument. |
| Topology | Legal flow is `core owner allocates process-heap memory -> pointer lifetime crosses local helper logic -> owner releases with HeapFree(GetProcessHeap() or heap, 0, ptr)`. The old flow passed an allocation-only option into the free API's control field. |
| Logic Risk | The old calls relied on undocumented handling of an unsupported `HeapFree` flag. If Windows rejects or changes handling of the bit, cleanup paths can fail to release temporary buffers. Even if current builds tolerate it, the code was not using Microsoft's API contract. |
| Official Shape | `docs/plan/srev-189-core-heapfree-flag-contract.md` records Microsoft `HeapFree` and `HeapAlloc` references. `docs/plan/srev-189-core-heapfree-flag-contract.schema.json` records the JSON Schema draft-07 local `CORE_HEAPFREE_FLAG_CONTRACT` contract. |
| Fix | All `HeapFree` calls under `Sandboxie/core` that passed `HEAP_GENERATE_EXCEPTIONS` now pass `0`. Allocation flags, buffer sizes, service policy, token logic, and broker behavior were not changed. |
| Acceptance Gate | `docs/plan/check-srev-189.py` validates the draft-07 schema, official references, source readback for representative changed calls, absence of `HeapFree(... HEAP_GENERATE_EXCEPTIONS ...)` under `Sandboxie/core`, and split ledger fragment; `docs/plan/check-srev-189.sh` is the matrix wrapper. Runtime gate: Windows Application Verifier or heap instrumentation across service-list, boxed-service, GUI/User helper, NetAPI, ProcessServer, and DLL cleanup paths. |
