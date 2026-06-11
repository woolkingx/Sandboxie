# SREV-132: Low ARM64 Entry Syscall ABI Contract

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema |
| Input artifact | `Sandboxie/core/low/entry_arm.asm`, `Sandboxie/core/low/init.c`, `Sandboxie/core/low/lowdata.h`, Microsoft ARM64 / ARM64EC ABI references |
| Output artifact | `docs/plan/srev-132-low-arm64-entry-syscall-abi-contract.schema.json`, `docs/plan/check-srev-132.py`, `docs/plan/check-srev-132.sh`, ledger row |
| Owner | `SystemServiceARM64`, `NtDeviceIoControlFileEC`, and `PrepSyscalls` |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows ARM64 / ARM64EC runtime remains required |

## Evidence

`Sandboxie/core/low/entry_arm.asm` was the highest-ranked unnamed reviewable core file after SREV-131. It is not ordinary application code; it is low-level injected bootstrap and syscall bridge code. The file exports `SystemServiceARM64`, `NtDeviceIoControlFileEC`, `DeviceIoControlSvc`, `EcExitThunkPtr`, `DetourCodeARM64`, and `SbieLowData`.

`SystemServiceARM64` spills incoming `x0-x7` syscall arguments, records the syscall index from `x17`, creates the `API_INVOKE_SYSCALL` parameter block, then calls the local `NtDeviceIoControlFile` pointer stored in `SBIELOW_DATA`. `PrepSyscalls` patches the `ServiceDataPtr` slot immediately before `SystemServiceARM64` with the `SBIELOW_DATA` pointer, and for ARM64EC routes `data->NtDeviceIoControlFile` to `NtDeviceIoControlFileEC`, copies the native `svc` instruction into `DeviceIoControlSvc`, and writes `EcExitThunkPtr`.

Microsoft documents the Windows ARM64 ABI as using `x0-x8` for volatile parameter/result registers, `x9-x15` as volatile scratch, `x16-x17` as volatile intra-procedure scratch, `x19-x28` as non-volatile, and requiring the stack to remain 16-byte aligned. Microsoft documents Arm64EC as an ABI that lets Arm64EC code interoperate with x64 code in the same process. Microsoft's Arm64EC ABI page explains that entry/exit thunks translate between Arm64EC and x64 calling conventions and that call checkers can invoke exit thunks for calls into x64 code.

Official references:

- https://learn.microsoft.com/en-us/cpp/build/arm64-windows-abi-conventions?view=msvc-170
- https://learn.microsoft.com/en-us/windows/arm/arm64ec-abi
- https://learn.microsoft.com/en-us/windows/arm/arm64ec

## Data

`SystemServiceARM64`, `ServiceDataPtr`, `NtDeviceIoControlFileEC`, `DeviceIoControlSvc`, `EcExitThunkPtr`, `MyHandleStubHijack`, `DetourCodeARM64`, `SbieLowData`, `SBIELOW_DATA`, `api_device_handle`, `api_sbiedrv_ctlcode`, `api_invoke_syscall`, `NtDeviceIoControlFile`, `NtDeviceIoControlFile_code`, `RealNtDeviceIoControlFile`, `syscall_data`, `x0-x17`, `sp`, `fp`, `lr`, and `API_NUM_ARGS`.

## Schema

`LOW_ARM64_ENTRY_SYSCALL_ABI_CONTRACT` says:

- `SystemServiceARM64` is an ARM64 syscall bridge that follows the Windows ARM64 volatile register and 16-byte stack-alignment contract.
- `SystemServiceARM64` spills original `x0-x7` syscall arguments before repurposing `x0-x7` for `NtDeviceIoControlFile`.
- `SystemServiceARM64` records the syscall index from `x17` and the original argument-stack pointer in `API_NUM_ARGS` slots.
- `SystemServiceARM64` builds the `NtDeviceIoControlFile` call with `x0-x7` plus two stack arguments and returns the call status in `x0`.
- `PrepSyscalls` patches the `ServiceDataPtr` slot immediately before `SystemServiceARM64` with the `SBIELOW_DATA` pointer.
- ARM64EC `PrepSyscalls` routes `data->NtDeviceIoControlFile` to `NtDeviceIoControlFileEC` and copies the native `svc` instruction into `DeviceIoControlSvc`.
- `NtDeviceIoControlFileEC` preserves the local handle-stub sentinel and branches through `MyHandleStubHijack` only when the emulator changes the sentinel.
- `EcExitThunkPtr` is sourced from the ARM64EC syscall extra-data trailer and used only by `MyHandleStubHijack`.
- This SREV is a source-level ABI classification and does not change syscall detour bytes or ARM64EC thunk policy.

## Topology

The ARM64 syscall bridge topology is:

```text
patched Zw* export
  -> SystemServiceARM64
  -> spill original x0-x7
  -> x17 syscall index + original argument stack pointer
  -> API_INVOKE_SYSCALL parameter block
  -> SBIELOW_DATA.NtDeviceIoControlFile
  -> SbieDrv API_SBIEDRV_CTLCODE
  -> return NTSTATUS in x0
```

The ARM64EC wrapper topology is:

```text
PrepSyscalls sees is_arm64ec
  -> data->NtDeviceIoControlFile = NtDeviceIoControlFileEC
  -> DeviceIoControlSvc gets native svc instruction
  -> EcExitThunkPtr gets extra-data trailer thunk pointer
  -> NtDeviceIoControlFileEC svc path
  -> optional MyHandleStubHijack emulator exit path
```

## Logic Risk

This file is high-risk because a tiny register, stack, or thunk routing change can break every ARM64 / ARM64EC syscall hook. However, source review did not expose a local one-line defect comparable to the previous SREV patches. The right move is therefore to name the ABI contract explicitly and keep it source-gated, instead of changing assembly bytes without runtime evidence.

The source-level invariants to preserve are the 16-byte stack alignment, volatile/non-volatile register boundary, `x17` syscall-index handoff, `SBIELOW_DATA` offset contract, and ARM64EC exit-thunk routing. Any future optimization must prove those edges against Windows ARM64 / ARM64EC runtime, not by analogy from x64 or x86 stubs.

## Fix

No source behavior changed. This SREV records `entry_arm.asm` as reviewed and classifies its legal ABI / topology shape for future changes.

## Acceptance Gate

`docs/plan/check-srev-132.py` validates the draft-07 schema, official references, ARM64 exported labels, `SystemServiceARM64` spill/parameter-block/call topology, `NtDeviceIoControlFileEC` sentinel and `MyHandleStubHijack` topology, `PrepSyscalls` ARM64EC patch edges, `SBIELOW_DATA` offset evidence, and ledger entry. `docs/plan/check-srev-132.sh` is the matrix wrapper.

Runtime/build gate: Windows ARM64 lowlevel build, ARM64 sandbox process startup proving `SystemServiceARM64` stack and status behavior, ARM64EC process startup proving `NtDeviceIoControlFileEC` and `EcExitThunkPtr` routing, syscall hook smoke proving original `x0-x7` arguments reach `API_INVOKE_SYSCALL`, and a disabled-hook smoke proving no ARM64EC wrapper state is used when `is_arm64ec` is false.
