#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-105 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-105 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-105-verify-legacy-cert-level-compatibility.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-105 failed: schema is not draft-07")
if schema.get("id") != "VERIFY_LEGACY_CERT_LEVEL_COMPATIBILITY":
    raise SystemExit("SREV-105 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "certificate validity is a time-window decision",
    "Windows system time is represented as UTC 100-nanosecond intervals",
    "Certificate.dat is a local signed text contract",
    "legacy LARGE MEDIUM and SMALL levels are parser compatibility aliases",
    "LARGE assigns an explicit two-year expiration interval",
    "MEDIUM keeps the default one-year expiration interval",
    "SMALL maps to Home subscription",
    "expiration_date drives expired and expirers_in_sec",
    "non-subscription certificates become outdated",
    "subscription certificates are gated by expired",
    "inactive certificates must be set inactive with STATUS_ACCOUNT_EXPIRED",
    "must not remove legacy level branches",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/verify.c").read_text()
spec = (ROOT / "docs/plan/srev-105-verify-legacy-cert-level-compatibility.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static const WCHAR *path_cert = L\"%s\\\\Certificate.dat\";",
    "MyHashData(&hashObj, temp, temp_len);",
    "_wcsicmp(L\"DATE\", name) == 0",
    "_wcsicmp(L\"TYPE\", name) == 0",
    "CERT_IS_TYPE(Verify_CertInfo, eCertPersonal) || CERT_IS_TYPE(Verify_CertInfo, eCertPatreon)",
    "_wcsicmp(level, L\"HUGE\") == 0",
    "_wcsicmp(level, L\"LARGE\") == 0 && cert_date.QuadPart < KphGetDate(1, 04, 2022)",
    "expiration_date.QuadPart = -2;",
    "Legacy LARGE level remains a signed certificate compatibility alias; expiration is enforced below.",
    "_wcsicmp(level, L\"LARGE\") == 0",
    "expiration_date.QuadPart = cert_date.QuadPart + KphGetDateInterval(0, 0, 2);",
    "Legacy MEDIUM level remains a signed certificate compatibility alias; default expiration is enforced below.",
    "_wcsicmp(level, L\"MEDIUM\") == 0",
    "Verify_CertInfo.level = eCertStandard2;",
    "Legacy SMALL level remains a signed certificate compatibility alias; subscription expiration is enforced below.",
    "_wcsicmp(level, L\"SMALL\") == 0",
    "Verify_CertInfo.type = eCertHome;",
    "else if (!expiration_date.QuadPart)",
    "KphGetDateInterval(0, 0, 1);",
    "BOOLEAN isSubscription = CERT_IS_SUBSCRIPTION(Verify_CertInfo);",
    "Verify_CertInfo.expired = 1;",
    "Verify_CertInfo.outdated = 1;",
    "isSubscription ? Verify_CertInfo.expired : Verify_CertInfo.outdated",
    "Verify_CertInfo.active = 0;",
    "status = STATUS_ACCOUNT_EXPIRED;",
]:
    require(source, term, "verify.c source shape")

scheme_start = source.index("// scheme 1.1 >>>")
scheme_end = source.index("// <<< scheme 1.1", scheme_start)
scheme = source[scheme_start:scheme_end]

large_legacy = scheme.index("cert_date.QuadPart < KphGetDate(1, 04, 2022)")
large_current = scheme.index("Legacy LARGE level remains")
medium = scheme.index("Legacy MEDIUM level remains")
small = scheme.index("Legacy SMALL level remains")
if not (large_legacy < large_current < medium < small):
    raise SystemExit("SREV-105 failed: legacy level branch order changed")

expiration_gate = source[source.index("if (CERT_IS_TYPE(Verify_CertInfo, eCertEternal))"):source.index("// check if lock is required")]
if expiration_gate.index("else if (!expiration_date.QuadPart)") > expiration_gate.index("BOOLEAN isSubscription"):
    raise SystemExit("SREV-105 failed: expiration fallback occurs after subscription classification")
if expiration_gate.index("BOOLEAN isSubscription") > expiration_gate.index("isSubscription ? Verify_CertInfo.expired"):
    raise SystemExit("SREV-105 failed: subscription gate occurs before classification")

for stale in [
    "todo: 01.09.2025: remove code for expired case LARGE",
    "todo: 01.09.2024: remove code for expired case MEDIUM",
    "todo: 01.09.2024: remove code for expired case SMALL",
]:
    reject(source, stale, "verify.c")

for term in [
    "### SREV-105: Verify Legacy Certificate Level Compatibility",
    "VERIFY_LEGACY_CERT_LEVEL_COMPATIBILITY",
    "srev-105-verify-legacy-cert-level-compatibility.schema.json",
    "Comment-only source clarification",
    "Sandboxie/core/drv/verify.c",
]:
    require(ledger, term, "ledger")

print("SREV-105 schema/source gate passed")
