# SREV-196: DLL TLS Name Buffer Allocation Contract

Stage: schema -> boundary -> action -> verify

Input artifact: `Sandboxie/core/dll/dllmem.c`

Output artifact: DLL memory/TLS helpers bound integer addition, preserve TLS
last-error behavior, and never publish a failed name-buffer allocation into
`THREAD_DATA`.

Owner: `Sandboxie/core/dll/dllmem.c`

Acceptance gate: `docs/plan/check-srev-196.py` plus
`docs/plan/check-srev-196.sh`.

## Data

`dllmem.c` owns three local data shapes:

- pool allocations store a hidden `ULONG_PTR` size prefix before the returned
  caller pointer;
- `THREAD_DATA` is stored in a Windows TLS slot allocated by `TlsAlloc`;
- per-thread name buffers are indexed by `name_buffer[which][depth]` and sized
  by counted bytes rounded up to `PAGE_SIZE`.

Local evidence:

- `Dll_AllocFromPool` previously added debug padding and the hidden prefix to a
  caller-supplied `ULONG` without an overflow gate.
- `Dll_GetTlsData` allocated `THREAD_DATA`, immediately zeroed it, and ignored
  the `TlsSetValue` return value.
- `Dll_GetTlsNameBuffer` rounded `size + 64 + PAGE_SIZE - 1` without checking
  overflow, then assigned the new length and pointer before proving allocation
  success.
- `Dll_PushTlsNameBuffer` incremented `name_buffer_depth` and wrote
  `name_buffer_count[depth]` before proving the new depth was in range.
- `Dll_PopTlsNameBuffer` allowed `name_buffer_depth` to go negative after an
  unmatched pop.

## Official API Shape

Microsoft documents `TlsAlloc` as returning `TLS_OUT_OF_INDEXES` on failure and
initializing slots to zero on success:

https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-tlsalloc

Microsoft documents `TlsGetValue` as returning the current TLS slot value and
states that a zero return can be a successful zero value; it clears last error
on success, so callers that preserve last error must save and restore it:

https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-tlsgetvalue

Microsoft documents `TlsSetValue` as returning nonzero on success and zero on
failure:

https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-tlssetvalue

## Boundary

The boundary is:

```text
caller byte count -> dllmem allocator/name-buffer owner -> local pool/TLS state
Windows TLS API -> Dll_GetTlsData -> THREAD_DATA pointer lifetime
```

`Pool_Alloc` accepts an `ULONG` size and returns `NULL` on impossible or failed
allocation. `dllmem.c` owns translating caller byte counts into that pool size.
No caller may cause integer wrap before the pool gate.

`TlsSetValue` is the publication edge for a newly allocated `THREAD_DATA`.
If publication fails, `dllmem.c` still owns the allocation and must free it
instead of leaking or returning a pointer that is not stored in TLS.

## Topology

```text
Dll_GetTlsData
  -> TlsGetValue
  -> Dll_Alloc(THREAD_DATA)
  -> memzero only after allocation success
  -> TlsSetValue publication
  -> free on publication failure

Dll_GetTlsNameBuffer
  -> checked round-up to PAGE_SIZE
  -> allocate new buffer into a temporary pointer
  -> copy old contents
  -> publish pointer and length only after success
```

SREV-265 records one caller-side consequence in `file_init.c`: mount-point
alternate path initialization must check the returned TLS name buffer before
copying `Dll_BoxFilePath` into it.

Depth transitions:

```text
push: depth < NAME_BUFFER_DEPTH - 1 -> increment -> initialize count
pop:  depth > 0 -> decrement
```

## Logic

The previous code treated arithmetic and TLS publication as if they could not
fail. That is not a legal owner boundary for a shared allocator used by many
hook paths.

The minimal fix is:

- add a checked `ULONG` addition helper;
- use it for the hidden pool prefix and debug padding;
- use it for TLS name-buffer page rounding;
- do not zero or publish a `THREAD_DATA` allocation unless allocation succeeded;
- free `THREAD_DATA` if `TlsSetValue` fails;
- allocate a replacement name buffer into a temporary pointer and publish it
  only after success;
- guard push and pop depth transitions before array indexing;
- keep Windows build/runtime proof explicit because this Linux pass is source
  level only.

## Verification

Linux source gates prove:

- checked arithmetic is used before pool allocation and name-buffer rounding;
- failed allocation cannot be passed to `memzero`;
- failed `TlsSetValue` frees the new `THREAD_DATA`;
- failed name-buffer replacement leaves the existing pointer and length intact;
- push/pop depth gates happen before out-of-range index mutation;
- DEBUG_MEMORY checks use `name_buffer_depth`, not a non-existent depth field.

Runtime gate:

- Windows DLL build with normal and `DEBUG_MEMORY` configurations.
- Fault injection for allocation failure, `TlsSetValue` failure, name-buffer
  overflow-size input, push at `NAME_BUFFER_DEPTH - 1`, and unmatched pop.
