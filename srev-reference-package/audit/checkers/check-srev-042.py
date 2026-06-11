#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-042 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-042 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-042-box-name-helper-routing.schema.json").read_text())
if schema.get("id") != "BOX_NAME_HELPER_ROUTING":
    raise SystemExit("SREV-042 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "explicit user box names must route through Api_CopyBoxNameFromUser",
    "must not duplicate ProbeForRead plus wcsncpy",
    "overlong unterminated box names must be rejected",
    "Process_Api_Enum keeps proc-owned box names",
    "Session_Api_ForceChildren requires a valid explicit box name",
]:
    require(contracts, term, "schema")

session = (ROOT / "Sandboxie/core/drv/session.c").read_text()
process_api = (ROOT / "Sandboxie/core/drv/process_api.c").read_text()
spec = (ROOT / "docs/plan/srev-042-box-name-helper-routing.md").read_text()
ledger = read_combined_ledger(ROOT)

sess_start = session.index("_FX NTSTATUS Session_Api_ForceChildren(")
sess_end = session.index("// Session_IsLeader", sess_start)
force_children = session[sess_start:sess_end]

enum_start = process_api.index("_FX NTSTATUS Process_Api_Enum(")
enum_end = process_api.index("_FX NTSTATUS Process_Api_Kill(", enum_start)
enum = process_api[enum_start:enum_end]

for term in [
    "user_boxname = (WCHAR *)parms[2];",
    "if (! Api_CopyBoxNameFromUser(boxname, user_boxname))",
    "return STATUS_INVALID_PARAMETER;",
    "Process_FcpInsert(process_id, boxname);",
]:
    require(force_children, term, "Session_Api_ForceChildren")

for term in [
    "if (proc)\n        wcscpy(boxname, proc->box->name);",
    "if ((! boxname[0]) && user_boxname) {",
    "if (! Api_CopyBoxNameFromUser(boxname, user_boxname))",
    "return STATUS_INVALID_PARAMETER;",
]:
    require(enum, term, "Process_Api_Enum")

for text, label in [
    (force_children, "Session_Api_ForceChildren"),
    (enum, "Process_Api_Enum"),
]:
    reject(text, "ProbeForRead(user_boxname, sizeof(WCHAR) * (BOXNAME_COUNT - 2)", label)
    reject(text, "wcsncpy(boxname, user_boxname, (BOXNAME_COUNT - 2))", label)
    reject(text, "sizeof(UCHAR)", label)

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-probeforread",
    "srev-041-api-copy-box-name.schema.json",
    "srev-042-box-name-helper-routing.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-042: Box Name Helper Routing",
    "Session_Api_ForceChildren",
    "Process_Api_Enum",
    "srev-042-box-name-helper-routing.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-042 schema/source gate passed")
