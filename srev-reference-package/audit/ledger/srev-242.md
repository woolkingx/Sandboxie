---
kind: srev-ledger-entry
id: SREV-242
title: DLL Utility Assembly Dispatcher Topology
status: docs-only-source-topology-reviewed-needs-windows-dll-build-proof
owner: Sandboxie/core/dll/util_asm.asm
additional_owners:
  - Sandboxie/core/dll/util_32.asm
  - Sandboxie/core/dll/util_64.asm
  - Sandboxie/core/dll/util_arm.asm
  - Sandboxie/core/dll/util_EC.asm
  - Sandboxie/core/dll/SboxDll.vcxproj
  - Sandboxie/core/dll/SboxDll.vcxproj.filters
  - docs/plan/ledger/srev-095.md
  - docs/plan/ledger/srev-177.md
  - docs/plan/ledger/srev-164.md
spec: docs/plan/srev-242-util-asm-dispatcher-topology.md
schema: docs/plan/srev-242-util-asm-dispatcher-topology.schema.json
checker: docs/plan/check-srev-242.py
runtime_gate: Windows DLL builds for Win32, x64, ARM64EC, and ARM64 must continue to select the intended assembly owner. Runtime behavior remains covered by concrete owner SREV Windows gates.
---

### SREV-242: DLL Utility Assembly Dispatcher Topology

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | docs-only source topology reviewed; needs Windows DLL build proof |
| Evidence | `Sandboxie/core/dll/util_asm.asm` was the top unnamed reviewable core file after SREV-241. Source readback shows it is not the implementation owner for a single ABI routine. It is a MASM dispatcher: non-`_WIN64` builds enable `.386p` / `.model flat` and include `util_32.asm`; `_WIN64` builds include `util_64.asm`; the file ends after include selection and contains no direct helper body. `SboxDll.vcxproj` builds this dispatcher through `ml` for Win32 and through `ml64 -D_WIN64` for x64 and ARM64EC. ARM64 is explicitly excluded and uses `util_arm.asm`; ARM64EC also has a dedicated `util_EC.asm` item. `util_32.asm` and `util_64.asm` are listed as `None` items and excluded from direct build, so their legal compile route is through `util_asm.asm`. |
| Data | `util_asm.asm`, `util_32.asm`, `util_64.asm`, `util_arm.asm`, `util_EC.asm`, `SboxDll.vcxproj`, `SboxDll.vcxproj.filters`, `_WIN64`, `_M_ARM64EC`, `.386p`, `.model flat`, `ml`, `ml64`, `-D_WIN64`, `-D_M_ARM64EC`, `ApiInstrumentationAsm`, `InstrumentationCallbackAsm`, `ProtectCall2`, `ProtectCall4`, `RpcRt_NdrAsyncClientCall`, `RpcRt_Ndr64AsyncClientCall`, SREV-095, SREV-177, and SREV-164. |
| Schema | `DLL_UTIL_ASM_DISPATCHER_TOPOLOGY_CONTRACT` says `util_asm.asm` is the DLL utility assembly dispatcher for MASM include selection; `util_32.asm` owns the 32-bit implementation body reached when `_WIN64` is not defined; `util_64.asm` owns the x64 and ARM64EC MASM body reached when `_WIN64` is defined; native ARM64 runtime assembly is not owned by this dispatcher and is owned by `util_arm.asm`; `SboxDll.vcxproj` owns active platform build selection; `util_32.asm` and `util_64.asm` are included source bodies, not direct project build items; and behavior or ABI changes must target the included implementation owner and concrete architecture SREV, not the dispatcher. |
| Topology | `SboxDll.vcxproj CustomBuild util_asm.asm -> Win32 ml without _WIN64 -> util_asm.asm -> include util_32.asm -> x86 DLL helper bodies`; `SboxDll.vcxproj CustomBuild util_asm.asm -> x64 ml64 -D_WIN64 -> util_asm.asm -> include util_64.asm -> x64 DLL helper bodies`; `SboxDll.vcxproj CustomBuild util_asm.asm -> ARM64EC ml64 -D_WIN64 -D_M_ARM64EC -> util_asm.asm -> include util_64.asm -> ARM64EC-gated util_64.asm sections`; `SboxDll.vcxproj native ARM64 -> util_asm.asm excluded -> util_arm.asm built with armasm64`. |
| Logic Risk | The high coverage score comes from the dispatcher naming architecture-sensitive assembly includes. Treating `util_asm.asm` as a concrete ABI owner would hide the owner split between Win32, x64, ARM64EC, and native ARM64 assembly files. It would also risk applying a fix intended for the DLL dispatcher to the separate driver assembly file already covered by SREV-164. |
| Official Shape | No new Windows/API runtime behavior is defined by this dispatcher. The official calling-convention and architecture ABI references for concrete implementation paths remain with their owner SREVs, especially SREV-095 and SREV-177. This SREV uses the local MSBuild/MASM topology to classify dispatch ownership only. |
| Fix | No source patch. This SREV records `util_asm.asm` as a DLL MASM include dispatcher and closes it as docs-only coverage. Future behavior patches should target `util_32.asm`, `util_64.asm`, `util_arm.asm`, `util_EC.asm`, or the concrete caller/trace/RPC owner that executes the ABI crossing. |
| Acceptance Gate | `docs/plan/check-srev-242.py` validates the draft-07 schema, dispatcher source shape, project build/exclusion topology, filters entry, included implementation file topology, existing architecture SREV separation, split ledger fragment, and absence of direct runtime helper bodies in the dispatcher; `docs/plan/check-srev-242.sh` is the targeted wrapper. Runtime/build gate: Windows DLL builds for Win32, x64, ARM64EC, and ARM64 must continue to select the intended assembly owner. Runtime behavior remains covered by concrete owner SREV Windows gates. |
