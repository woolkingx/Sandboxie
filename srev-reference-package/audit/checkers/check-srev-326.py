#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-326 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-326 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-326-secure-bits-wuau-accesscheck-bypass.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-326 failed: schema is not draft-07")
if schema.get("id") != "SECURE_BITS_WUAU_ACCESSCHECK_BYPASS":
    raise SystemExit("SREV-326 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/secure.c":
    raise SystemExit("SREV-326 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "official access-check semantics are descriptor, token, object-type, and generic mapping decisions",
    "MAXIMUM_ALLOWED is not equivalent to blindly granting GenericAll",
    "local compatibility bypass",
    "limited to BITS, Sandboxie WUAU, and wuauclt images",
    "allowlisted callers must try Ldr_TestToken plus native __sys_NtAccessCheckByType",
    "native API call itself fails",
    "continue through Ldr_TestToken and native __sys_NtAccessCheckByType",
    "runtime matrix must cover Windows versions",
    "adds a native access-check first path",
    "SREV-326 and SREV-327 share docs/plan/srev-326-327-secure-runtime-capture.schema.json",
]:
    require(contracts, term, "schema contracts")

secure = (ROOT / "Sandboxie/core/dll/secure.c").read_text()
spec = (ROOT / "docs/plan/srev-326-secure-bits-wuau-accesscheck-bypass.md").read_text()
shared_playbook = (ROOT / "docs/plan/srev-326-327-secure-runtime-capture-playbook.md").read_text()
shared_schema = json.loads((ROOT / "docs/plan/srev-326-327-secure-runtime-capture.schema.json").read_text())
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-326.md").read_text()

if shared_schema.get("id") != "SECURE_RUNTIME_CAPTURE_EVIDENCE":
    raise SystemExit("SREV-326 failed: shared secure capture schema has wrong id")
require(shared_playbook, "Non-allowlisted caller using same hook", "shared capture playbook")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = secure.index("NTSTATUS Ldr_NtAccessCheckByType(")
end = secure.index("_FX NTSTATUS Ldr_NtAccessCheck(", start)
func = secure[start:end]

for term in [
    "if (Dll_OsBuild >= 9600)",
    "BOOLEAN allowlisted_bits_wuau = FALSE;",
    "allowlisted_bits_wuau =",
    "Dll_ImageType == DLL_IMAGE_SANDBOXIE_BITS",
    "Dll_ImageType == DLL_IMAGE_SANDBOXIE_WUAU",
    "Dll_ImageType == DLL_IMAGE_WUAUCLT",
    "Ldr_TestToken(ClientToken, &hTokenReal, TRUE);",
    "if (allowlisted_bits_wuau)",
    "SREV-326: official access-check semantics first.",
    "Let the native",
    "descriptor/token/object-type path decide",
    "fallback when the native API itself fails.",
    "rc = __sys_NtAccessCheckByType(",
    "hTokenReal ? hTokenReal : ClientToken",
    "if (NT_SUCCESS(rc))",
    "return rc;",
    "ACCESS_MASK granted_access = DesiredAccess;",
    "if ((DesiredAccess & MAXIMUM_ALLOWED) && GenericMapping)",
    "granted_access = GenericMapping->GenericAll\n                               | (DesiredAccess & ~MAXIMUM_ALLOWED);",
    "*GrantedAccess = granted_access;",
    "*AccessStatus = STATUS_SUCCESS;",
    "SetLastError(0);",
    "return STATUS_SUCCESS;",
    "NtClose(hTokenReal);",
]:
    require(func, term, "Ldr_NtAccessCheckByType source")

allowlist = func.index("if (allowlisted_bits_wuau)")
test_token = func.index("Ldr_TestToken(ClientToken, &hTokenReal, TRUE);")
native = func.index("rc = __sys_NtAccessCheckByType(", allowlist)
synthetic = func.index("ACCESS_MASK granted_access = DesiredAccess;", native)
if not test_token < allowlist < native < synthetic:
    raise SystemExit("SREV-326 failed: allowlisted callers must run native access check before synthetic fallback")

for stale in [
    "todo: is that right? It seems wrong",
]:
    reject(func, stale, "source uncertainty comment")

for term in [
    "SECURE_BITS_WUAU_ACCESSCHECK_BYPASS",
    "Runtime Verification Matrix",
    "docs/plan/srev-326-327-secure-runtime-capture-playbook.md",
    "docs/plan/srev-326-327-secure-runtime-capture.schema.json",
    "Windows 8.1 baseline",
    "Non-allowlist callers",
    "deny DACL",
    "`GrantedAccess`, `AccessStatus`, `SetLastError`, and return status",
    "No public Microsoft Win32 API page was found for `NtAccessCheckByType`",
    "native access-check first ordering",
    "No image predicate, OS-build gate",
    "Do not treat `MAXIMUM_ALLOWED -> GenericAll` as a correct access-check model.",
    "non-allowlisted callers plus deny-descriptor cases",
    "docs/plan/check-srev-326-327-secure-runtime-capture.sh",
    "Windows gate: run the runtime verification matrix above before release.",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-326",
    "owner: Sandboxie/core/dll/secure.c",
    "spec: docs/plan/srev-326-secure-bits-wuau-accesscheck-bypass.md",
    "schema: docs/plan/srev-326-secure-bits-wuau-accesscheck-bypass.schema.json",
    "checker: docs/plan/check-srev-326.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-326: Secure BITS/WUAU AccessCheckByType Bypass",
    "SECURE_BITS_WUAU_ACCESSCHECK_BYPASS",
    "AccessCheckByType",
    "MAXIMUM_ALLOWED",
    "DLL_IMAGE_SANDBOXIE_BITS",
    "non-allowlisted caller negative controls",
    "allow/deny/NULL/owner-specific/object-type security descriptors",
]:
    require(ledger, term, "combined ledger")

print("SREV-326 schema/source gate passed")
