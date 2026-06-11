# SREV-246: DLL Hook Unity NOP Padding Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/dllhook.c`, `Sandboxie/core/dll/hook_tramp.c`, SREV-058, SREV-091, Intel and Microsoft executable-code references |
| Output artifact | `docs/plan/srev-246-dllhook-unity-nop-padding-boundary.schema.json`, `docs/plan/check-srev-246.py`, `docs/plan/check-srev-246.sh`, ledger fragment, comment-only source clarification |
| Owner | `SbieDll_Hook_x86` detour patch span in `dllhook.c` |
| Acceptance gate | targeted source checker plus core coverage/diff checkpoint; behavior changes still require Windows hook and Unity runtime proof |

## Evidence

`SbieDll_Hook_x86` builds a trampoline through `SbieApi_HookTramp`, writes a
detour at the source function entry, restores page protection, and flushes the
instruction cache. Immediately after the detour write block, the old source
comment proposed NOP-padding the rest of the moved bytes but left it disabled
because it broke Unity games:

```c
// just in case nop out the rest of the code we moved to the trampoline
// ToDo: why does this break unity games
//for(; UsedCount < ByteCount; UsedCount++)
//    func[UsedCount] = 0x90; // nop
```

Local topology shows why this is not a harmless cleanup:

- `SbieApi_HookTramp` / `hook_tramp.c` owns moved-instruction counting and stores
  the copied byte count in the trampoline header.
- `dllhook.c` currently comments out both `ByteCount` and `UsedCount`.
- The active source patch writes only the detour envelope: 5-byte x86 relative
  jump, 6-byte x64 RIP-indirect jump, or 6-byte Windows 10 REX.W relative jump.
- SREV-058 owns page-protection and instruction-cache coherency for this hook
  writer.
- SREV-091 owns preserving third-party detour envelopes such as `PUSH imm32`;
  `RET`.

Official references:

- https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html
- https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect
- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache

## Data

`SbieDll_Hook_x86`, `SbieApi_HookTramp`, `Hook_Tramp_CountBytes`,
`Hook_Tramp_Copy`, `ByteCount`, `UsedCount`, source-function detour bytes,
trampoline bytes, x86 `E9 rel32`, x64 `FF 25 rip+disp32`, Windows 10 `48 E9`,
NOP padding, page-protection restore, and instruction-cache flush.

## Schema

`DLLHOOK_UNITY_NOP_PADDING_BOUNDARY` says:

- `hook_tramp.c` owns copied-instruction byte counting.
- `dllhook.c` owns only the active detour envelope it writes at the source
  function entry.
- The entry detour transfers normal control flow before any tail bytes execute.
- NOP-padding from `UsedCount` to `ByteCount` changes the writable code span and
  compatibility surface.
- The old Unity breakage is runtime compatibility evidence, not proof that NOP
  padding is impossible.
- A future NOP-padding patch must first publish a checked `ByteCount` /
  `UsedCount` contract from the trampoline owner and must run a Windows hook
  runtime matrix including Unity.
- This SREV does not change detour bytes, trampoline generation, page
  protection, cache flushing, or hook policy.

## Topology

Current legal path:

```text
SbieApi_HookTramp
  -> copies enough source instructions into trampoline
  -> SbieDll_Hook_x86 writes entry detour envelope
  -> remaining source bytes are not part of normal entry control flow
  -> VirtualProtect restore
  -> FlushInstructionCache(source region)
  -> caller receives trampoline pointer
```

Disabled NOP-padding path:

```text
HookTramp ByteCount
  -> dllhook UsedCount
  -> write NOPs across moved instruction tail
  -> larger executable mutation span
  -> Unity compatibility risk
```

## Logic Risk

The original comment framed the disabled code as a TODO. The real owner issue is
that `ByteCount` is produced by the trampoline builder, while the source detour
writer currently has no active, checked contract saying which tail bytes are
safe to overwrite for every accepted instruction shape and third-party detour
envelope. Enabling NOP padding just to make the source bytes look tidier would
cross from the detour-envelope owner into the trampoline-byte-count owner and
would reintroduce the known Unity compatibility risk without a runtime gate.

## Fix

Comment-only source clarification. The disabled NOP block now states that the
entry jump already owns the normal control-flow transfer and that extending the
write span to HookTramp's `ByteCount` needs a Unity runtime gate.

## Acceptance Gate

`docs/plan/check-srev-246.py` validates the draft-07 schema, official reference
links, source evidence for the disabled NOP block, replacement of the old
symptom-only TODO/breakage wording with the owner/span contract, `hook_tramp.c`
ByteCount owner evidence, SREV-058 cache-coherency adjacency, SREV-091
detour-envelope adjacency, and the ledger fragment.

Runtime gate: not required for this comment-only clarification. Any future
behavior patch that enables NOP padding must run Windows x86/WoW64/x64 hook
smoke tests, third-party detour-envelope compatibility tests, and a Unity game
launch/runtime smoke that proves no regression.
