---
kind: srev-ledger-entry
id: SREV-164
title: x64 Syscall Count Width
status: patched-source-needs-windows-runtime
owner: Sandboxie/core/drv/util_asm.asm
spec: docs/plan/srev-164-x64-syscall-count-width.md
schema: docs/plan/srev-164-x64-syscall-count-width.schema.json
checker: docs/plan/check-srev-164.py
runtime_gate: "Windows x64 driver build, kernel syscall proxy smoke, win32k syscall proxy smoke, argument-count boundary smoke, and HVCI-enabled guarded indirect-call smoke"
---

### SREV-164: x64 Syscall Count Width

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after Microsoft x64 ABI register-width review; needs Windows x64 driver build/runtime proof |
| Evidence | `Sandboxie/core/drv/util_asm.asm` was the top unnamed reviewable core file after SREV-163. Its x64 `Sbie_InvokeSyscall_asm` implements the C-facing `NTSTATUS Sbie_InvokeSyscall_asm(void* func, ULONG count, void* args);` boundary used by `syscall.c` and `syscall_win32.c`. Before this SREV, the x64 trampoline compared and copied `count` through full 64-bit `rdx`, `r10`, and `rcx` even though `count` is a 32-bit `ULONG`. |
| Data | `Sandboxie/core/drv/util_asm.asm`, `Sandboxie/core/drv/syscall.c`, `Sandboxie/core/drv/syscall_win32.c`, `Sbie_InvokeSyscall_asm`, `ULONG count`, `edx`, `r10d`, `ecx`, `rep movsq`, and `STATUS_INVALID_SYSTEM_SERVICE`. |
| Schema | `X64_SYSCALL_COUNT_WIDTH` says `util_asm.asm` owns the assembly implementation of `Sbie_InvokeSyscall_asm`; the C-facing count parameter is `ULONG count`; on x64, `count` arrives as the low 32 bits of `RDX` and the high 32 bits are not part of the `ULONG` contract; the x64 trampoline must validate, store, compare, and load the count through 32-bit register views `edx`, `r10d`, and `ecx`; the count remains capped at 19 arguments before any stack copy; and register argument layout, stack argument layout, shadow-space placement, nonvolatile register preservation, and x86 trampoline behavior are unchanged. |
| Topology | Legal flow is `Syscall_Invoke` / `Syscall_Invoke32` -> `Sbie_InvokeSyscall_asm(func, ULONG count, args)` -> count validated through `edx <= 19` -> count stored in `r10d` -> stack arguments copied with `ecx` as the `rep movsq` count -> first four arguments loaded into `rcx`, `rdx`, `r8`, and `r9` -> `call func`. |
| Logic Risk | Using full 64-bit register state for a 32-bit ABI parameter can let undefined or stale high bits change the validation path or `rep movsq` count. A legal low 32-bit count could be rejected or a polluted count could copy beyond the intended argument array. |
| Official Shape | `docs/plan/srev-164-x64-syscall-count-width.md` records Microsoft x64 calling convention, parameter passing, and prolog/epilog references. `docs/plan/srev-164-x64-syscall-count-width.schema.json` records the JSON Schema draft-07 local `X64_SYSCALL_COUNT_WIDTH` contract. |
| Fix | `Sbie_InvokeSyscall_asm` now uses `cmp         edx, 13h`, `mov         r10d, edx`, `cmp         r10d, 4`, and `mov         ecx, r10d` / `sub         ecx, 4` for count handling. No x86 trampoline, stack allocation size, register argument order, syscall policy, win32k filtering, token setup, or call target selection changed. |
| Acceptance Gate | `docs/plan/check-srev-164.py` validates the draft-07 schema, official references, C call sites, x64 32-bit count handling, unchanged x86 count handling, ledger entry, and rejection of stale 64-bit count instructions; `docs/plan/check-srev-164.sh` is the matrix wrapper. Runtime/build gate: Windows x64 driver build; normal kernel syscall proxy smoke; win32k syscall proxy smoke; argument-count boundary smoke for counts 0, 4, 5, 19, and over-19; HVCI-enabled smoke for the guarded indirect-call path. |
