---
kind: srev-ledger-entry
id: SREV-173
title: Hook Trampoline Code Capacity
status: patched-source-level-after-official-intel-instruction-shape-and-local-trampoline-buffer-review-needs-windows-hook-runtime-proof
owner: Sandboxie/core/dll/hook_tramp.c
spec: docs/plan/srev-173-hook-tramp-code-capacity.md
schema: docs/plan/srev-173-hook-tramp-code-capacity.schema.json
checker: docs/plan/check-srev-173.py
runtime_gate: "Windows x86/WoW64/x64 hook install smoke plus synthetic expanded-prologue overflow/fail-closed proof"
---

### SREV-173: Hook Trampoline Code Capacity

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official Intel instruction-shape and local trampoline buffer review; needs Windows hook runtime proof |
| Evidence | `Sandboxie/core/dll/hook_inst.c` was the highest-ranked unnamed reviewable core file after SREV-172. `hook_inst.c` analyzes IA-32 / Intel 64 instruction length and relocation shape into `HOOK_INST`; `Sandboxie/core/dll/hook_tramp.c` consumes that shape in `Hook_Tramp_Copy` and emits relocated bytes into `HOOK_TRAMP.code`, which is a 64-byte buffer in `Sandboxie/core/dll/hook.h`. `Hook_Tramp_CountBytes` counts source bytes until the overwritten detour span reaches 5 bytes on x86 or 12 bytes on x64, but `Hook_Tramp_Copy` can expand short/control-transfer/RIP-relative source instructions into 14-byte or 16-byte x64 destination sequences plus a final jump-back stub. Before this SREV, the destination writes were not gated by the bounded `HOOK_TRAMP.code` capacity. |
| Data | `Sandboxie/core/dll/hook_inst.c`, `Sandboxie/core/dll/hook_tramp.c`, `Sandboxie/core/dll/hook.h`, `Sandboxie/core/drv/hook.c`, `HOOK_INST`, `HOOK_TRAMP.code`, `Hook_Analyze`, `Hook_Tramp_CountBytes`, `Hook_Tramp_Copy`, `Hook_Tramp_EmitLength`, `Hook_Tramp_HasCodeSpace`, `Hook_Tramp_JumpBackSize`, `Hook_Api_Tramp`, and `ProbeForWrite`. |
| Schema | `HOOK_TRAMP_CODE_CAPACITY` says `hook_inst.c` owns source instruction analysis only; `hook_tramp.c` owns destination trampoline emission and must bound-check emitted bytes against `HOOK_TRAMP.code`; `Hook_Tramp_EmitLength` names local relocation expansion sizes before writes; `Hook_Tramp_HasCodeSpace` proves current emission and reserved final jump-back bytes fit; `Hook_Tramp_Copy` fails closed when expanded emission would overflow; instruction decoding, source byte counting, relocation semantics, allocation, page protection, and instruction-cache ownership are unchanged. |
| Topology | `Hook_Analyze` produces `HOOK_INST`; `Hook_Tramp_EmitLength` computes destination bytes; `Hook_Tramp_HasCodeSpace` checks the current emission plus final jump-back reserve; relocated bytes are written only after that gate; the final stub gets its own capacity gate before `tramp->size` is published. |
| Logic Risk | The source instruction span and the destination trampoline span are different schemas after relocation. A compact x64 source prologue can require several expanded 14-byte or 16-byte destination sequences. Without a destination-capacity gate, trampoline construction can corrupt adjacent trampoline metadata or memory while returning a usable-looking pointer. |
| Official Shape | `docs/plan/srev-173-hook-tramp-code-capacity.md` records Intel SDM as the instruction-set source and Microsoft `ProbeForWrite` as the user-buffer validation boundary for the driver trampoline API. `docs/plan/srev-173-hook-tramp-code-capacity.schema.json` records the JSON Schema draft-07 local `HOOK_TRAMP_CODE_CAPACITY` contract. |
| Fix | `hook_tramp.c` now adds `Hook_Tramp_HasCodeSpace`, `Hook_Tramp_JumpBackSize`, and `Hook_Tramp_EmitLength`. `Hook_Tramp_Copy` checks the computed destination emission length plus reserved final jump-back space before copying or expanding each instruction, and checks final stub capacity before writing it. |
| Acceptance Gate | `docs/plan/check-srev-173.py` validates the draft-07 schema, official references, source analyzer ownership, trampoline buffer size, driver trampoline buffer probe, named emit-length helper, bounded code-space helper, per-instruction emission gate, final-stub gate, expansion-size constants for local relocation shapes, and ledger fragment; `docs/plan/check-srev-173.sh` is the matrix wrapper. Runtime gate: Windows x86, WoW64, and x64 hook-install smoke plus synthetic expanded-prologue overflow/fail-closed proof. |
