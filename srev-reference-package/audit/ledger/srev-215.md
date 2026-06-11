---
kind: srev-ledger-entry
id: SREV-215
title: ProxyHandle Destructor Drain
status: patched-source-level-after-official-heap-and-critical-section-lifetime-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/ProxyHandle.cpp
declaration: Sandboxie/core/svc/ProxyHandle.h
spec: docs/plan/srev-215-proxyhandle-destructor-drain.md
schema: docs/plan/srev-215-proxyhandle-destructor-drain.schema.json
checker: docs/plan/check-srev-215.py
runtime_gate: Windows SbieSvc build plus service-shutdown smoke with outstanding ICMP and named-pipe proxy handles, proving each downstream close callback runs once, entries are freed, and no worker uses ProxyHandle after the destructor starts.
---

### SREV-215: ProxyHandle Destructor Drain

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official heap and critical-section lifetime review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/ProxyHandle.cpp` was the top unnamed reviewable core file after SREV-214. It owns the service-side proxy-handle table used by `IpHlpServer` and `NamedPipeServer`. `ProxyHandle::Create` allocates a `PROXY_HANDLE` from `m_heap`, copies model data into the entry, and inserts it into `m_list`. `Release`, `Close`, and `ReleaseProcess` release entries by invoking `m_close_callback`, removing the list element, and freeing the heap block. Before this fix, `ProxyHandle::~ProxyHandle` only called `DeleteCriticalSection(&m_lock)`, so destroying the owner while entries remained skipped callback cleanup and leaked the entry blocks. |
| Data | `ProxyHandle.cpp`, `ProxyHandle.h`, `PROXY_HANDLE`, `m_list`, `m_lock`, `m_heap`, `m_close_callback`, `m_context_for_callback`, `Create`, `Find`, `Close`, `Release`, `ReleaseProcess`, `HeapAlloc`, `HeapFree`, `InitializeCriticalSectionAndSpinCount`, `DeleteCriticalSection`, `IpHlpServer::CloseCallback`, `NamedPipeServer::CloseCallback`, ICMP handles, named-pipe handles, completion events, and per-pipe I/O locks. |
| Schema | `PROXYHANDLE_DESTRUCTOR_DRAIN` says `ProxyHandle.cpp` owns the lifetime of every `PROXY_HANDLE` allocated from `m_heap`; every published `PROXY_HANDLE` is reachable from `m_list` until removed; releasing a proxy entry must call `m_close_callback` exactly once before `HeapFree` releases the entry allocation; the destructor must drain every remaining list entry before deleting `m_lock`; and normal `Close`, `Release`, and `ReleaseProcess` behavior remains unchanged. |
| Topology | Entry acquisition is `Create -> HeapAlloc(sizeof(PROXY_HANDLE) + m_size_of_data) -> copy model_data into proxy->data -> List_Insert_After(m_list)`. Entry release is `proxy entry -> m_close_callback(context, &proxy->data) -> List_Remove(m_list, proxy) -> HeapFree(m_heap, proxy)`. Destructor release is `~ProxyHandle -> EnterCriticalSection(m_lock) -> repeat list-head release path until m_list empty -> LeaveCriticalSection(m_lock) -> DeleteCriticalSection(m_lock)`. |
| Logic Risk | `ProxyHandle` is a generic owner, but downstream resources are hidden behind the close callback. Deleting the synchronization primitive without walking the list discards the only owner path for entries that were not closed by process notification or explicit close requests. In `IpHlpServer`, that can skip `IcmpCloseHandle`; in `NamedPipeServer`, it can skip named-pipe handle, completion-event, and per-pipe lock cleanup. |
| Official Shape | `docs/plan/srev-215-proxyhandle-destructor-drain.md` records Microsoft `HeapAlloc`, `HeapFree`, `InitializeCriticalSectionAndSpinCount`, and `DeleteCriticalSection` references. `docs/plan/srev-215-proxyhandle-destructor-drain.schema.json` records the JSON Schema draft-07 local `PROXYHANDLE_DESTRUCTOR_DRAIN` contract. |
| Fix | `ProxyHandle::~ProxyHandle` now enters `m_lock`, walks all remaining entries, calls `m_close_callback` for each entry's data, removes each list element, frees the heap allocation, leaves the lock, and only then deletes the critical section. `Create`, `Find`, `Close`, `Release`, and `ReleaseProcess` keep their existing runtime behavior. |
| Acceptance Gate | `docs/plan/check-srev-215.py` validates the draft-07 schema, official references, destructor drain ordering, close-callback/list-remove/heap-free release shape, preservation of normal `Close`, `Release`, and `ReleaseProcess` paths, split ledger fragment, and removal of the stale destructor-only critical-section cleanup shape; `docs/plan/check-srev-215.sh` is the targeted wrapper. Runtime/build gate: Windows SbieSvc build plus service-shutdown smoke with outstanding ICMP and named-pipe proxy handles, proving each downstream close callback runs once, entries are freed, and no worker uses `ProxyHandle` after the destructor starts. |
