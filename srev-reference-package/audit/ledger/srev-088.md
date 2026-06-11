---
kind: srev-ledger-entry
id: SREV-088
title: DLL Digital Guardian Module Flag
status: source-level-classified-after-official-getmodulehandlea-getmodulehandleexa-modul
owner: Sandboxie/core/dll/dll.h
spec: docs/plan/srev-088-dll-digitalguardian-module-flag.md
schema: docs/plan/srev-088-dll-digitalguardian-module-flag.schema.json
checker: docs/plan/check-srev-088.py
runtime_gate: not required for this comment-only source clarification; existing Digital Guardian runtime behavior still depends on Windows testing from SREV-085
---
### SREV-088: DLL Digital Guardian Module Flag

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | source-level classified after official `GetModuleHandleA` / `GetModuleHandleExA` module-handle shape; comment-only source clarification, no new runtime behavior |
| Evidence | `Sandboxie/core/dll/dll.h` declared `Dll_DigitalGuardian` under a vague `$Workaround$ - 3rd party fix` comment. `Sandboxie/core/dll/dllmain.c` populates the value with `GetModuleHandleA("DgApi64.dll")` / `GetModuleHandleA("DgApi.dll")`; `Sandboxie/core/dll/ldr.c` wires `DigitalGuardian_Init`; `Sandboxie/core/dll/file.c` consumes the flag for Digital Guardian file-policy compatibility. Microsoft documents `GetModuleHandleA` as returning a handle to a module already loaded in the calling process without incrementing the module reference count, and documents `GetModuleHandleExA` as the shape for reference-counted or pinned handles. |
| Data | Loaded module presence, non-owning `HMODULE`, Digital Guardian compatibility flag, loader initialization consumer, and file-policy compatibility consumer. |
| Schema | `DLL_DIGITALGUARDIAN_MODULE_FLAG` says `Dll_DigitalGuardian` is loaded-module presence evidence rather than module ownership; the value is populated from `GetModuleHandleA` in `dllmain.c`; it must not be used as a `FreeLibrary`-owned reference; `DigitalGuardian_Init` remains the loader-owned initialization consumer; `file.c` remains the file-policy compatibility consumer; `dll.h` documents the shared data role rather than an anonymous workaround. |
| Topology | `dllmain.c` detects loaded Digital Guardian modules with `GetModuleHandleA`, stores the result in the shared `Dll_DigitalGuardian` declaration, `ldr.c` initializes the compatibility surface when the module is loaded, and `file.c` reads the flag at file-policy decision points. |
| Logic Risk | A vague workaround label hides the owner/lifetime shape of the shared variable. Since `GetModuleHandleA` does not increment the reference count, future code must treat this handle as presence evidence only and must not free or otherwise own the module lifetime. |
| Official Shape | `docs/plan/srev-088-dll-digitalguardian-module-flag.md` records Microsoft `GetModuleHandleA` and `GetModuleHandleExA` references. `docs/plan/srev-088-dll-digitalguardian-module-flag.schema.json` records the JSON Schema draft-07 local `DLL_DIGITALGUARDIAN_MODULE_FLAG` contract. |
| Fix | `dll.h` now labels `Dll_DigitalGuardian` as a Digital Guardian module-presence compatibility flag. |
| Acceptance Gate | `docs/plan/check-srev-088.py` validates the draft-07 schema, official loader references, `dll.h` declaration wording, `dllmain.c` `GetModuleHandleA` population, `ldr.c` `DigitalGuardian_Init` consumers, `file.c` policy consumers, stale `$Workaround$` header wording removal, and ledger entry; `docs/plan/check-srev-088.sh` is the matrix wrapper. Runtime gate: not required for this comment-only source clarification; existing Digital Guardian runtime behavior still depends on Windows testing from SREV-085. |
