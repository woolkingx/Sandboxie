# SREV-320: Proc Child Token Compatibility Gates

## Data

`Sandboxie/core/dll/proc.c` owns the DLL-side `Proc_CreateProcessInternalW`
detour. In the non-compartment, non-`OriginalToken` branch, several legacy
image-specific compatibility predicates clear `hToken` before the call proceeds
to the native process creation path.

The relevant data nodes are:

```text
Proc_CreateProcessInternalW hToken
lpApplicationName / lpCommandLine
DeprecatedTokenHacks
DropChildProcessToken
DLL_IMAGE_GOOGLE_CHROME
DLL_IMAGE_MOZILLA_FIREFOX
DLL_IMAGE_ACROBAT_READER
DLL_IMAGE_PLUGIN_CONTAINER
--service-sandbox-type
-sandboxingKind
__sys_CreateProcessInternalW
```

## Official Shape

Microsoft documents `CreateProcessW` as creating a new process and primary
thread for an executable, with no explicit token parameter in the public call
shape. Microsoft documents `CreateProcessAsUserW` as creating a process that
runs in the security context represented by a supplied primary token.

```text
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw
```

Microsoft also documents Windows access tokens as the objects that describe the
security context of a process or thread.

```text
https://learn.microsoft.com/en-us/windows/win32/secauthz/access-tokens
```

`CreateProcessInternalW` is not the public Microsoft API contract. This SREV
therefore does not infer new behavior from undocumented internals; it records
the existing local owner split and keeps the Windows runtime gate visible.

## Schema

Local schema:

```text
docs/plan/srev-320-proc-child-token-compatibility-gates.schema.json
```

`PROC_CHILD_TOKEN_COMPATIBILITY_GATES` says:

- public process creation either uses the caller/default token shape or an
  explicit primary token shape;
- local `hToken` clearing is a process-token selection boundary, not a generic
  browser compatibility switch;
- Edge CDM token clearing must stay under `DeprecatedTokenHacks`,
  `DLL_IMAGE_GOOGLE_CHROME`, and `--service-sandbox-type`;
- Firefox token clearing must stay under `DLL_IMAGE_MOZILLA_FIREFOX` and
  `-sandboxingKind`;
- plugin-container / Acrobat token clearing must stay under the existing
  `DropChildProcessToken` or image-type predicates;
- this SREV changes comments and proof only, not token selection behavior.

## Topology

```text
caller process creation request
  -> Proc_CreateProcessInternalW
  -> existing image/config/command predicates
  -> hToken preserved or cleared
  -> native CreateProcessInternalW path
```

The local compatibility comments live beside the predicate that clears `hToken`;
they do not own token creation semantics outside those exact branches.

## Logic Risk

The old comments named these paths as MSEdge/Firefox/Flash hacks. That wording
hides the real topology: each branch is a narrow child-process token selection
gate. Future edits should not broaden, remove, or merge these predicates without
a Windows runtime matrix proving browser/plugin launch behavior and service
port/DLL loading effects.

## Fix

Comment-only source clarification. The source now names the three branches as
SREV-320 child-token gates and records that the existing predicates are the
scope. No token value, condition, command-line predicate, image predicate,
config setting, or native process-creation call changed.

## Acceptance Gate

`docs/plan/check-srev-320.py` validates the draft-07 schema, official Microsoft
references, the three source comments, preservation of the existing
`DeprecatedTokenHacks` / Edge CDM predicate, preservation of the Firefox
`-sandboxingKind` predicate, preservation of the plugin/Acrobat
`DropChildProcessToken` predicate, removal of stale hack wording from these
branches, and the split ledger fragment.

Windows gate: Edge/Chrome CDM service child launch, Firefox `-sandboxingKind`
child launch, Acrobat/plugin-container child launch, `DeprecatedTokenHacks`
negative smoke, and `DropChildProcessToken` negative smoke.
