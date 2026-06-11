# SREV-091: Hook Trampoline PUSH/RET Stub Preservation

## Data

`Sandboxie/core/dll/hook_tramp.c` owns low-level trampoline construction and
detour-byte emission for both user-mode and kernel-mode builds. The
comment-admitted shape is:

```text
source executable address
writable alias address
third-party 32-bit PUSH imm32 / RET detour envelope
replacement jump target
normal 32-bit relative E9 JMP detour
64-bit mov-rax / jmp-rax detour
kernel write-protect boundary
instruction-cache coherency boundary owned by the caller path
```

## Official Shape

Intel's official Intel 64 and IA-32 Software Developer's Manuals are the primary
instruction-set source for IA-32 and Intel 64 instruction encodings and
control-transfer semantics, including `PUSH`, `RET`, and `JMP`.

Microsoft documents `VirtualProtect` as changing protection on committed pages
and says executable code changes require instruction-cache coherency through
`FlushInstructionCache`. Microsoft documents `FlushInstructionCache` as the API
applications should call after generating or modifying code in memory.

Microsoft documents `FreeLibrary` as decrementing a per-process module reference
count and unloading the module when that count reaches zero. Microsoft documents
`ZwUnloadDriver` as dynamically unloading a driver, with strong caution around
driver unload and filter-driver retail usage.

There is no Microsoft public contract for a third-party SSDT hooker's private
unload implementation. The local legal shape is therefore not "all detours can
be normalized to E9 JMP"; it is "if the existing code is already a `PUSH imm32`;
`RET` envelope owned by another hooker, preserve that envelope and replace only
the immediate operand."

```text
https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html
https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualprotect
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache
https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-freelibrary
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwunloaddriver
```

## Schema

Local schema:

```text
docs/plan/srev-091-hook-tramp-push-ret-stub-preservation.schema.json
```

The detour-envelope contract is:

```text
the existing 32-bit PUSH imm32 / RET envelope is a third-party-owned detour shape
Sandboxie may replace only the PUSH immediate operand in that envelope
Sandboxie must not rewrite that envelope into a relative E9 JMP
ordinary 32-bit non-PUSH/RET hooks still use the existing E9 relative JMP path
64-bit hooks keep the mov-rax / jmp-rax path
code mutation and instruction-cache coherency remain owned by caller hook-install paths such as SREV-058
```

## Topology

```text
Hook_BuildJump
  -> writable alias of executable bytes
  -> existing instruction-shape classifier
  -> if 32-bit PUSH imm32 / RET: operand-only replacement
  -> else 32-bit: relative E9 JMP replacement
  -> 64-bit: mov rax target; jmp rax replacement
  -> caller-owned page-protection/cache coherency gate
```

The branch is not choosing a prettier instruction. It is preserving a
third-party-owned unload contract by keeping the opcode envelope visible to that
owner's later cleanup path.

## Logic Risk

The old source comment described the symptom but not the data shape. The actual
risk is owner mismatch: a third-party hook owns a `PUSH imm32`; `RET` envelope
and later expects to restore only the immediate operand. If Sandboxie normalizes
that envelope to a relative `E9` jump, the third-party unload code no longer sees
the instruction shape it owns.

The current code already preserves the correct local shape by writing only
`SourceAddr[1..4]` when it detects `0x68 ... 0xC3`. No behavior patch is made in
this SREV; the source comment is rewritten from symptom language into the
schema/topology contract, and the gate records why this special case must not be
"simplified."

## Fix

Comment-only source clarification: the Rising Antivirus branch now states that
the existing `PUSH`/`RET` instruction envelope is preserved because the
third-party unload path owns that shape and restores only the immediate operand.

## Acceptance Gate

`docs/plan/check-srev-091.py` validates the draft-07 schema, official Intel and
Microsoft references, source evidence for the `PUSH imm32`; `RET` classifier,
operand-only replacement, ordinary 32-bit E9 fallback, 64-bit mov-rax/jmp-rax
path, stale symptom-only comment removal, SREV-058 instruction-cache ownership,
and ledger entry.

Runtime gate: not required for this comment-only clarification. Any future
behavior change to this branch needs an x86 kernel/runtime matrix with a
PUSH/RET-owning third-party detour and unload path, plus the existing
instruction-cache gates.
