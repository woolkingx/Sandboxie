# SREV-265: File AltBoxPath Allocation Publication Gate

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file_init.c`, SREV-196, SREV-264, Microsoft CRT/TLS references |
| Output artifact | `docs/plan/srev-265-file-altboxpath-allocation-publication-gate.schema.json`, `docs/plan/check-srev-265.py`, `docs/plan/check-srev-265.sh`, ledger fragment, source patch |
| Owner | `file_init.c` mount-point alternate box path publication |
| Acceptance gate | targeted source checker plus SREV-196/SREV-264 adjacency checkers, core coverage, and diff checkpoint |

## Evidence

The mount-point alternate box path block allocates a TLS true-path buffer with
`Dll_GetTlsNameBuffer`, copies `Dll_BoxFilePath` into it, converts mount-point
links, allocates `File_AltBoxPath`, copies the converted path, and publishes
`File_AltBoxPathLen`.

Before this SREV, the first `wmemcpy` ran before checking whether
`Dll_GetTlsNameBuffer` returned a non-null pointer. The second allocation was
assigned directly to the global `File_AltBoxPath` before proving allocation
success or initialization. SREV-196 already proves `Dll_GetTlsNameBuffer` can
return null on allocation failure and must not publish failed allocations.

## Official Shape

Microsoft documents `TlsGetValue` as being able to return zero for a valid empty
TLS slot and documents `TlsSetValue` as a fallible publication API. SREV-196
records that local TLS/name-buffer allocation can fail and returns null. Microsoft
documents `wmemcpy` as copying a caller-provided element count from source to
destination; the destination must be a valid writable buffer.

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-tlsgetvalue
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-tlssetvalue
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memcpy-wmemcpy
```

## Data

`Dll_GetTlsNameBuffer`, `TruePath`, `Dll_BoxFilePath`, `Dll_BoxFilePathLen`,
`File_GetName_ConvertLinks`, `Dll_Alloc`, `AltBoxPath`, `File_AltBoxPath`, and
`File_AltBoxPathLen`.

## Schema

`FILE_ALTBOXPATH_ALLOCATION_PUBLICATION_GATE` says:

- `Dll_GetTlsNameBuffer` output must be checked before `wmemcpy` writes into it;
- the alternate mount-point path must be copied into a local allocation before
  `File_AltBoxPath` is published;
- `File_AltBoxPathLen` is published only after the pointer is non-null and
  initialized;
- this SREV does not change mount-point conversion semantics, prefix order,
  raw-root fallback semantics, or file policy.

## Topology

```text
Dll_BoxFilePath
  -> Dll_GetTlsNameBuffer
  -> TruePath non-null gate
  -> wmemcpy + File_GetName_ConvertLinks
  -> Dll_Alloc local AltBoxPath
  -> copy initialized path
  -> publish File_AltBoxPath + File_AltBoxPathLen
```

## Logic Risk

The old order could turn memory pressure into a null write in process
initialization. It could also publish the global alternate prefix pointer before
initialization, making later prefix consumers depend on a partially constructed
fallback.

## Fix

The first `wmemcpy` now runs only inside the `TruePath` non-null gate. The
alternate path allocation is staged in a local `AltBoxPath` pointer, copied, and
only then published to `File_AltBoxPath` with `File_AltBoxPathLen`.

## Acceptance Gate

`docs/plan/check-srev-265.py` validates the draft-07 schema, official references,
`file_init.c` gate order, removal of stale pre-gate copy/global-publish shape,
SREV-196/SREV-264 adjacency, and the ledger fragment.

Runtime gate: Windows mount-point alternate box path smoke plus allocation
failure injection for `Dll_GetTlsNameBuffer` and `Dll_Alloc`.
