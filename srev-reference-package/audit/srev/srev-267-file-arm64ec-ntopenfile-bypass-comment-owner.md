# SREV-267: File ARM64EC NtOpenFile Bypass Comment Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, SREV-054, Microsoft `GetModuleHandleW` and PE `SizeOfImage` documentation recorded by SREV-054 |
| Output artifact | `docs/plan/srev-267-file-arm64ec-ntopenfile-bypass-comment-owner.schema.json`, `docs/plan/check-srev-267.py`, `docs/plan/check-srev-267.sh`, ledger fragment, comment-only source clarification |
| Owner | `File_NtOpenFile` ARM64EC compatibility bypass, with SREV-054 owning the executable range gate |
| Acceptance gate | targeted source checker plus SREV-054 adjacency checker, core coverage, and diff checkpoint |

## Evidence

`File_NtOpenFile` has an ARM64EC-only bypass for calls whose return address is
inside `xtajit64.dll`. The old source comment said `TODO: Fix-Me` and described
the observed `__chkstk_arm64ec` stack overflow, but did not name the owner or
the gate that makes the direct `NtOpenFile` call legal.

SREV-054 already replaced the historical hard-coded range with a half-open
loaded-image range derived from the `xtajit64.dll` module base and PE
`SizeOfImage`. This SREV closes the remaining comment/topology gap: future work
must treat the bypass as a compatibility exception owned by SREV-054, not as an
unbounded TODO.

## Official Shape

SREV-054 records the official Microsoft shape for this bypass:

```text
https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandlew
https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
```

`GetModuleHandleW` identifies the loaded module in the current process. The PE
optional-header `SizeOfImage` owns the in-memory image extent. The local legal
gate is therefore the SREV-054 half-open loaded-image range.

## Data

`File_NtOpenFile`, `_ReturnAddress()`, `Dll_xtajit64`, `Dll_xtajit64_End`,
`File_NtCreateFileImpl`, and the direct `__sys_NtOpenFile` fallback.

## Schema

`FILE_ARM64EC_NTOPENFILE_BYPASS_COMMENT_OWNER` says:

- the ARM64EC direct `NtOpenFile` path is a compatibility bypass, not the normal
  Sandboxie file-policy route;
- SREV-054 owns the executable range gate for this bypass;
- the bypass is legal only when the caller return address is inside the
  SREV-054 half-open `xtajit64.dll` image range;
- stale `TODO` / `Fix-Me` wording must not remain on this bypass because it
  hides the owner and policy gate;
- this SREV changes comments and proof only; behavior remains owned by SREV-054.

## Topology

```text
ARM64EC caller return address
  -> SREV-054 xtajit64.dll half-open image range gate
  -> direct NtOpenFile compatibility bypass
  -> otherwise normal File_NtCreateFileImpl policy path
```

## Logic Risk

A stale TODO makes future changes likely to attack the wrong problem: removing
or broadening the bypass without first reproving the SREV-054 return-address
gate and ARM64EC stack-overflow runtime behavior. The topology owner must be
visible at the source line where the bypass decision is made.

## Fix

Comment-only source clarification. The source now names SREV-267 and states
that SREV-054 owns the ARM64EC compatibility bypass and half-open image range.
No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-267.py` validates the draft-07 schema, official-reference
inheritance from SREV-054, source comment owner, removal of the stale TODO/Fix-Me
wording from the bypass block, direct `NtOpenFile` bypass containment, and the
ledger fragment. `docs/plan/check-srev-054.py` also validates the SREV-267
adjacency so the executable gate and comment owner remain coupled.

Runtime gate is inherited from SREV-054: ARM64EC process with `xtajit64.dll`
loaded, return address inside image bypasses without stack overflow; return
address outside image stays on the normal Sandboxie file path; unloaded or
invalid image range disables the bypass.
