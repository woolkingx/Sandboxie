# SREV-337: Key Mount Hive Device-Map Warmup

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/key.c`, SREV-008, SREV-026, SREV-111, SREV-233, SREV-280, Microsoft object directory, local/global MS-DOS device names, `ObOpenObjectByName`, and registry hive load documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `Key_MountHive3` pre-`ZwLoadKey` DosDevices/device-map warmup |
| Acceptance gate | Targeted checker validates official references, token default-DACL restore topology, `\??\C:` object-open warmup, `ZwLoadKey` ordering, source comment ownership, stale workaround wording removal, and ledger fragment |

## Data

`Key_MountHive3` mounts a sandbox registry hive in the current process context.
The relevant flow is:

- query the sandbox session `TokenDefaultDacl`;
- open the current process token with `TOKEN_QUERY | TOKEN_ADJUST_DEFAULT`;
- temporarily set the token default DACL to `Driver_PublicAcl`;
- initialize an object name for `\??\C:`;
- call `ObOpenObjectByName` for `*IoFileObjectType` and close the handle if it
  opens successfully;
- call `ZwLoadKey(target, source)`;
- restore the original `TokenDefaultDacl`;
- notify SbieSvc with `SVC_MOUNTED_HIVE` only after a successful load.

The old comment described this as a workaround. The stronger contract is that
the object open is a pre-load DosDevices/device-map warmup trigger. The drive
letter is incidental; the comment already recorded that a non-existent volume
works in tests.

## Official Shape

Microsoft documents object directories as object-manager directories, not file
system directories. `\DosDevices` stores MS-DOS device names as symbolic links
to the corresponding device objects.

Microsoft documents local and global MS-DOS device names: there is one global
`\DosDevices` directory and multiple local `\DosDevices` directories; each
thread has a current DosDevices context; object-manager lookup first searches
the local context and then the global context on Windows XP and later.

Microsoft documents `ObOpenObjectByName` as opening an object with full access
validation and auditing. In this source tree it is declared locally and used
with `*IoFileObjectType` to open a file object by object-manager path.

Microsoft documents `RegLoadKey` as loading a registry hive file into a subkey
under `HKEY_USERS` or `HKEY_LOCAL_MACHINE`. Microsoft also documents
`REG_LOAD_KEY_INFORMATION.SourceFile` as the path name of a file that contains
registry hive information when a registry load occurs.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/object-directories`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/local-and-global-ms-dos-device-names`
- `https://learn.microsoft.com/en-us/windows/win32/devnotes/obopenobjectbyname-function`
- `https://learn.microsoft.com/en-us/windows/win32/api/winreg/nf-winreg-regloadkeya`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_reg_load_key_information`

## Boundary

```text
Key_MountHive3 current-process registry-hive mount
  -> temporary TokenDefaultDacl replacement with Driver_PublicAcl
  -> \??\C: file-object open as DosDevices/device-map warmup trigger
  -> close warmup handle if open succeeds
  -> ZwLoadKey(target registry key, source hive file path)
  -> restore original TokenDefaultDacl
```

The registry load owner is `ZwLoadKey` / registry hive load. The object-manager
owner is the `ObOpenObjectByName` path open. The DosDevices/device-map owner is
the current process lookup context. Sandboxie's local owner is only the ordering
and comment contract: warm the current process device-map context before the
registry hive load resolves a source path that may depend on that context.

## Topology

```text
Key_MountHive2
  -> target key missing
  -> non-app-package process
  -> Key_MountHive3
  -> Token_QueryPrimary(TokenDefaultDacl)
  -> ZwOpenProcessTokenEx(TOKEN_QUERY | TOKEN_ADJUST_DEFAULT)
  -> ZwSetInformationToken(TokenDefaultDacl, Driver_PublicAcl)
  -> RtlInitUnicodeString("\\??\\C:")
  -> InitializeObjectAttributes(OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE)
  -> ObOpenObjectByName(*IoFileObjectType, KernelMode, DesiredAccess = 0)
  -> optional ZwClose(warmup handle)
  -> ZwLoadKey(target, source)
  -> ZwSetInformationToken(TokenDefaultDacl, old_token_dacl)
```

## Logic Risk

The stale workaround wording hides the owner and acceptance gate. A future patch
could remove the warmup because `C:` looks arbitrary, replace it with a real
volume dependency, move it after `ZwLoadKey`, or treat it as a registry-load
access-control step. The correct shape is narrower: it is an ordering-sensitive
current-process DosDevices/device-map warmup before `ZwLoadKey`; it is not
required to prove that `C:` exists, and it does not own hive-load policy.

## Fix

Comment-only source clarification. The source now names SREV-337 and states
that the block warms the current process DosDevices/device-map context before
`ZwLoadKey` resolves a hive source path. It also states that the drive letter is
only a trigger and the volume need not exist. No token DACL behavior,
`ObOpenObjectByName` parameters, handle close, `ZwLoadKey` call, mount success
logic, or SbieSvc notification behavior changed.

## Acceptance Gate

`docs/plan/check-srev-337.py` validates the draft-07 schema, official
references, `Key_MountHive3` token default-DACL save/replace/restore topology,
the `\??\C:` warmup object attributes, `ObOpenObjectByName` before `ZwLoadKey`,
warmup handle close, source comment ownership, stale workaround wording
removal, SREV-008 / SREV-026 / SREV-111 / SREV-233 / SREV-280 adjacency, combined ledger
entry, and split ledger fragment.

Runtime gate: Windows hive-load matrix for current-process device-map null vs
initialized states, source paths using DOS drive presentation, missing `C:`
volume or alternate drive-letter trigger, DACL restore after success/failure,
and app-package path using `Key_MountHive4`.
