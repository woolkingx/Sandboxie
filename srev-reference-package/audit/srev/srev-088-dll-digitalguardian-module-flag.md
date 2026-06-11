# SREV-088: DLL Digital Guardian Module Flag

## Data

`Sandboxie/core/dll/dll.h` declares global DLL module handles used across the
SbieDll owner boundary. The comment-admitted shape in this file was the
`Dll_DigitalGuardian` declaration:

```text
loaded module presence
HMODULE value
Digital Guardian compatibility flag
loader initialization consumer
file-policy compatibility consumer
```

## Official Shape

Microsoft documents `GetModuleHandleA` as retrieving a module handle for a
specified module that must already be loaded by the calling process.

Microsoft documents that a `GetModuleHandle` return value is not global or
inheritable, and that `GetModuleHandle` does not increment the module reference
count. The returned handle must not be passed to `FreeLibrary`.

Microsoft documents `GetModuleHandleExA` as the alternative when the caller
needs a reference-counted or pinned module-handle shape.

```text
https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandlea
https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandleexa
```

## Schema

Local schema:

```text
docs/plan/srev-088-dll-digitalguardian-module-flag.schema.json
```

The module-flag contract is:

```text
Dll_DigitalGuardian is loaded-module presence evidence, not module ownership
the value is populated from GetModuleHandleA in dllmain.c
the value must not be used as a FreeLibrary-owned reference
DigitalGuardian_Init remains the loader-owned initialization consumer
file.c remains the file-policy compatibility consumer
dll.h documents the shared data role rather than an anonymous workaround
```

## Topology

```text
dllmain.c GetModuleHandleA("DgApi64.dll" / "DgApi.dll")
  -> Dll_DigitalGuardian global module-presence flag
  -> ldr.c DigitalGuardian_Init when module loads
  -> file.c Digital Guardian file-policy compatibility checks
```

`dll.h` owns only the shared declaration surface. It does not own detection
logic, loader initialization, or file-policy decisions.

## Logic Risk

The previous `$Workaround$ - 3rd party fix` comment hid the actual shape of the
shared variable. The official loader API makes the important boundary explicit:
`Dll_DigitalGuardian` is presence evidence for a loaded module in the current
process and is not a reference-counted module owner.

This SREV does not change behavior. It removes the vague workaround label from
the header and records the real data role so future changes do not accidentally
treat this `HMODULE` as a lifetime owner.

## Fix

`dll.h` now describes `Dll_DigitalGuardian` as a Digital Guardian
module-presence compatibility flag.

## Acceptance Gate

`docs/plan/check-srev-088.py` validates the draft-07 schema, official loader
references, `dll.h` declaration wording, `dllmain.c` `GetModuleHandleA`
population, `ldr.c` `DigitalGuardian_Init` consumers, `file.c` policy consumers,
stale `$Workaround$` header wording removal, and ledger entry.

Runtime gate: not required for this comment-only source clarification. The
existing Digital Guardian runtime behavior still depends on Windows testing
from SREV-085.
