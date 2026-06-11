# SREV-111 Driver Public Security And Private Handles

## Data

Owner file:

```text
Sandboxie/core/drv/driver.c
```

Reviewed nodes:

```text
Driver_InitPublicSecurity
Driver_PublicAcl
Driver_PublicSd
Driver_LowLabelSd
Driver_FindHomePath
ZwOpenKey
ZwQueryValueKey
ZwCreateFile
ObReferenceObjectByHandle
```

## Schema

`DRIVER_PUBLIC_SECURITY_AND_PRIVATE_HANDLES` defines these local contracts:

- `Driver_InitPublicSecurity` builds absolute security descriptors owned by the driver.
- Each ACL/security-descriptor construction DDI returns `NTSTATUS`; initialization must fail closed when any step fails.
- `Driver_PublicAcl` grants the current compatibility DACL to Authenticated Users and Everyone.
- `Driver_LowLabelSd` keeps the low-integrity SACL and restricted-code DACL path for Vista and later.
- Mandatory Integrity Control stores the integrity label in an object's SACL through a `SYSTEM_MANDATORY_LABEL_ACE`.
- `Driver_FindHomePath` creates only private driver handles while reading the service registry key and opening the installation directory.
- Private registry/file handles are created with `OBJ_KERNEL_HANDLE`.
- `ObReferenceObjectByHandle(..., KernelMode, ...)` is used only on the kernel-private file handle returned by `ZwCreateFile`.

## Topology

Driver load first creates driver-wide reusable security descriptors:

```text
Driver_InitPublicSecurity
  -> Driver_PublicAcl
  -> Driver_PublicSd
  -> Driver_LowLabelSd
```

Those descriptors are later consumed by file, IPC, key, and token paths:

```text
Driver_PublicSd -> ZwCreateFile / ZwCreateDirectoryObject / ZwCreateSymbolicLinkObject
Driver_PublicAcl -> token default DACL replacement
Driver_LowLabelSd -> ZwSetSecurityObject(LABEL_SECURITY_INFORMATION)
```

Home-path discovery is a private driver lookup:

```text
RegistryPath
  -> ZwOpenKey(OBJ_KERNEL_HANDLE)
  -> ZwQueryValueKey(ImagePath)
  -> ZwCreateFile(OBJ_KERNEL_HANDLE, FILE_DIRECTORY_FILE)
  -> ObReferenceObjectByHandle(KernelMode)
  -> Obj_GetName
```

## Logic Risk

The previous source ignored every `NTSTATUS` returned by the ACL and security
descriptor construction DDIs. That made driver initialization proceed with
partially built security descriptors if an ACL buffer, SID, revision, or SACL
operation failed.

`Driver_FindHomePath` also opened private registry and file handles without
`OBJ_KERNEL_HANDLE`. This routine normally runs during driver initialization,
but the official driver contract is sharper: private driver handles should be
kernel handles, and `ObReferenceObjectByHandle(..., KernelMode, ...)` assumes a
kernel-space handle rather than a user-supplied handle.

## Official Shape

- https://learn.microsoft.com/en-us/windows-hardware/drivers/driversecurity/windows-security-model
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/sddl-for-device-objects
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlcreateacl
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtladdaccessallowedaceex
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlcreatesecuritydescriptor
- https://learn.microsoft.com/en-us/windows/win32/devnotes/rtlsetsaclsecuritydescriptor
- https://learn.microsoft.com/en-us/windows/win32/secauthz/mandatory-integrity-control
- https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/object-handles
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopenkey
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwcreatefile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobjectbyhandle

## Fix

`Driver_InitPublicSecurity` now checks the `NTSTATUS` from:

- `RtlCreateAcl`
- `RtlAddAccessAllowedAceEx`
- `RtlAddAce`
- `RtlCreateSecurityDescriptor`
- `RtlSetDaclSecurityDescriptor`
- `RtlSetSaclSecurityDescriptor`

Any failure stops driver initialization through the existing `FALSE` return
path. The compatibility DACL, low-integrity label, SID values, access masks,
and descriptor consumers are unchanged.

`Driver_FindHomePath` now sets `OBJ_KERNEL_HANDLE` for the registry key handle
and installation-directory file handle it opens for private driver use.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-111.py
bash docs/plan/check-srev-111.sh
```

Runtime gate still required:

- Windows driver-load matrix with Driver Verifier enabled.
- Failure injection for ACL/security descriptor allocation and DDI failures.
- `Driver_FindHomePath` registry/file open path under normal boot, service
  restart, and verifier handle checks.
- Low-integrity sandbox path creation and registry low-label application.
- Public descriptor consumers in file, IPC, token default-DACL, and key paths.
