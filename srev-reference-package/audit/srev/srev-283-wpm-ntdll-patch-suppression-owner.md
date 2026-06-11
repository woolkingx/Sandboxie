# SREV-283: WriteProcessMemory NTDLL Patch Suppression Owner

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Input artifact | `Sandboxie/core/dll/file_misc.c`, SREV-075, Microsoft `WriteProcessMemory` documentation, and adjacent `NtMapViewOfSection` / `NtSetInformationThread` hook owners |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `File_WriteProcessMemory` Firefox/Thunderbird ntdll patch suppression branch |
| Acceptance gate | Targeted checker validates official reference, narrow target export predicate, SREV-075 output gate adjacency, real fallback preservation, stale workaround wording removal, and ledger fragment |

## Data

`File_WriteProcessMemory` intercepts Win32 `WriteProcessMemory` calls. For
non-compartment Firefox or Thunderbird processes, it suppresses writes that
target the process-local `ntdll` export addresses for:

```text
NtSetInformationThread
NtMapViewOfSection
```

The suppression branch claims success without calling the real
`__sys_WriteProcessMemory` owner. SREV-075 already owns the output-parameter
shape for this fake-success branch: NULL `lpNumberOfBytesWritten` is ignored,
and non-NULL output is written under SEH so a bad caller slot fails with
`ERROR_NOACCESS`.

## Official Shape

Microsoft documents `WriteProcessMemory` as writing data to an area of memory in
a specified process. The entire target area must be accessible or the operation
fails. `lpNumberOfBytesWritten` is optional; if it is NULL, the parameter is
ignored.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-writeprocessmemory`

## Schema

Local schema:

```text
docs/plan/srev-283-wpm-ntdll-patch-suppression-owner.schema.json
```

Contract id:

```text
WPM_NTDLL_PATCH_SUPPRESSION_OWNER
```

## Boundary

```text
caller WriteProcessMemory
  -> File_WriteProcessMemory hook
  -> Firefox/Thunderbird image gate
  -> ntdll export-address gate
  -> local fake-success suppression branch
```

Sandboxie owns this branch only after it chooses not to call the real Win32 API
owner. All non-matching writes must continue to `__sys_WriteProcessMemory`.

## Topology

```text
Dll_CompartmentMode true
  -> no suppression branch
  -> real __sys_WriteProcessMemory

non-compartment Firefox/Thunderbird + target is selected ntdll export
  -> fake success
  -> SREV-075 output gate

anything else
  -> hook trace if enabled
  -> real __sys_WriteProcessMemory
```

## Logic Risk

The old comment described the branch as a generic third-party workaround. That
blurs the boundary between a narrow Firefox/Thunderbird `ntdll` patch
suppression branch and the general `WriteProcessMemory` API owner. Future edits
could expand the branch to more target addresses or image types without proving
the caller contract, or could bypass SREV-075's output-parameter gate.

## Fix

Comment-only source clarification. The source now names SREV-283 and states
that the branch suppresses only Firefox/Thunderbird writes to the selected
`ntdll` export addresses, while SREV-075 owns the fake-success output contract.
No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-283.py` validates the draft-07 schema, official
reference, source predicate, selected `ntdll` exports, SREV-075 output gate
adjacency, real fallback preservation, stale workaround wording removal, and
ledger fragment.

Runtime gate: Windows Firefox/Thunderbird matrix inherited from SREV-075, plus
target-address regression proof that only `NtSetInformationThread` and
`NtMapViewOfSection` writes enter the fake-success branch while other
`WriteProcessMemory` calls reach the real API owner.
