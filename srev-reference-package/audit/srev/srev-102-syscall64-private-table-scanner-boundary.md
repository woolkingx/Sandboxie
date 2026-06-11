# SREV-102: Syscall64 Private Table Scanner Boundary

## Data

`Sandboxie/core/drv/syscall_64.c` owns the 64-bit syscall service-table
discovery path. The uncovered comment hits were both in private scanner code:

```text
disabled x64 master/shadow table spacing check
ARM64 KeServiceDescriptorTableFilter lookup placeholder
```

The x64 scanner first tries `MmGetSystemRoutineAddress("KeServiceDescriptorTable")`.
If that export is unavailable, it derives table candidates by scanning
`KeAddSystemServiceTable` instruction patterns. The service-table path later
validates `ShadowTable->Addrs` against `MasterTable->Addrs`.

The ARM64 master-table path already has a local `ADRP` / `ADD` pattern scanner.
The ARM64 filter-table branch currently returns `0`; `Syscall_GetServiceTableFilter`
then logs `FILTER TABLE` and fails closed.

## Official Shape

Microsoft documents KVA Shadow as the Windows kernel mitigation for the rogue
data cache load vulnerability, CVE-2017-5754, also known as Meltdown or Variant
3. Microsoft describes this mitigation as changing user/kernel address-space
transition handling, including trap handling and system service call dispatch.
The same MSRC post explicitly warns that KVA Shadow implementation details are
subject to change and that drivers and applications must not depend on those
internals without updated documentation.

Microsoft support guidance for speculative-execution side-channel
vulnerabilities identifies CVE-2017-5754 as Rogue Data Cache Load. Intel's
official advisory for Rogue Data Cache Load / Intel-SA-00088 records the
processor-side vulnerability class and the mitigation direction.

Microsoft documents the Windows ARM64 ABI and documents building ARM64 drivers
with the WDK. These documents prove ARM64 is a supported Windows driver target,
but they do not define a public `KeServiceDescriptorTableFilter` scanner shape.

```text
https://www.microsoft.com/en-us/msrc/blog/2018/03/kva-shadow-mitigating-meltdown-on-windows
https://support.microsoft.com/en-us/topic/kb4072698-windows-server-and-azure-stack-hci-guidance-to-protect-against-silicon-based-microarchitectural-and-speculative-execution-side-channel-vulnerabilities-2f965763-00e2-8f98-b632-0d96f30c8c8e
https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/advisory-guidance/rogue-data-cache-load.html
https://learn.microsoft.com/en-us/cpp/build/arm64-windows-abi-conventions?view=msvc-170
https://learn.microsoft.com/en-us/windows-hardware/drivers/develop/building-arm64-drivers
```

## Schema

Local schema:

```text
docs/plan/srev-102-syscall64-private-table-scanner-boundary.schema.json
```

The syscall64 private table scanner contract is:

```text
Syscall_GetMasterServiceTable uses exported KeServiceDescriptorTable when available before private pattern scanning
the disabled x64 0x40 / 0xC0 spacing check is a historical private invariant and must not be re-enabled from source comments alone
KVA Shadow / KB4056892 changed x64 kernel-entry and system-service dispatch internals for Meltdown mitigation
Microsoft says KVA Shadow implementation details are subject to change and drivers must not depend on those internals without updated documentation
Syscall_GetServiceTable still validates ShadowTable->Addrs against MasterTable->Addrs after deriving the candidate table
ARM64 MasterTable lookup uses an ADRP / ADD pattern in KeAddSystemServiceTable
ARM64 FilterTable lookup remains fail-closed until a version-gated KeAddSystemServiceTable pattern is proven
this SREV does not change service table offsets, pattern scanner behavior, or syscall dispatch
```

## Topology

x64 master/shadow table path:

```text
MmGetSystemRoutineAddress("KeServiceDescriptorTable")
  -> use export if present
  -> else scan KeAddSystemServiceTable
  -> derive MasterTable candidate
  -> derive ShadowTable candidate by OS-build offsets
  -> require ShadowTable->Addrs == MasterTable->Addrs
```

ARM64 paths:

```text
Syscall_GetMasterServiceTable
  -> scan KeAddSystemServiceTable for ADRP / ADD
  -> derive MasterTable

Syscall_GetMasterServiceTableFilter
  -> ARM64 branch intentionally returns 0 today
  -> Syscall_GetServiceTableFilter logs FILTER TABLE and fails closed
```

## Logic Risk

The old Meltdown comment said the code block was "broken", but the disabled
block is an old spacing assertion over private kernel layout. The official
KVA Shadow documentation says those kernel-entry and system-service internals
changed and are not a stable driver dependency. The right contract is therefore
"private invariant disabled", not "repair the check".

The ARM64 `TODO` was also too vague. Treating it as an obvious implementation
task would invite x64 pattern assumptions into ARM64 without a Windows ARM64
runtime matrix. The current behavior is fail-closed, which is the correct source
boundary until a version-gated `KeAddSystemServiceTable` pattern is proven.

## Fix

Comment-only source clarification:

```text
The disabled x64 spacing check now states that KVA Shadow / KB4056892 changed kernel-entry layout enough that the private invariant is not legal.
The ARM64 filter-table placeholder now states that the lookup remains fail-closed until a version-gated pattern is proven on real Windows ARM64 builds.
```

No service table offsets, pattern scanner predicates, table validation, filter
table fail-closed behavior, or syscall dispatch behavior changed.

## Acceptance Gate

`docs/plan/check-srev-102.py` validates the draft-07 schema, official
references, export-first table lookup, disabled spacing-check shape,
post-derivation `ShadowTable->Addrs` validation, ARM64 master-table `ADRP` /
`ADD` pattern, ARM64 filter-table fail-closed wording, stale `broken` and `TODO`
wording removal from `syscall_64.c`, and ledger entry.
`docs/plan/check-srev-102.sh` is the matrix wrapper.

Runtime gate: Windows x64/ARM64 matrix with Windows 7 x64 pre/post KB4056892,
Windows 10/11 x64 with KVA Shadow on/off where applicable, Windows ARM64
supported WDK builds, service table discovery, filter table discovery,
Driver Verifier, HVCI on/off, and syscall dispatch smoke for ordinary NT and
win32k syscall entries.
