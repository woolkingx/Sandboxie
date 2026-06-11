#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-148 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-148 failed: {label} still contains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-148-dyndata-registry-blob-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-148 failed: schema is not draft-07")
if schema.get("id") != "DYNDATA_REGISTRY_BLOB_BOUNDARY":
    raise SystemExit("SREV-148 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "GetRegValue returns counted registry bytes; those bytes are not a legal SBIE_DYNDATA table until the local table shape is validated",
    "The table must contain the fixed SBIE_DYNDATA header before any header field read",
    "The Configs offset array must fit inside the counted blob before iteration",
    "Each nonzero config offset must start after the offset array and its Dyndata->Size bytes must fit inside the counted blob without overflow",
    "Dyndata->Size must be at least the current SBIE_DYNCONFIG size before the current driver reads current fields such as OsBuild_min and OsBuild_max",
    "Built-in default table allocation must be checked before clearing or writing the allocated buffer",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/drv/dyn_data.c").read_text()
hdr = (ROOT / "Sandboxie/core/drv/dyn_data.h").read_text()
spec = (ROOT / "docs/plan/srev-148-dyndata-registry-blob-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-148.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "typedef struct _SBIE_DYNCONFIG",
    "typedef struct _SBIE_DYNDATA",
    "USHORT Size;",
    "USHORT Count;",
    "USHORT Configs[1];",
]:
    require(hdr, term, "dyn_data.h schema")

helper = between(src, "static BOOLEAN Dyndata_IsValidData(", "#define INIT_DATA")
for term in [
    "ULONG HeaderSize = FIELD_OFFSET(SBIE_DYNDATA, Configs);",
    "if (!Dyndata || DyndataSize < HeaderSize)",
    "if (!Dyndata->Count || Dyndata->Size < sizeof(SBIE_DYNCONFIG))",
    "ConfigsEnd = HeaderSize + (ULONG)Dyndata->Count * sizeof(USHORT);",
    "if (ConfigsEnd > DyndataSize)",
    "for (USHORT Index = 0; Index < Dyndata->Count; Index++)",
    "ULONG Offset = Dyndata->Configs[Index];",
    "if (Offset < ConfigsEnd)",
    "EntryEnd = Offset + Dyndata->Size;",
    "if (EntryEnd < Offset || EntryEnd > DyndataSize)",
]:
    require(helper, term, "Dyndata_IsValidData")

init_macro = between(src, "#define INIT_DATA", "#define BEGIN_DATA")
pool = init_macro.index("Default = (PSBIE_DYNDATA)Pool_Alloc(Driver_Pool, DefaultSize);")
null_check = init_macro.index("if(!Default)")
clear = init_macro.index("memset(Default, 0x00, DefaultSize);")
if not (pool < null_check < clear):
    raise SystemExit("SREV-148 failed: INIT_DATA must check allocation before memset")
reject(init_macro, "Pool_Alloc(Driver_Pool, DefaultSize); \\\n    memset(Default", "stale allocation order")

load = between(src, "_FX NTSTATUS Dyndata_LoadData()", "//---------------------------------------------------------------------------\n// Dyndata_Init")
custom_valid = load.index("if (!Dyndata_IsValidData(Custom, CustomSize))")
format_read = load.index("Custom->Format != DYNDATA_FORMAT")
if not custom_valid < format_read:
    raise SystemExit("SREV-148 failed: custom Dyndata validation must precede header field reads")

selected_valid = load.index("if (!Dyndata_IsValidData(Dyndata, DyndataSize))")
iteration = load.index("for (USHORT Index = 0; Index < Dyndata->Count; Index++)")
if not selected_valid < iteration:
    raise SystemExit("SREV-148 failed: selected Dyndata validation must precede iteration")

for stale in [
    "if ((UCHAR*)Data > (UCHAR*)Dyndata + DyndataSize) continue;",
    "memset(Default, 0x00, DefaultSize); \\\n    if(!Default)",
]:
    reject(load + init_macro, stale, "stale Dyndata boundary")

for term in [
    "Sandboxie/core/drv/dyn_data.c",
    "Sandboxie/core/drv/dyn_data.h",
    "### SREV-148: DynData Registry Blob Boundary",
    "DYNDATA_REGISTRY_BLOB_BOUNDARY",
    "srev-148-dyndata-registry-blob-boundary.schema.json",
    "Dyndata_IsValidData",
    "GetRegValue",
    "KEY_VALUE_PARTIAL_INFORMATION",
    "SBIE_DYNDATA",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-148 schema/source gate passed")
