#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-048 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-048 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-048-ipc-query-symbolic-link.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-048 failed: schema is not draft-07")
if schema.get("id") != "IPC_QUERY_SYMBOLIC_LINK_BUFFER":
    raise SystemExit("SREV-048 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "name_len is the shared user buffer capacity in bytes",
    "NUL-terminated symbolic-link object name",
    "empty input name and unterminated input are invalid",
    "copy stops at the first input NUL",
    "MaximumLength set to the shared buffer capacity",
    "ProbeForWrite",
]:
    require(contracts, term, "schema")

for term in [
    "name_len",
    "input_name",
    "query_output",
]:
    require("\n".join(schema["properties"].keys()), term, "draft-07 properties")

src = (ROOT / "Sandboxie/core/drv/ipc.c").read_text()
spec = (ROOT / "docs/plan/srev-048-ipc-query-symbolic-link.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX NTSTATUS Ipc_Api_QuerySymbolicLink(")
end = src.index("// Api_Unload", start)
query = src[start:end]

for term in [
    "if (args->name_len.val & 1)",
    "user_len = args->name_len.val / sizeof(WCHAR);",
    "buf = Mem_Alloc(proc->pool, (user_len + 1) * sizeof(WCHAR));",
    "for (i = 0; i < user_len; ++i)",
    "buf[i] = user_buf[i];",
    "if (buf[i] == L'\\0')",
    "if ((! i) || (i == user_len))",
    "goto finish;",
    "objname.Length = 0;",
    "objname.MaximumLength = (USHORT)(user_len * sizeof(WCHAR));",
    "status = ZwQuerySymbolicLinkObject(handle, &objname, NULL);",
    "if (len >= user_len)",
    "ProbeForWrite(\n                    user_buf, sizeof(WCHAR) * (len + 1), sizeof(WCHAR));",
    "wmemcpy(user_buf, buf, len + 1);",
    "finish:",
    "Mem_Free(buf, (user_len + 1) * sizeof(WCHAR));",
]:
    require(query, term, "Ipc_Api_QuerySymbolicLink")

for term in [
    "wmemcpy(buf, user_buf, user_len);",
    "buf[user_len] = L'\\0';",
    "if (len >= user_len - 1)",
    "ProbeForRead(\n                    user_buf, sizeof(WCHAR) * (len + 1), sizeof(WCHAR));",
    "Mem_Free(buf, (user_len + 8) * sizeof(WCHAR));",
]:
    reject(query, term, "Ipc_Api_QuerySymbolicLink")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopensymboliclinkobject",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwquerysymboliclinkobject",
    "srev-048-ipc-query-symbolic-link.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-048: IPC Query Symbolic Link Buffer",
    "IPC_QUERY_SYMBOLIC_LINK_BUFFER",
    "srev-048-ipc-query-symbolic-link.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-048 schema/source gate passed")
