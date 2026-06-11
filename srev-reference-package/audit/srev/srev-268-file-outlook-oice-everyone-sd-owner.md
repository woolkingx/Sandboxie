# SREV-268: File Outlook OICE Everyone SD Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/file.c`, `Sandboxie/core/dll/secure.c`, Microsoft `OBJECT_ATTRIBUTES`, security descriptor, and `RtlSetDaclSecurityDescriptor` documentation |
| Output artifact | `docs/plan/srev-268-file-outlook-oice-everyone-sd-owner.schema.json`, `docs/plan/check-srev-268.py`, `docs/plan/check-srev-268.sh`, ledger fragment, comment-only source clarification |
| Owner | `File_NtCreateFileImpl` Outlook OICE_ compatibility descriptor override |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Evidence

`File_NtCreateFileImpl` has an Outlook 2010 compatibility branch for OICE_ files
used to communicate with embedded previewers running with restricted tokens. The
branch changes the local `OBJECT_ATTRIBUTES.SecurityDescriptor` from the normal
Sandboxie descriptor to `Secure_EveryoneSD`.

Before this SREV, the decision was labeled only as `$Workaround$ - 3rd party
fix`. That label hid the data shape: this is an object-creation security
descriptor override, and its blast radius must stay limited to Outlook image
type plus an OICE_ path segment.

## Official Shape

Microsoft documents `OBJECT_ATTRIBUTES.SecurityDescriptor` as the security
descriptor used when an object is created. If it is `NULL`, default security is
used.

Microsoft documents security descriptors as containing owner/group identity,
DACL, SACL, and control bits. The DACL is the access-rights owner for users and
groups.

Microsoft documents `RtlSetDaclSecurityDescriptor` as setting the DACL in an
absolute security descriptor. It warns that a NULL DACL grants unrestricted
access, while an empty DACL denies access. `Secure_EveryoneSD` is not a NULL
DACL: local `secure.c` builds an explicit DACL with Authenticated Users and
Everyone ACEs, then optionally adds a low mandatory label.

```text
https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_object_attributes
https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptors
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtlsetdaclsecuritydescriptor
```

## Data

`Dll_ImageType`, `DLL_IMAGE_OFFICE_OUTLOOK`, `TruePath`, `\OICE_`,
`objattrs.SecurityDescriptor`, `Secure_EveryoneSD`, `Secure_NormalSD`, and
`Secure_InitSecurityDescriptors`.

## Schema

`FILE_OUTLOOK_OICE_EVERYONE_SD_OWNER` says:

- the branch is a compatibility security-descriptor override for Outlook OICE_
  previewer files;
- the override is legal only when `Dll_ImageType == DLL_IMAGE_OFFICE_OUTLOOK`
  and the true path contains an OICE_ path segment;
- the override must use `Secure_EveryoneSD`, not a NULL DACL or caller-supplied
  descriptor mutation;
- `Secure_EveryoneSD` must remain an explicit local DACL that includes
  Authenticated Users and Everyone, with low-integrity support owned by
  `secure.c`;
- this SREV changes comments and proof only; Outlook/previewer compatibility
  still needs Windows runtime proof.

## Topology

```text
Outlook process
  -> OICE_ true path segment
  -> local OBJECT_ATTRIBUTES.SecurityDescriptor override
  -> Secure_EveryoneSD explicit DACL
  -> created file usable by restricted-token embedded previewer
```

## Logic Risk

The security descriptor is a creation-time object boundary. If the branch is
broadened by path-only matching, image-only matching, or a generic workaround
label, Sandboxie can accidentally create unrelated files with a more public
descriptor. If the branch is removed without a Windows Outlook previewer matrix,
embedded previewers can lose access to the OICE_ exchange file.

## Fix

Comment-only source clarification. The source now names SREV-268 and states
that this is an Outlook OICE_ previewer compatibility descriptor scoped to
Outlook image type and OICE_ path segment. No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-268.py` validates the draft-07 schema, official references,
source comment owner, exact Outlook + OICE_ gate, `Secure_EveryoneSD` assignment,
explicit local DACL construction in `secure.c`, removal of the anonymous
`$Workaround$` label for this branch, and the ledger fragment.

Runtime gate: Windows Outlook 2010/Office previewer test where an embedded
restricted-token previewer can use the OICE_ file, while non-Outlook callers and
non-OICE_ paths do not receive this descriptor override.
