#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-031 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-031 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-031-process-low-sid.schema.json").read_text())
if schema.get("id") != "API_INJECT_COMPLETE_SANDBOXIE_LOGON_SID":
    raise SystemExit("SREV-031 failed: wrong SID schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "RtlValidSid must succeed before RtlLengthSid",
    "RtlLengthSid result must be <= SECURITY_MAX_SID_SIZE",
    "copy uses RtlCopySid",
    "PROCESS.SandboxieLogonSid is a PSID",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/process_low.c").read_text()
hdr = (ROOT / "Sandboxie/core/drv/process.h").read_text()
spec = (ROOT / "docs/plan/srev-031-process-low-sid.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "NTSTATUS status = STATUS_SUCCESS;",
    "ProbeForRead(pSID, SECURITY_MAX_SID_SIZE, sizeof(UCHAR));",
    "if (! RtlValidSid(pSID))",
    "ULONG sid_length = RtlLengthSid(pSID);",
    "sid_length > SECURITY_MAX_SID_SIZE",
    "if (! proc->SandboxieLogonSid)",
    "status = RtlCopySid(",
    "Mem_Free(proc->SandboxieLogonSid, sid_length);",
    "proc->SandboxieLogonSid = NULL;",
]:
    require(src, term, "source")

valid = src.index("RtlValidSid(pSID)")
length = src.index("RtlLengthSid(pSID)")
copy = src.index("RtlCopySid(")
if not (valid < length < copy):
    raise SystemExit("SREV-031 failed: SID validation/copy order is wrong")

reject(src, "memcpy(proc->SandboxieLogonSid, pSID, sid_length)", "source")

require(hdr, "PSID SandboxieLogonSid;", "process header")
reject(hdr, "PSID *SandboxieLogonSid;", "process header")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlvalidsid",
    "srev-031-process-low-sid.schema.json",
    "RtlLengthSid",
    "RtlCopySid",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-031: Process Low Inject SID Validation",
    "RtlValidSid",
    "RtlCopySid",
    "srev-031-process-low-sid.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-031 schema/source gate passed")
