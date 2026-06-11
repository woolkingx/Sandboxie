#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-209 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-209 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-209-current-process-signature-path-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-209 failed: schema is not draft-07")
if schema.get("id") != "CURRENT_PROCESS_SIGNATURE_PATH_CONTRACT":
    raise SystemExit("SREV-209 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/verify.h":
    raise SystemExit("SREV-209 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/drv/verify.c":
    raise SystemExit("SREV-209 failed: wrong implementation")

contracts = "\n".join(schema["contracts"])
for term in [
    "driver verification declaration boundary",
    "current-process signature sidecar path builder",
    "counted UNICODE_STRING",
    "plus .sig plus one Unicode terminator",
    "Length excludes the terminator",
    "must not use wcscpy or wcscat",
]:
    require(contracts, term, "schema contract")

header = (ROOT / "Sandboxie/core/drv/verify.h").read_text()
src = (ROOT / "Sandboxie/core/drv/verify.c").read_text()
spec = (ROOT / "docs/plan/srev-209-current-process-signature-path-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-209.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef union _SCertInfo",
    "extern SCertInfo Verify_CertInfo;",
    "NTSTATUS KphVerifyBuffer(PUCHAR Buffer, ULONG BufferSize, PUCHAR Signature, ULONG SignatureSize);",
    "NTSTATUS KphVerifyCurrentProcess();",
]:
    require(header, term, "verify.h declaration boundary")

fn = between(
    src,
    "NTSTATUS KphVerifyCurrentProcess()",
    "//---------------------------------------------------------------------------\n\n#define KERNEL_MODE",
)

for term in [
    "PUNICODE_STRING processFileName = NULL;",
    "PUNICODE_STRING signatureFileName = NULL;",
    "USHORT signatureNameLength;",
    "USHORT signatureNameMaximumLength;",
    "SeLocateProcessImageName(PsGetCurrentProcess(), &processFileName)",
    "if (!processFileName->Buffer ||",
    "processFileName->Length > (0xFFFF - 5 * sizeof(WCHAR))",
    "status = STATUS_NAME_TOO_LONG;",
    "signatureNameLength = processFileName->Length + 4 * sizeof(WCHAR);",
    "signatureNameMaximumLength = signatureNameLength + sizeof(WCHAR);",
    "sizeof(UNICODE_STRING) + signatureNameMaximumLength",
    "signatureFileName->Length = signatureNameLength;",
    "signatureFileName->MaximumLength = signatureNameMaximumLength;",
    "memcpy(signatureFileName->Buffer, processFileName->Buffer, processFileName->Length);",
    "memcpy((PUCHAR)signatureFileName->Buffer + processFileName->Length,",
    "L\".sig\", 5 * sizeof(WCHAR));",
    "KphReadSignature(signatureFileName, &signature, &signatureSize)",
    "KphVerifyFile(processFileName, signature, signatureSize)",
]:
    require(fn, term, "counted signature path builder")

reject(fn, "wcscpy(signatureFileName->Buffer, processFileName->Buffer);", "null-terminated process path copy")
reject(fn, "wcscat(signatureFileName->Buffer, L\".sig\");", "null-terminated signature suffix append")
reject(fn, "processFileName->MaximumLength + 4 * sizeof(WCHAR)", "underallocated signature path")
reject(fn, "processFileName->MaximumLength + 5 * sizeof(WCHAR)", "capacity derived from MaximumLength instead of Length")

if not fn.index("processFileName->Length >") < fn.index("signatureNameLength ="):
    raise SystemExit("SREV-209 failed: overflow gate appears after signature length calculation")
if not fn.index("signatureNameMaximumLength =") < fn.index("ExAllocatePoolWithTag("):
    raise SystemExit("SREV-209 failed: maximum length calculated after allocation")
if not fn.index("signatureFileName->Length =") < fn.index("memcpy(signatureFileName->Buffer"):
    raise SystemExit("SREV-209 failed: UNICODE_STRING length set after counted copy")
if not fn.index("memcpy(signatureFileName->Buffer") < fn.index("KphReadSignature(signatureFileName"):
    raise SystemExit("SREV-209 failed: signature path read before counted copy")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-209",
    "owner: Sandboxie/core/drv/verify.h",
    "implementation: Sandboxie/core/drv/verify.c",
    "spec: docs/plan/srev-209-current-process-signature-path-contract.md",
    "schema: docs/plan/srev-209-current-process-signature-path-contract.schema.json",
    "checker: docs/plan/check-srev-209.py",
    "patched source-level after official counted Unicode string shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-209 source gate passed")
