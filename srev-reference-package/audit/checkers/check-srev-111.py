#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-111 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-111 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-111-driver-public-security-and-private-handles.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-111 failed: schema is not draft-07")
if schema.get("id") != "DRIVER_PUBLIC_SECURITY_AND_PRIVATE_HANDLES":
    raise SystemExit("SREV-111 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Driver_InitPublicSecurity builds absolute security descriptors",
    "ACL and security descriptor construction DDIs return NTSTATUS and must fail closed",
    "existing compatibility DACL to Authenticated Users and Everyone",
    "low-integrity SACL plus restricted-code DACL",
    "Mandatory Integrity Control stores an integrity label",
    "Driver_FindHomePath creates only private driver handles",
    "OBJ_KERNEL_HANDLE",
    "ObReferenceObjectByHandle with KernelMode",
    "must not change SID values access masks descriptor consumers",
    "runtime proof is required",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/driver.c").read_text()
spec = (ROOT / "docs/plan/srev-111-driver-public-security-and-private-handles.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = source.index("_FX BOOLEAN Driver_InitPublicSecurity(void)")
end = source.index("#undef MyAddAccessAllowedAce", start)
init_security = source[start:end]

for term in [
    "NTSTATUS status;",
    "status = RtlCreateAcl(Driver_PublicAcl, 128, ACL_REVISION);",
    "if (! NT_SUCCESS(status))",
    "status = RtlAddAccessAllowedAceEx(pAcl, ACL_REVISION",
    "status = RtlCreateSecurityDescriptor(",
    "status = RtlSetDaclSecurityDescriptor(",
    "status = RtlAddAce(LowLabelAcl1, ACL_REVISION, 0, pAce, pAce->Header.AceSize);",
    "status = RtlSetSaclSecurityDescriptor(",
    "Driver_PublicAcl",
    "Driver_PublicSd",
    "Driver_LowLabelSd",
    "SYSTEM_MANDATORY_LABEL_ACE_TYPE",
    "SYSTEM_MANDATORY_LABEL_NO_WRITE_UP",
    "SECURITY_MANDATORY_LOW_RID",
    "SECURITY_RESTRICTED_CODE_RID",
]:
    require(init_security, term, "Driver_InitPublicSecurity")

for term in [
    "RtlCreateAcl(Driver_PublicAcl, 128, ACL_REVISION);\n    MyAddAccessAllowedAce",
    "RtlCreateSecurityDescriptor(\n        Driver_PublicSd, SECURITY_DESCRIPTOR_REVISION);\n    RtlSetDaclSecurityDescriptor",
    "RtlCreateAcl(LowLabelAcl1, 128, ACL_REVISION);\n        RtlAddAce",
    "RtlCreateSecurityDescriptor(\n            Driver_LowLabelSd, SECURITY_DESCRIPTOR_REVISION);\n        RtlSetDaclSecurityDescriptor",
    "RtlSetDaclSecurityDescriptor(\n            Driver_LowLabelSd, TRUE, LowLabelAcl2, FALSE);\n        RtlSetSaclSecurityDescriptor",
]:
    reject(init_security, term, "unchecked security descriptor construction")

start = source.index("_FX BOOLEAN Driver_FindHomePath")
end = source.index("// Driver_FindKiServiceInternal", start)
home_path = source[start:end]

for term in [
    "RegistryPath, OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE, NULL, NULL",
    "&uni, OBJ_CASE_INSENSITIVE | OBJ_KERNEL_HANDLE, NULL, NULL",
    "status = ZwOpenKey(&handle, KEY_READ, &objattrs);",
    "status = ZwQueryValueKey(",
    "ZwClose(handle);",
    "status = ZwCreateFile(",
    "FILE_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT",
    "status = ObReferenceObjectByHandle(",
    "handle, 0, NULL, KernelMode, &file_object, NULL",
    "ObDereferenceObject(file_object);",
]:
    require(home_path, term, "Driver_FindHomePath private handle topology")

for term in [
    "InitializeObjectAttributes(&objattrs,\n        RegistryPath, OBJ_CASE_INSENSITIVE, NULL, NULL);",
    "InitializeObjectAttributes(&objattrs,\n        &uni, OBJ_CASE_INSENSITIVE, NULL, NULL);",
]:
    reject(home_path, term, "missing OBJ_KERNEL_HANDLE")

for term in [
    "### SREV-111: Driver Public Security And Private Handles",
    "DRIVER_PUBLIC_SECURITY_AND_PRIVATE_HANDLES",
    "srev-111-driver-public-security-and-private-handles.schema.json",
    "Sandboxie/core/drv/driver.c",
    "Driver_InitPublicSecurity",
    "Driver_FindHomePath",
    "OBJ_KERNEL_HANDLE",
    "ObReferenceObjectByHandle",
]:
    require(ledger, term, "ledger")

print("SREV-111 schema/source gate passed")
