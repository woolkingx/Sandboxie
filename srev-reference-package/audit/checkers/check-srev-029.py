#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-029 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-029 failed: {label} still contains {needle!r}")


api = json.loads((ROOT / "docs/plan/srev-029-crypt-wire.schema.json").read_text())
if api.get("id") != "COM_CRYPT_PROTECT_DATA":
    raise SystemExit("SREV-029 failed: schema missing COM_CRYPT_PROTECT_DATA")

for path in ["request", "reply"]:
    if path in api:
        require(api[path]["payload_offset"], "FIELD_OFFSET", f"schema {path}")
        if not api[path]["segments"]:
            raise SystemExit(f"SREV-029 failed: schema {path} has no segments")
    else:
        audit_contract = api["properties"]["audit_contract"]["description"]
        require(audit_contract, f"{path}:", f"schema {path}")
        require(audit_contract, "\"payload_offset\": \"FIELD_OFFSET", f"schema {path}")
        require(audit_contract, "\"segments\": [", f"schema {path}")

contracts = "\n".join(api["contracts"])
for term in [
    "checked ULONG addition",
    "validate reply h.length",
    "subtracting remaining length",
    "LocalAlloc outputs",
]:
    require(contracts, term, "schema contracts")

dll = (ROOT / "Sandboxie/core/dll/crypt.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/comserver2.cpp").read_text()
spec = (ROOT / "docs/plan/srev-029-crypt-wire-schema.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "Crypt_AddUlong",
    "Crypt_WcharsToBytesWithNull",
    "Crypt_GetBlobLength",
    "Crypt_ValidateReply",
    "Crypt_GetOptionalBlobLength(pOptionalEntropy, &entropy_len)",
    "pDataOut->pbData = NULL;",
    "if (reply_data_len)",
    "if (descr_len_size > ~0u)",
    "Crypt_ValidateReply(rpl, &reply_data_len, &reply_descr_len)",
    "Crypt_ValidateReply(rpl, &reply_data_len, NULL)",
]:
    require(dll, term, "DLL source")

for stale in [
    "req_len = sizeof(COM_CRYPT_PROTECT_DATA_REQ)\n            +",
    "LocalAlloc(LPTR, rpl->data_len)",
    "memcpy(pDataOut->pbData, rpl->data, rpl->data_len)",
    "(rpl->descr_len + 1) * sizeof(WCHAR)",
    "wmemcpy(*ppszDataDescr, (WCHAR*)(rpl->data + rpl->data_len)",
]:
    reject(dll, stale, "DLL source")

for term in [
    "CryptAddUlong",
    "CryptWcharsToBytesWithNull",
    "remaining = req_len - offset;",
    "if (req->data_len > remaining)",
    "if (req->entropy_len > remaining)",
    "if (descr_bytes > remaining)",
    "CryptAddUlong(rpl_len, DataOut.cbData, &rpl_len)",
    "CryptAddUlong(rpl_len, descr_bytes, &rpl_len)",
    "if (rpl->data_len)",
    "((WCHAR*)(rpl->data + rpl->data_len))[descr_len] = L'\\0';",
]:
    require(svc, term, "service source")

for stale in [
    "offset + req->data_len > req_len",
    "offset + req->entropy_len > req_len",
    "offset + req->descr_len * sizeof(WCHAR) > req_len",
    "rpl_len += (descr_len + 1) * sizeof(WCHAR)",
    "wmemcpy((WCHAR*)(rpl->data + rpl->data_len), DataDescr, descr_len);",
]:
    reject(svc, stale, "service source")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata",
    "srev-029-crypt-wire.schema.json",
    "COM_CRYPT_PROTECT_DATA",
    "checked addition",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-029: Crypt DPAPI Broker Wire Schema",
    "srev-029-crypt-wire.schema.json",
    "Crypt_ValidateReply",
    "CryptAddUlong",
]:
    require(ledger, term, "ledger")

print("SREV-029 schema/source gate passed")
