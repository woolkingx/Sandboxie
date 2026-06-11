#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-300 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-300 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-300-ipc-self-impersonation-status-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-300 failed: schema is not draft-07")
if schema.get("id") != "IPC_SELF_IMPERSONATION_STATUS_GATE":
    raise SystemExit("SREV-300 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/ipc.c":
    raise SystemExit("SREV-300 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Ipc_ImpersonateSelf success means an existing SecurityImpersonation token was preserved or a self TokenImpersonation token was installed",
    "NtQueryInformationToken(TokenImpersonationLevel) owns the current thread token level read",
    "NtDuplicateToken(TokenImpersonation) owns the self primary-token to impersonation-token conversion",
    "NtSetInformationThread(ThreadImpersonationToken) owns the thread-token install result",
    "Ipc_ImpersonateSelf must return the actual self-impersonation status",
    "SREV-110 owns the adjacent driver-side private-offset impersonation replay shim",
]:
    require(contracts, term, "schema")

ipc = (ROOT / "Sandboxie/core/dll/ipc.c").read_text()
spec = (ROOT / "docs/plan/srev-300-ipc-self-impersonation-status-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-300.md").read_text()
srev_110 = "\n".join([
    (ROOT / "docs/plan/ledger/srev-110.md").read_text(),
    (ROOT / "docs/plan/srev-110-thread-impersonation-offset-boundary.md").read_text(),
    (ROOT / "docs/plan/srev-110-thread-impersonation-offset-boundary.schema.json").read_text(),
])

start = ipc.index("_FX NTSTATUS Ipc_ImpersonateSelf(")
end = ipc.index("// Ipc_NtImpersonateClientOfPort", start)
self_func = ipc[start:end]

start = ipc.index("_FX NTSTATUS Ipc_NtImpersonateClientOfPort(")
end = ipc.index("// Ipc_NtAlpcImpersonateClientOfPort", start)
lpc_func = ipc[start:end]

start = ipc.index("_FX NTSTATUS Ipc_NtAlpcImpersonateClientOfPort(")
end = ipc.index("// Ipc_NtImpersonateAnonymousToken", start)
alpc_func = ipc[start:end]

for term in [
    "NtOpenThreadToken(\n                        NtCurrentThread(), TOKEN_QUERY, FALSE, &hOldToken);",
    "NtQueryInformationToken(\n            hOldToken, TokenImpersonationLevel,",
    "if (ImpLevel >= SecurityImpersonation) {\n\n            NtClose(hOldToken);\n            return STATUS_SUCCESS;\n        }",
    "NtSetInformationThread(\n        NtCurrentThread(), ThreadImpersonationToken,\n        &hNewToken, sizeof(HANDLE));",
    "NtOpenProcessToken(\n                        NtCurrentProcess(), TOKEN_DUPLICATE, &hPriToken);",
    "QoS.ImpersonationLevel = SecurityImpersonation;",
    "status = NtDuplicateToken(\n            hPriToken, TOKEN_IMPERSONATE | TOKEN_QUERY, &objattrs,\n            FALSE, TokenImpersonation, &hNewToken);",
    "NtSetInformationThread(\n                NtCurrentThread(), ThreadImpersonationToken,\n                &hNewToken, sizeof(HANDLE));",
    "NtSetInformationThread(\n                NtCurrentThread(), ThreadImpersonationToken,\n                &hOldToken, sizeof(HANDLE));",
    "return status;",
]:
    require(self_func, term, "Ipc_ImpersonateSelf")

reject(self_func, "return STATUS_SUCCESS;\n}\n\n\n//---------------------------------------------------------------------------\n// Ipc_NtImpersonateClientOfPort", "Ipc_ImpersonateSelf final return")

for term in [
    "NTSTATUS status =\n        __sys_NtImpersonateClientOfPort(PortHandle, RequestMessage);",
    "if (! Dll_IsSystemSid)\n        status = Ipc_ImpersonateSelf(NULL);",
    "return status;",
]:
    require(lpc_func, term, "Ipc_NtImpersonateClientOfPort")

for term in [
    "SREV-300: if ALPC client impersonation fails or yields only",
    "SecurityIdentification, the local compatibility path duplicates this",
    "process primary token into a SecurityImpersonation thread token.",
    "Success must mean that Ipc_ImpersonateSelf actually installed that",
    "token or preserved an existing SecurityImpersonation token.",
    "NTSTATUS status = __sys_NtAlpcImpersonateClientOfPort(",
    "if (! Dll_IsSystemSid)\n        status = Ipc_ImpersonateSelf(RequestMessage);",
    "return status;",
]:
    require(alpc_func, term, "Ipc_NtAlpcImpersonateClientOfPort")

for stale in [
    "this workaround allows this to succeed by impersonating our own",
    "credentials, which is reasonable, because presumably everything in",
]:
    reject(alpc_func, stale, "ALPC comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "IPC_SELF_IMPERSONATION_STATUS_GATE",
    "Ipc_ImpersonateSelf must return the actual self-impersonation status",
    "SREV-110 owns the adjacent driver-side private-offset token replay shim",
    "No token access mask, impersonation level,",
]:
    require(spec, term, "spec")

for term in [
    "THREAD_IMPERSONATION_OFFSET_BOUNDARY",
    "SecurityIdentification cannot impersonate",
    "SecurityImpersonation can impersonate locally",
    "this SREV must not replace the shim with direct SecurityImpersonation or worker-thread dispatch",
]:
    require(srev_110, term, "SREV-110 adjacency")

for term in [
    "### SREV-300: IPC Self Impersonation Status Gate",
    "IPC_SELF_IMPERSONATION_STATUS_GATE",
    "srev-300-ipc-self-impersonation-status-gate.schema.json",
    "Sandboxie/core/dll/ipc.c",
    "Ipc_ImpersonateSelf",
    "Ipc_NtAlpcImpersonateClientOfPort",
    "SREV-110",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-300 source gate passed")
