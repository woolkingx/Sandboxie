#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-194 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-194 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-194-protected-root-api-string-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-194 failed: schema is not draft-07")
if schema.get("id") != "PROTECTED_ROOT_API_STRING_CONTRACT":
    raise SystemExit("SREV-194 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/file_flt.c":
    raise SystemExit("SREV-194 failed: wrong owner")
if schema.get("entry_surface") != "Sandboxie/core/drv/file.h":
    raise SystemExit("SREV-194 failed: wrong entry surface")

contracts = "\n".join(schema["contracts"])
for term in [
    "file.h declares the protected root API entry points",
    "API_PROTECT_ROOT receives raw user-mode pointer arguments",
    "API_UNPROTECT_ROOT receives a raw user-mode reg_root pointer",
    "reg_root must terminate within MAX_REG_ROOT_LEN",
    "file_root must terminate within the driver bounded cap",
    "driver probes bounded string bytes before copying",
    "driver must not use unbounded wcslen on protected root API pointers",
    "allocation failure must not be reported as successful protection",
]:
    require(contracts, term, "schema contracts")

file_h = (ROOT / "Sandboxie/core/drv/file.h").read_text()
file_flt = (ROOT / "Sandboxie/core/drv/file_flt.c").read_text()
mount = (ROOT / "Sandboxie/core/svc/MountManager.cpp").read_text()
spec = (ROOT / "docs/plan/srev-194-protected-root-api-string-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-194.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "NTSTATUS File_Api_ProtectRoot(PROCESS *proc, ULONG64 *parms);",
    "NTSTATUS File_Api_UnprotectRoot(PROCESS *proc, ULONG64 *parms);",
]:
    require(file_h, term, "file.h protected root declarations")

for term in [
    "SbieApi_Call(API_PROTECT_ROOT, 3, req->reg_root, TargetNtPath.c_str(), admin_only)",
    "SbieApi_Call(API_UNPROTECT_ROOT, 1, req->reg_root)",
]:
    require(mount, term, "MountManager producer shape")

helper = between(
    file_flt,
    "_FX BOOLEAN File_ProtectedRootStringLen(",
    "_FX NTSTATUS File_Api_ProtectRoot(",
)
for term in [
    "if ((! text) || (! out_len) || (! max_chars))",
    "for (i = 0; i < max_chars; ++i)",
    "if (text[i] == L'\\0')",
    "*out_len = i;",
]:
    require(helper, term, "bounded string helper")

protect = between(
    file_flt,
    "_FX NTSTATUS File_Api_ProtectRoot(",
    "//---------------------------------------------------------------------------\n// File_Api_UnprotectRoot",
)
for term in [
    "if (! File_ProtectedRootStringLen(reg_root, MAX_REG_ROOT_LEN, &reg_root_len))",
    "if ((! File_ProtectedRootStringLen(file_root, 32767, &file_root_len)) ||",
    "(! file_root_len)",
    "ProbeForRead(reg_root, (reg_root_len + 1) * sizeof(WCHAR), sizeof(WCHAR));",
    "ProbeForRead(file_root, (file_root_len + 1) * sizeof(WCHAR), sizeof(WCHAR));",
    "if (! root)\n        return STATUS_INSUFFICIENT_RESOURCES;",
    "root->file_root_len = file_root_len;",
    "root->reg_root_len = reg_root_len;",
]:
    require(protect, term, "ProtectRoot bounded gate")
reject(protect, "wcslen(", "ProtectRoot unbounded string scan")

unprotect = between(
    file_flt,
    "_FX NTSTATUS File_Api_UnprotectRoot(",
    "    return status;\n}",
)
for term in [
    "if (! File_ProtectedRootStringLen((WCHAR *)parms[1], MAX_REG_ROOT_LEN, &reg_root_len))",
    "ProbeForRead((WCHAR *)parms[1], (reg_root_len + 1) * sizeof(WCHAR), sizeof(WCHAR));",
    "wmemcpy(reg_root, (WCHAR *)parms[1], reg_root_len);",
]:
    require(unprotect, term, "UnprotectRoot bounded gate")
reject(unprotect, "wcslen(", "UnprotectRoot unbounded string scan")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-194",
    "owner: Sandboxie/core/drv/file_flt.c",
    "spec: docs/plan/srev-194-protected-root-api-string-contract.md",
    "schema: docs/plan/srev-194-protected-root-api-string-contract.schema.json",
    "checker: docs/plan/check-srev-194.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-194: Protected Root API String Contract",
    "PROTECTED_ROOT_API_STRING_CONTRACT",
    "Sandboxie/core/drv/file.h",
    "Sandboxie/core/drv/file_flt.c",
    "File_ProtectedRootStringLen",
    "ProbeForRead",
    "STATUS_INSUFFICIENT_RESOURCES",
]:
    require(ledger, term, "combined ledger")

print("SREV-194 schema/source gate passed")
