# SREV-258: Custom SYSFER Comment Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/custom.c`, SREV-055, Microsoft PE / executable-code references |
| Output artifact | `docs/plan/srev-258-custom-sysfer-comment-owner.schema.json`, `docs/plan/check-srev-258.py`, `docs/plan/check-srev-258.sh`, ledger fragment, comment-only source clarification |
| Owner | `Custom_SYSFER_DLL` source comment for SREV-055 entry-point patch boundary |
| Acceptance gate | targeted source checker plus SREV-055 adjacency checker, core coverage, and diff checkpoint |

## Evidence

SREV-055 already owns and hardens the SYSFER entry-point patch: PE signature
gates, bounded entry-point span, exact `VirtualProtect` range,
`FlushInstructionCache`, and protection restore.

The remaining `custom.c` comment still described the patch as a generic
workaround to nullify `SYSFER.DLL`. That wording hides the exact owner and can
misroute future work into broad third-party patching instead of the already
documented PE entry-point boundary.

Official references are inherited from SREV-055:

- https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache

## Data

`Custom_SYSFER_DLL`, `SYSFER.DLL`, PE DOS/NT headers, `AddressOfEntryPoint`,
`SizeOfImage`, four-byte `mov al, 1; ret` patch, `VirtualProtect`,
`FlushInstructionCache`, and SREV-055.

## Schema

`CUSTOM_SYSFER_COMMENT_OWNER` says:

- SREV-055 owns the executable-code patch boundary for `SYSFER.DLL`;
- the source comment must name the bounded entry-point patch owner rather than a
  generic workaround;
- this SREV does not change PE validation, patch bytes, page protection,
  instruction-cache coherency, or Symantec compatibility behavior.

## Topology

```text
SYSFER.DLL load
  -> valid PE image and entry-point span
  -> SREV-055 bounded entry-point patch owner
  -> exact four-byte patch plus instruction-cache coherency
```

## Logic Risk

Generic workaround wording obscures the fact that the code is an executable-code
mutation with strict PE and cache-coherency gates. Future patches should extend
or revise SREV-055's owner boundary rather than treating this as anonymous
third-party residue.

## Fix

Comment-only source clarification. The source now says SREV-055 owns the
bounded entry-point patch for the `SYSFER.DLL` load path. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-258.py` validates the draft-07 schema, SREV-055 adjacency,
source comment, removal of the stale generic workaround wording, unchanged
patch behavior evidence, and the ledger fragment.

Runtime gate: inherited from SREV-055. Windows endpoint-protection compatibility
proof remains required for behavior closure.
