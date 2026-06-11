# SREV-260: DLL Hook Unity Runtime Gate Wording

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/dllhook.c`, SREV-246 |
| Output artifact | `docs/plan/srev-260-dllhook-unity-runtime-gate-wording.schema.json`, `docs/plan/check-srev-260.py`, `docs/plan/check-srev-260.sh`, ledger fragment, comment-only source clarification |
| Owner | `SbieDll_Hook_x86` disabled NOP-padding comment |
| Acceptance gate | targeted source checker plus SREV-246 adjacency checker, core coverage, and diff checkpoint |

## Evidence

SREV-246 already classified the disabled NOP-padding block as a detour span and
trampoline byte-count owner boundary. The remaining source wording still used a
historical symptom phrase about Unity breakage. This SREV removes the symptom
wording and names the gate directly.

## Data

`SbieDll_Hook_x86`, disabled NOP padding, `HookTramp` `ByteCount`, detour write
span, and Unity runtime gate.

## Schema

`DLLHOOK_UNITY_RUNTIME_GATE_WORDING` says:

- SREV-246 owns the disabled NOP-padding boundary;
- the source comment must name the Unity runtime gate rather than symptom-only
  breakage wording;
- this SREV does not change hook bytes, NOP-padding state, page protection,
  instruction-cache flushing, trampoline generation, or runtime policy.

## Topology

```text
SbieApi_HookTramp ByteCount
  -> disabled NOP-padding span
  -> future behavior requires Unity runtime gate
```

## Logic Risk

Historical breakage wording can be mistaken for folklore. The actionable rule is
the runtime gate: do not enable NOP padding until the hook matrix and Unity
runtime proof exist.

## Fix

Comment-only source clarification. The source now says the write span needs a
Unity runtime gate. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-260.py` validates the draft-07 schema, source comment,
removal of the symptom-only breakage wording, preservation of the disabled NOP
block, SREV-246 adjacency, and the ledger fragment.

Runtime gate: inherited from SREV-246 for any future behavior patch.
