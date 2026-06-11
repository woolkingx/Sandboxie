---
kind: srev-ledger-entry
id: SREV-196
title: DLL TLS Name Buffer Allocation Contract
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/dll/dllmem.c
spec: docs/plan/srev-196-dll-tls-name-buffer-allocation-contract.md
schema: docs/plan/srev-196-dll-tls-name-buffer-allocation-contract.schema.json
checker: docs/plan/check-srev-196.py
runtime_gate: Windows DLL build plus allocation/TLS/depth fault-injection smoke
---

### SREV-196: DLL TLS Name Buffer Allocation Contract

Schema: `DLL_TLS_NAME_BUFFER_ALLOCATION_CONTRACT`

`Sandboxie/core/dll/dllmem.c` owns DLL pool allocation wrappers, TLS
`THREAD_DATA`, and per-thread name-buffer reuse. The previous source shape had
four local owner-boundary gaps:

- pool allocation size arithmetic added debug padding and the hidden
  `ULONG_PTR` prefix without checking `ULONG` wrap;
- `Dll_GetTlsData` zeroed the new `THREAD_DATA` without checking allocation and
  ignored the `TlsSetValue` publication result;
- `Dll_GetTlsNameBuffer` rounded `size + 64 + PAGE_SIZE - 1` without checking
  overflow and published the new slot length before proving allocation success;
- push/pop depth transitions could index or leave `name_buffer_depth` outside
  the legal range.

Official TLS API shape:

- `TlsAlloc` returns `TLS_OUT_OF_INDEXES` on failure.
- `TlsGetValue` can return `NULL` for a valid empty slot and clears last error
  on success.
- `TlsSetValue` returns zero on failure.

Patch:

- added `Dll_AddUlong`, `Dll_RoundTlsNameBufferSize`, and
  `Dll_AllocFailure`;
- made `Dll_AllocFromPool` check every `ULONG` addition before `Pool_Alloc`;
- made `Dll_GetTlsData` check allocation before `memzero` and free the new
  `THREAD_DATA` if `TlsSetValue` fails;
- made `Dll_GetTlsNameBuffer` allocate into a temporary pointer and publish
  pointer/length only after success;
- guarded `Dll_PushTlsNameBuffer` before incrementing/indexing;
- prevented `Dll_PopTlsNameBuffer` from making depth negative;
- corrected DEBUG_MEMORY checks to index with `name_buffer_depth`.

Linux source gate:

```text
python3 docs/plan/check-srev-196.py
bash docs/plan/check-srev-196.sh
python3 docs/plan/check-core-coverage.py
git diff --check
```

Runtime gate remains a Windows DLL build plus allocation/TLS/depth
fault-injection smoke.

SREV-265 adds a caller-side adjacency for this contract: `file_init.c`
mount-point alternate path initialization now checks the `Dll_GetTlsNameBuffer`
result before copying into it.
