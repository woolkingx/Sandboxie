#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-181 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-181 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-181 failed: {label}")


def function_slice(text: str, start: str, end: str) -> str:
    s = text.index(start)
    e = text.index(end, s)
    return text[s:e]


schema = json.loads((ROOT / "docs/plan/srev-181-box-name-fixed-buffer-boundary.schema.json").read_text())
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-181 failed: schema is not draft-07")
if schema.get("id") != "BOX_NAME_FIXED_BUFFER_BOUNDARY":
    raise SystemExit("SREV-181 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "box.c owns writes into BOX.name",
    "BOX.name has exactly BOXNAME_COUNT WCHAR slots",
    "Box_IsValidName is the local semantic schema",
    "rejects NULL or invalid box names before allocating owner state",
    "bounded API that receives BOXNAME_COUNT",
    "frees any allocated BOX if the bounded copy fails",
    "Api_CopyBoxNameFromUser is useful but is not the owner boundary",
]:
    require(contracts, term, "schema contracts")

box_c = (ROOT / "Sandboxie/core/drv/box.c").read_text()
box_h = (ROOT / "Sandboxie/core/drv/box.h").read_text()
api_c = (ROOT / "Sandboxie/core/drv/api.c").read_text()
process_api = (ROOT / "Sandboxie/core/drv/process_api.c").read_text()
process_force = (ROOT / "Sandboxie/core/drv/process_force.c").read_text()
driver_h = (ROOT / "Sandboxie/core/drv/driver.h").read_text()
spec = (ROOT / "docs/plan/srev-181-box-name-fixed-buffer-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-181.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

box_alloc = function_slice(
    box_c,
    "_FX BOX *Box_Alloc",
    "//---------------------------------------------------------------------------\n// Box_Free",
)

for term in [
    "WCHAR name[BOXNAME_COUNT];",
    "ULONG name_len;",
    "WCHAR *sid;",
    "ULONG session_id;",
]:
    require(box_h, term, "box.h identity shape")

for term in [
    "#define NTSTRSAFE_LIB",
    "#include <ntstrsafe.h>",
]:
    require(driver_h, term, "driver safe-string include")

for term in [
    "NTSTATUS status;",
    "if ((! boxname) || (! Box_IsValidName(boxname)))",
    "STATUS_INVALID_PARAMETER",
    "boxname ? L\"(invalid)\" : L\"(null)\"",
    "box = Mem_Alloc(pool, sizeof(BOX));",
    "memzero(box, sizeof(BOX));",
    "status = RtlStringCchCopyW(box->name, BOXNAME_COUNT, boxname);",
    "if (! NT_SUCCESS(status))",
    "Box_Free(box);",
    "return NULL;",
    "box->name_len = (wcslen(box->name) + 1) * sizeof(WCHAR);",
]:
    require(box_alloc, term, "Box_Alloc source shape")

reject(box_alloc, "wcscpy(box->name, boxname);", "direct fixed-buffer wcscpy")
assert_before(box_alloc, "name gate before allocation", "Box_IsValidName(boxname)", "box = Mem_Alloc")
assert_before(box_alloc, "bounded copy after zeroing", "memzero(box, sizeof(BOX));", "RtlStringCchCopyW")
assert_before(box_alloc, "copy failure before name_len", "if (! NT_SUCCESS(status))", "box->name_len")

for term in [
    "if (name[i] >= L'0' && name[i] <= L'9')",
    "if (name[i] >= L'A' && name[i] <= L'Z')",
    "if (name[i] >= L'a' && name[i] <= L'z')",
    "if (name[i] == L'_')",
    "if (i == 0 || name[i])",
]:
    require(box_c, term, "Box_IsValidName semantic schema")

for term in [
    "if (boxname34[0] && Box_IsValidName(boxname34))",
    "box = Box_CreateEx(",
]:
    require(api_c + process_api, term, "API caller evidence")

for term in [
    "box->box = Box_CreateEx(",
    "Conf_IsBoxEnabled(section, SidString, SessionId)",
]:
    require(process_force, term, "force caller evidence")

for term in [
    "should be used instead of `wcscpy`",
    "destination buffer of a specified character length",
    "Box_Alloc now rejects `NULL` or invalid box names before allocation",
    "No valid box-name character set",
]:
    require(spec, term, "spec shape")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-181",
    "owner: Sandboxie/core/drv/box.c",
    "checker: docs/plan/check-srev-181.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-181: Box Name Fixed Buffer Boundary",
    "BOX_NAME_FIXED_BUFFER_BOUNDARY",
    "Sandboxie/core/drv/box.c",
    "Sandboxie/core/drv/box.h",
    "Box_Alloc",
    "RtlStringCchCopyW",
    "Api_CopyBoxNameFromUser",
]:
    require(ledger, term, "ledger")

print("SREV-181 schema/source gate passed")
