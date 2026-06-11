# SREV-097: Zw Redirector HAL7600 Skip Contract

## Data

`Sandboxie/core/drv/hook_32.c` and `Sandboxie/core/drv/hook_64.c` own the
driver-side scan that maps a native system-service number back to the
corresponding kernel `ZwXxx` redirector stub. The comment-admitted shape is:

```text
Hook_GetService
  -> Hook_GetZwServiceInternal
  -> Hook_Find_ZwRoutine_1 / Hook_Find_ZwRoutine
  -> scan ntoskrnl Zw redirector bytes
  -> skip known HAL7600 replacement stub for ZwLockProductActivationKeys
  -> continue scanning for the next legal Zw redirector
```

## Official Shape

Microsoft documents Windows native operating system services as routines that
run in kernel mode and have `Nt` or `Zw` entrypoint names. Microsoft documents
that `NtXxx` and `ZwXxx` versions are generally serviced by the same kernel-mode
system routine, while calls from a kernel-mode driver differ in parameter
handling. That gives the local scanner its intended object: a kernel `ZwXxx`
entrypoint stub, not an arbitrary third-party replacement.

Intel documents the Intel 64 and IA-32 instruction-set reference as the
authoritative instruction-format and instruction-reference source. This SREV
uses that source to classify the byte patterns only:

```text
33 C0 C2 08 00 -> xor eax,eax ; ret 8
33 C0 C3       -> xor eax,eax ; ret
66 90          -> xchg ax,ax / two-byte NOP padding
```

Microsoft documents that attempting to write to read-only system memory from a
kernel-mode driver bugchecks, and specifically calls out drivers overwriting
their own code to insert jump instructions as a bugcheck-causing pattern.
Microsoft also documents the general executable-code rule that generated or
modified code needs instruction-cache flushing because the CPU may execute old
cached code. This SREV therefore treats the HAL7600 branch as a read-only
scanner exception, not a permission to modify kernel code.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/using-nt-and-zw-versions-of-the-native-system-services-routines
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/ntxxx-routines
https://www.intel.com/content/www/us/en/content-details/835757/intel-64-and-ia-32-architectures-software-developer-s-manual-combined-volumes-2a-2b-2c-and-2d-instruction-set-reference-a-z.html
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/accessing-read-only-system-memory
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache
```

## Schema

Local schema:

```text
docs/plan/srev-097-zw-redirector-hal7600-skip-contract.schema.json
```

The HAL7600 skip contract is:

```text
Hook_GetZwServiceInternal scans kernel Zw redirector bytes only to locate an existing stub
the HAL7600 branch is a scanner skip over a known replacement stub
the 32-bit HAL7600 pattern is 33 C0 C2 08 00 followed by the original ret 8
the 64-bit HAL7600 pattern is 33 C0 C3 followed by the original 66 90 padding
Sandboxie must not treat the HAL7600 replacement stub as a legal Zw redirector
Sandboxie must not patch kernel code from this scanner branch
ordinary 32-bit Zw redirector parsing and fallback search remain unchanged
ordinary 64-bit Zw redirector parsing remains unchanged
```

## Topology

```text
Hook_GetService
  -> Hook_GetServiceIndex(user-mode DllProc)
  -> Hook_GetNtServiceInternal(service index)
  -> Hook_GetZwServiceInternal(service index)
  -> 32-bit: Hook_Find_ZwRoutine_1, then Hook_Find_ZwRoutine_2 fallback
  -> 64-bit: Hook_Find_ZwRoutine
  -> classify bytes at current scan pointer
  -> if HAL7600 replacement stub, advance to the next original redirector boundary
  -> if legal Zw redirector with target service number, return that stub address
```

## Logic Risk

The old `$Workaround$ - 3rd party fix` marker made a very specific scanner
exception look like generic compatibility glue. Removing it as cleanup would
break machines where the scan lands on the HAL7600 replacement stub. Expanding
it into code mutation would be worse: Microsoft does not define this scanner as
a kernel patching surface, and official driver guidance treats read-only kernel
code writes as bugcheck territory.

The stable shape is narrower: preserve the skip as a byte-pattern classifier
for a known non-Zw redirector stub, then continue scanning to the next original
redirector boundary.

## Fix

Comment-only source clarification. The vague `$Workaround$` inline labels were
replaced with byte-pattern contracts:

```text
32-bit: 33 C0 C2 08 00 (xor eax,eax ; ret 8)
64-bit: 33 C0 C3       (xor eax,eax ; ret)
```

The comments now state this branch is a scanner skip over a third-party
replacement stub, not a legal Zw redirector shape and not code-patching
permission. No runtime behavior was changed.

## Acceptance Gate

`docs/plan/check-srev-097.py` validates the draft-07 schema, official
references, local `Hook_GetService` topology, exact 32-bit and 64-bit HAL7600
byte-pattern predicates, original-boundary search, stale `$Workaround$` removal,
ordinary Zw redirector parsing preservation, and ledger entry.
`docs/plan/check-srev-097.sh` is the matrix wrapper.

Runtime gate: Windows x86/x64 matrix with clean ntoskrnl Zw stubs, HAL7600-style
modified `ZwLockProductActivationKeys` stubs, Driver Verifier import redirection,
and service lookup for both Nt and Zw outputs. This SREV is comment-only, so the
runtime gate is required only before any behavior change to this scanner.
