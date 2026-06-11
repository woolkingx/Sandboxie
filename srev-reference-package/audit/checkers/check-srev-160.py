#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-160 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-160 failed: {label} still contains {needle!r}")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


schema = json.loads(
    (ROOT / "docs/plan/srev-160-obj-object-type-table-bound.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-160 failed: schema is not draft-07")
if schema.get("id") != "OBJ_OBJECT_TYPE_TABLE_BOUND":
    raise SystemExit("SREV-160 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Obj_ObjectTypes is a fixed-capacity pointer table allocated by Obj_Init",
    "the table is consumed as a NULL-terminated list by session.c",
    "capacity includes one reserved sentinel slot",
    "Obj_AddObjectType is the only writer and must prove an empty payload slot exists before writing a new POBJECT_TYPE",
    "after each successful write the next slot remains NULL",
    "if no payload slot remains initialization fails closed with a logged status instead of overwriting the sentinel or adjacent pool memory",
    "does not change which object types Sandboxie recognizes object manager private probing ObQueryNameString name construction parse-proc hooks minifilter callbacks or session monitor semantics",
    "Linux source gate is not Windows runtime proof",
]:
    require(contracts, term, "schema")

header = (ROOT / "Sandboxie/core/drv/obj.h").read_text()
source = (ROOT / "Sandboxie/core/drv/obj.c").read_text()
session = (ROOT / "Sandboxie/core/drv/session.c").read_text()
spec = (ROOT / "docs/plan/srev-160-obj-object-type-table-bound.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-160.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "extern POBJECT_TYPE *Obj_ObjectTypes;",
    "POBJECT_TYPE Obj_GetTypeObjectType(void);",
]:
    require(header, term, "obj.h")

for term in [
    "#define OBJ_OBJECT_TYPES_CAPACITY 10",
    "#define OBJ_OBJECT_TYPES_MAX      (OBJ_OBJECT_TYPES_CAPACITY - 1)",
    "sizeof(POBJECT_TYPE) * OBJ_OBJECT_TYPES_CAPACITY",
]:
    require(source, term, "obj.c named capacity")
reject(source, "sizeof(POBJECT_TYPE) * 10", "literal object-type allocation")

obj_init = section(source, "_FX BOOLEAN Obj_Init(void)", "//---------------------------------------------------------------------------\n// Obj_Unload")
for term in [
    "Mem_AllocEx(",
    "sizeof(POBJECT_TYPE) * OBJ_OBJECT_TYPES_CAPACITY",
    "memzero(",
    "sizeof(POBJECT_TYPE) * OBJ_OBJECT_TYPES_CAPACITY",
    "Obj_AddObjectType(L\"Job\")",
    "Obj_AddObjectType(L\"Event\")",
    "Obj_AddObjectType(L\"Mutant\")",
    "Obj_AddObjectType(L\"Semaphore\")",
    "Obj_AddObjectType(L\"Section\")",
    "Obj_AddObjectType(L\"SymbolicLink\")",
]:
    require(obj_init, term, "Obj_Init")
if "Obj_AddObjectType(L\"ALPC Port\")" not in obj_init and "Obj_AddObjectType(L\"Port\")" not in obj_init:
    raise SystemExit("SREV-160 failed: Obj_Init does not add a port object type")

obj_add = section(source, "_FX BOOLEAN Obj_AddObjectType", "\n}\n")
for term in [
    "for (i = 0; i < OBJ_OBJECT_TYPES_MAX && Obj_ObjectTypes[i]; ++i)",
    "if (i >= OBJ_OBJECT_TYPES_MAX) {",
    "Log_Status_Ex(\n            MSG_OBJ_HOOK_ANY_PROC, 0x96, STATUS_BUFFER_OVERFLOW, TypeName);",
    "return FALSE;",
    "Obj_ObjectTypes[i] = object;",
    "Obj_ObjectTypes[i + 1] = NULL;",
]:
    require(obj_add, term, "Obj_AddObjectType")
reject(obj_add, "for (i = 0; Obj_ObjectTypes[i]; ++i)", "unbounded object-type scan")
if obj_add.index("if (i >= OBJ_OBJECT_TYPES_MAX)") > obj_add.index("Obj_ObjectTypes[i] = object;"):
    raise SystemExit("SREV-160 failed: capacity gate is after object-type write")
if obj_add.index("Obj_ObjectTypes[i] = object;") > obj_add.index("Obj_ObjectTypes[i + 1] = NULL;"):
    raise SystemExit("SREV-160 failed: sentinel refresh is before payload write")

for term in [
    "for (i = 0; Obj_ObjectTypes[i]; ++i)",
    "STATUS_OBJECT_TYPE_MISMATCH",
    "ObReferenceObjectByName(",
]:
    require(session, term, "session consumer")

for term in [
    "### SREV-160: Obj Object Type Table Bound",
    "OBJ_OBJECT_TYPE_TABLE_BOUND",
    "srev-160-obj-object-type-table-bound.schema.json",
    "Sandboxie/core/drv/obj.h",
    "Sandboxie/core/drv/obj.c",
    "Sandboxie/core/drv/session.c",
    "Obj_ObjectTypes",
    "OBJ_OBJECT_TYPES_CAPACITY",
    "OBJ_OBJECT_TYPES_MAX",
    "STATUS_BUFFER_OVERFLOW",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-160 schema/source gate passed")
