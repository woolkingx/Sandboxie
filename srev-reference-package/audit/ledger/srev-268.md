---
kind: srev-ledger-entry
id: SREV-268
title: File Outlook OICE Everyone SD Owner
status: patched-comment-topology-after-official-security-descriptor-review-no-behavior-change
owner: Sandboxie/core/dll/file.c
spec: docs/plan/srev-268-file-outlook-oice-everyone-sd-owner.md
schema: docs/plan/srev-268-file-outlook-oice-everyone-sd-owner.schema.json
checker: docs/plan/check-srev-268.py
runtime_gate: Windows Outlook 2010/Office previewer OICE_ restricted-token compatibility and non-Outlook/non-OICE_ negative proof
---

### SREV-268: File Outlook OICE Everyone SD Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after official security descriptor review; no behavior change |
| Evidence | `File_NtCreateFileImpl` has an Outlook 2010 compatibility branch for OICE_ files used to communicate with embedded previewers running with restricted tokens. The branch changes the local `OBJECT_ATTRIBUTES.SecurityDescriptor` from the normal Sandboxie descriptor to `Secure_EveryoneSD`. Before this SREV, the decision was labeled only as `$Workaround$ - 3rd party fix`. |
| Data | `Dll_ImageType`, `DLL_IMAGE_OFFICE_OUTLOOK`, `TruePath`, `\OICE_`, `objattrs.SecurityDescriptor`, `Secure_EveryoneSD`, `Secure_NormalSD`, and `Secure_InitSecurityDescriptors`. |
| Schema | `FILE_OUTLOOK_OICE_EVERYONE_SD_OWNER` says the branch is a compatibility security-descriptor override for Outlook OICE_ previewer files; the override is legal only when `Dll_ImageType == DLL_IMAGE_OFFICE_OUTLOOK` and the true path contains an OICE_ path segment; the override must use `Secure_EveryoneSD`, not a NULL DACL or caller-supplied descriptor mutation; `Secure_EveryoneSD` must remain an explicit local DACL that includes Authenticated Users and Everyone, with low-integrity support owned by `secure.c`; this SREV changes comments and proof only. |
| Topology | `Outlook process -> OICE_ true path segment -> local OBJECT_ATTRIBUTES.SecurityDescriptor override -> Secure_EveryoneSD explicit DACL -> created file usable by restricted-token embedded previewer`. |
| Logic Risk | The security descriptor is a creation-time object boundary. If the branch is broadened by path-only matching, image-only matching, or a generic workaround label, Sandboxie can accidentally create unrelated files with a more public descriptor. If the branch is removed without a Windows Outlook previewer matrix, embedded previewers can lose access to the OICE_ exchange file. |
| Official Shape | Microsoft documents `OBJECT_ATTRIBUTES.SecurityDescriptor` as the security descriptor used when an object is created; security descriptors include DACL/SACL/control information; and `RtlSetDaclSecurityDescriptor` sets an explicit DACL, with NULL DACL being a separate unrestricted-access shape. |
| Fix | Comment-only source clarification. The source now names SREV-268 and states that this is an Outlook OICE_ previewer compatibility descriptor scoped to Outlook image type and OICE_ path segment. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-268.py` validates the draft-07 schema, official references, source comment owner, exact Outlook + OICE_ gate, `Secure_EveryoneSD` assignment, explicit local DACL construction in `secure.c`, removal of the anonymous `$Workaround$` label for this branch, and the ledger fragment; `docs/plan/check-srev-268.sh` is the targeted wrapper. Runtime gate: Windows Outlook 2010/Office previewer test where an embedded restricted-token previewer can use the OICE_ file, while non-Outlook callers and non-OICE_ paths do not receive this descriptor override. |
