---
kind: srev-ledger-entry
id: SREV-337
title: Key Mount Hive Device-Map Warmup
status: patched-comment-topology-after-official-object-manager-devicemap-registry-load-review-no-behavior-change
owner: Sandboxie/core/drv/key.c
spec: docs/plan/srev-337-key-mount-hive-devicemap-warmup.md
schema: docs/plan/srev-337-key-mount-hive-devicemap-warmup.schema.json
checker: docs/plan/check-srev-337.py
runtime_gate: Windows hive-load matrix for device-map state DOS source paths and DACL restore
---

### SREV-337: Key Mount Hive Device-Map Warmup

| Field | Content |
|---|---|
| Severity | [medium] |
| Status | patched comment/topology after official object-manager, DosDevices/device-map, and registry-load review; no behavior change |
| Evidence | `Key_MountHive3` queries the sandbox session `TokenDefaultDacl`, opens the current process token, temporarily sets the default DACL to `Driver_PublicAcl`, initializes `\??\C:`, calls `ObOpenObjectByName` for `*IoFileObjectType`, closes the warmup handle if opened, calls `ZwLoadKey(target, source)`, restores the original default DACL, and notifies SbieSvc only after successful hive load. The old comment described this as a workaround for null current-process devicemap. |
| Data | `Key_MountHive2`, `Key_MountHive3`, `Token_QueryPrimary(TokenDefaultDacl)`, `ZwOpenProcessTokenEx`, `TOKEN_QUERY`, `TOKEN_ADJUST_DEFAULT`, `Driver_PublicAcl`, `ZwSetInformationToken(TokenDefaultDacl)`, `\??\C:`, `OBJ_KERNEL_HANDLE`, `ObOpenObjectByName`, `IoFileObjectType`, `ZwClose`, `ZwLoadKey`, `SVC_MOUNTED_HIVE`, and `ExFreePool(old_token_dacl)`. |
| Schema | `KEY_MOUNT_HIVE_DEVICEMAP_WARMUP` says `Key_MountHive3` owns the pre-`ZwLoadKey` current-process DosDevices/device-map warmup ordering; object directories and DosDevices names belong to the Windows object-manager namespace; local and global DosDevices contexts make drive-letter presentation context-sensitive; `ObOpenObjectByName` opens an object by name with validation and auditing and is used here only as a warmup trigger; the drive letter is incidental and the volume need not exist for the warmup contract; `ZwLoadKey` owns the registry hive load while `Key_MountHive3` owns token default-DACL save/replace/restore ordering; this SREV changes comments and proof only. |
| Topology | `Key_MountHive2 -> target key missing -> non-app-package process -> Key_MountHive3 -> Token_QueryPrimary(TokenDefaultDacl) -> ZwOpenProcessTokenEx(TOKEN_QUERY | TOKEN_ADJUST_DEFAULT) -> ZwSetInformationToken(TokenDefaultDacl, Driver_PublicAcl) -> RtlInitUnicodeString("\\??\\C:") -> InitializeObjectAttributes(OBJ_KERNEL_HANDLE) -> ObOpenObjectByName(*IoFileObjectType, KernelMode) -> optional ZwClose -> ZwLoadKey(target, source) -> ZwSetInformationToken(TokenDefaultDacl, old_token_dacl)`. |
| Logic Risk | Generic workaround wording hides that the block is ordering-sensitive device-map warmup, not hive-load policy. Future work could remove it because `C:` appears arbitrary, require a real volume, move it after `ZwLoadKey`, or confuse it with registry access control. |
| Official Shape | Microsoft documents object directories as object-manager directories and `\DosDevices` as MS-DOS device-name symbolic links; local/global DosDevices contexts make lookup context-sensitive; `ObOpenObjectByName` opens named objects with validation/auditing; `RegLoadKey` and `REG_LOAD_KEY_INFORMATION` document registry hive load and source-file path shape. |
| Fix | Comment-only source clarification. The source now names SREV-337 and states that the block warms the current process DosDevices/device-map context before `ZwLoadKey` resolves a hive source path. It also states that the drive letter is only a trigger and the volume need not exist. No token DACL behavior, `ObOpenObjectByName` parameters, handle close, `ZwLoadKey` call, mount success logic, or SbieSvc notification behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-337.py` validates the draft-07 schema, official references, `Key_MountHive3` token default-DACL save/replace/restore topology, the `\??\C:` warmup object attributes, `ObOpenObjectByName` before `ZwLoadKey`, warmup handle close, source comment ownership, stale workaround wording removal, SREV-008 / SREV-026 / SREV-111 / SREV-233 / SREV-280 adjacency, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-337.sh` is the targeted wrapper. Runtime gate: Windows hive-load matrix for current-process device-map null vs initialized states, source paths using DOS drive presentation, missing `C:` volume or alternate drive-letter trigger, DACL restore after success/failure, and app-package path using `Key_MountHive4`. |
