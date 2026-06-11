# SREV-216: PDH Status ABI Contract

## Stage

schema -> boundary -> topology -> logic -> action -> verify

## Evidence

`Sandboxie/core/dll/pdh.c` was the top unnamed reviewable core file after
SREV-215. It owns Sandboxie's PDH deny hooks for `PdhConnectMachineW` and
`PdhLookupPerfNameByIndexW`. The hook module loads `Pdh.dll`, resolves those
two exports, installs replacements through `SBIEDLL_HOOK`, and returns a denial
status to callers so sandboxed code cannot access performance counters through
PDH.

Before this fix, both local function-pointer typedefs and both hook functions
used `UINT`. The official PDH surface returns `PDH_STATUS`. The hook also
returned `ERROR_ACCESS_DENIED`, a generic system error value, instead of the
PDH-specific `PDH_ACCESS_DENIED` status that names the denied performance-data
boundary.

## Data

`pdh.c`, `dll.h`, `ldr.c`, `Pdh_Init`, `Pdh_PdhConnectMachineW`,
`Pdh_PdhLookupPerfNameByIndexW`, `P_PdhConnectMachineW`,
`P_PdhLookupPerfNameByIndexW`, `__sys_PdhConnectMachineW`,
`__sys_PdhLookupPerfNameByIndexW`, `GetProcAddress`, `SBIEDLL_HOOK`,
`PDH_STATUS`, `PDH_ACCESS_DENIED`, `PdhConnectMachineW`, and
`PdhLookupPerfNameByIndexW`.

## Official Shape

Microsoft documents `PdhConnectMachineW` with the `PDH_FUNCTION` return shape.
On success it returns `ERROR_SUCCESS`; on failure it returns a system error code
or a PDH error code.

Microsoft documents `PdhLookupPerfNameByIndexW` with the same `PDH_FUNCTION`
return shape. Its output buffer and size are used only on successful or
buffer-size query paths; a policy denial does not own output writes.

Microsoft's PDH error-code page says all PDH functions return `PDH_STATUS`,
and lists `PDH_ACCESS_DENIED` as the PDH-specific status for being unable to
access the desired computer or service.

References:

- `https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhconnectmachinew`
- `https://learn.microsoft.com/en-us/windows/win32/api/pdh/nf-pdh-pdhlookupperfnamebyindexw`
- `https://learn.microsoft.com/en-us/windows/win32/perfctrs/pdh-error-codes`

## Schema

`PDH_STATUS_ABI_CONTRACT` says:

- `pdh.c` owns Sandboxie's DLL-side PDH deny hooks.
- Local PDH function-pointer typedefs use `PDH_STATUS`, matching the official
  PDH return contract.
- Hook functions use `PDH_STATUS`, matching the resolved export ABI.
- Policy denial returns `PDH_ACCESS_DENIED`.
- Hook installation and the selected PDH export set remain unchanged.

## Topology

```text
Pdh.dll export
-> GetProcAddress
-> local P_Pdh* typedef
-> SBIEDLL_HOOK original-function storage
-> Pdh_Pdh* replacement
-> PDH_ACCESS_DENIED
```

## Logic Risk

Hook wrappers are ABI boundaries. A generic integer return type hides the
external API contract and makes future edits more likely to treat PDH as a
plain Win32 `UINT` API. Returning generic `ERROR_ACCESS_DENIED` is allowed by
some PDH documentation as a system error shape, but it does not name the
performance-data policy denial that this module owns. The correct local schema
is the official `PDH_STATUS` surface with explicit `PDH_ACCESS_DENIED`.

## Fix

`pdh.c` now includes `pdh.h`, declares the two PDH typedefs and hook functions
with `PDH_STATUS`, and returns `PDH_ACCESS_DENIED` from both deny hooks.

Hook selection, export resolution, and `SBIEDLL_HOOK` installation are
unchanged.

## Acceptance Gate

`docs/plan/check-srev-216.py` validates the draft-07 schema, official
references, `pdh.h` inclusion, `PDH_STATUS` typedef and hook signatures,
`PDH_ACCESS_DENIED` policy return, unchanged `GetProcAddress`/`SBIEDLL_HOOK`
topology, split ledger fragment, and removal of the stale `UINT`/generic
`ERROR_ACCESS_DENIED` PDH return shape.

Runtime/build gate: Windows DLL build plus sandboxed PDH smoke for
`PdhConnectMachineW` and `PdhLookupPerfNameByIndexW`, proving callers receive a
PDH failure status without successful performance-counter access and without
unexpected output-buffer writes on denied calls.
