# SREV-317: Ldr Third-Party Module Callback Group

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/ldr.c`, adjacent vendor-specific SREVs, and Microsoft loader module-handle/reference documentation |
| Output artifact | non-Microsoft loader callback group contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Ldr_Dlls` table group in `Sandboxie/core/dll/ldr.c` |
| Acceptance gate | Targeted checker validates official references, loader table entries, ARM64 guard, architecture-specific Digital Guardian entries, adjacent vendor SREVs, stale generic workaround wording removal, combined ledger, and ledger fragment |

## Data

`Ldr_Dlls` maps loaded DLL base names to Sandboxie init callbacks. The
non-Microsoft group currently contains:

- `acscmonitor.dll -> Acscmonitor_Init`
- `IDMIECC.dll -> Custom_InternetDownloadManager`
- `snxhk.dll -> Custom_Avast_SnxHk`
- `snxhk64.dll -> Custom_Avast_SnxHk`
- `sysfer.dll -> Custom_SYSFER_DLL`
- `dgapi64.dll -> DigitalGuardian_Init` on 64-bit builds
- `dgapi.dll -> DigitalGuardian_Init` on 32-bit builds

Several entries already have owner-specific SREVs. SREV-259 owns the
ActivClient `acscmonitor.dll` loader-reference lifetime. SREV-257 owns the
Avast/SnxHk generated trampoline publication gate. SREV-055 and SREV-258 own
the SYSFER bounded entry-point patch and comment owner. SREV-088 and SREV-249
own the Digital Guardian module-presence flag and comment topology.

Adjacent owner contracts:

- SREV-259: `CUSTOM_ACSCMONITOR_LOADER_REFERENCE`
- SREV-257: `CUSTOM_AVAST_TRAMPOLINE_PUBLISH_GATE`
- SREV-055: `CUSTOM_SYSFER_ENTRYPOINT_PATCH`
- SREV-258: `CUSTOM_SYSFER_COMMENT_OWNER`
- SREV-088: `DLL_DIGITALGUARDIAN_MODULE_FLAG`
- SREV-249: `DIGITALGUARDIAN_COMMENT_TOPOLOGY`

This SREV owns only the loader table group label and the fact that these are
non-Microsoft module callback registrations. It does not own the vendor-specific
behavior behind the callbacks.

Source gate phrase: loaded module base-name to init-callback registration.
Source gate phrase: non-Microsoft module callback registration group.

## Official Shape

Microsoft documents `LoadLibraryW` as loading a module into the address space of
the calling process and returning a module handle on success. It also documents
that module handles are per-process and not global or inheritable, and that the
system maintains a per-process reference count for loaded modules.

Microsoft documents `GetModuleHandleW` as retrieving a handle for a module that
has already been loaded by the calling process. The returned handle does not
increment the module reference count and must not be treated as a `FreeLibrary`
owned reference.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-loadlibraryw`
- `https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getmodulehandlew`

## Schema

Local schema:

```text
docs/plan/srev-317-ldr-third-party-module-callback-group.schema.json
```

Contract id:

```text
LDR_THIRD_PARTY_MODULE_CALLBACK_GROUP
```

## Topology

```text
Windows loader observes a loaded module
  -> Ldr_Dlls base-name match
  -> owner-specific init callback
  -> vendor-specific compatibility owner
```

Group topology:

```text
non-Microsoft module callback group
  -> ARM64 excludes acscmonitor / IDMIECC / snxhk / sysfer callbacks
  -> architecture-specific Digital Guardian callback remains dgapi64/dgapi
  -> callback body owns behavior, not the group header
```

## Logic Risk

The old `$Workaround$ - 3rd party fix` header made the block look like an
unowned compatibility dumping ground. That is dangerous because the entries do
not share one behavior. Some entries pin loader references, some publish
generated executable trampolines, some patch a loaded image entry point, and
some update a module-presence flag. A future edit should follow the
entry-specific owner SREV instead of treating the whole group as one policy.

## Fix

The `ldr.c` group header now names the block as the SREV-317 non-Microsoft
module callback registration group. No DLL name, callback function, ARM64
guard, architecture-specific Digital Guardian selection, callback body, or
return value changed.

## Acceptance Gate

`docs/plan/check-srev-317.py` validates the draft-07 schema, official
references, loader group label, exact DLL-to-callback registrations, ARM64
guard, Digital Guardian architecture split, adjacent SREV owner references,
stale generic workaround wording removal, combined ledger entry, and split
ledger fragment.

Runtime gate: no runtime gate is required for this comment-only group-label
clarification. Any future behavior change must run the owner-specific runtime
gate for the affected callback, such as the ActivClient, Avast/SnxHk, SYSFER, or
Digital Guardian gates named by the adjacent SREVs.
