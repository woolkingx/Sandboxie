#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-299 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-299 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-299-ipc-createobjects-bootstrap-allocation-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-299 failed: schema is not draft-07")
if schema.get("id") != "IPC_CREATEOBJECTS_BOOTSTRAP_ALLOCATION_GATE":
    raise SystemExit("SREV-299 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/ipc.c":
    raise SystemExit("SREV-299 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Ipc_CreateObjects owns local bootstrap storage and dummy event handle cleanup",
    "buffer, BNOLINKS, buffer2, and GLOBAL must be allocation-proven before string writes",
    "the dummy event handle must be closed on normal and failure exits",
    "SbieApi_CreateDirOrLink owns the driver-side directory or symbolic-link creation request",
    "SREV-037 must accept the box-level BNOLINKS bootstrap auxiliary path without broadening normal IPC path creation",
    "the broader symbolic-link reparse design remains a separate runtime design gate",
]:
    require(contracts, term, "schema")

ipc = (ROOT / "Sandboxie/core/dll/ipc.c").read_text()
spec = (ROOT / "docs/plan/srev-299-ipc-createobjects-bootstrap-allocation-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-299.md").read_text()
srev_037 = "\n".join([
    (ROOT / "docs/plan/ledger/srev-037.md").read_text(),
    (ROOT / "docs/plan/srev-037-ipc-create-dir-link-wire.md").read_text(),
    (ROOT / "docs/plan/srev-037-ipc-create-dir-link-wire.schema.json").read_text(),
])

start = ipc.index("_FX void Ipc_CreateObjects(void)")
end = ipc.index("// Ipc_GetName", start)
func = ipc[start:end]

for term in [
    "HANDLE handle = NULL;",
    "Sbie_snwprintf(str, 64, SBIE_BOXED_ L\"DummyEvent_%d\", Dll_ProcessId);",
    "handle = CreateEvent(NULL, FALSE, FALSE, str);",
    "status = Ipc_GetName(handle, NULL, &TruePath, &CopyPath, NULL);",
    "NtClose(handle);\n    handle = NULL;",
    "if (handle)\n        NtClose(handle);",
]:
    require(func, term, "dummy event handle")

for term in [
    "SREV-299: the dummy event publishes the object-manager namespace path",
    "that Ipc_GetName maps into CopyPath. Symbolic-link reparse remains a",
    "separate design gate; this bootstrap owns allocation and handle cleanup",
    "before creating BNOLINKS, Global, Local, and Session object links.",
]:
    require(func, term, "source topology comment")

reject(func, "todo: fix-me: properly reparse symbolic links in IPC paths instead of creating dummy for everything", "Ipc_CreateObjects comment")

checks = [
    ("buffer = Dll_Alloc((wcslen(CopyPath) + 32) * sizeof(WCHAR));", "if (!buffer) {", "wcscpy(buffer, BNOLINKS);"),
    ("BNOLINKS  = Dll_Alloc((wcslen(CopyPath) + 32) * sizeof(WCHAR));", "if (!BNOLINKS) {", "wcscpy(BNOLINKS, CopyPath);"),
    ("buffer2 = Dll_Alloc((Dll_BoxIpcPathLen + 32) * sizeof(WCHAR));", "if (!buffer2) {", "wcscpy(buffer2, Dll_BoxIpcPath);"),
    ("GLOBAL  = Dll_Alloc((wcslen(buffer) + 32) * sizeof(WCHAR));", "if (!GLOBAL) {", "wcscpy(GLOBAL, buffer);"),
]
for alloc, gate, first_write in checks:
    require(func, alloc, "allocation")
    require(func, gate, "allocation gate")
    require(func, first_write, "first write")
    if not (func.index(alloc) < func.index(gate) < func.index(first_write)):
        raise SystemExit(f"SREV-299 failed: allocation gate ordering for {alloc}")

for term in [
    "status = STATUS_INSUFFICIENT_RESOURCES;",
    "errlvl = 61;",
    "errlvl = 62;",
    "errlvl = 63;",
    "errlvl = 64;",
    "status = SbieApi_CreateDirOrLink(CopyPath, NULL);",
    "wcscat(BNOLINKS, L\"\\\\BNOLINKS\");",
    "backslash = wcsrchr(BNOLINKS, L'\\\\');",
    "status = SbieApi_CreateDirOrLink(BNOLINKS, NULL);",
    "status = SbieApi_CreateDirOrLink(buffer, CopyPath);",
]:
    require(func, term, "Ipc_CreateObjects")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "IPC_CREATEOBJECTS_BOOTSTRAP_ALLOCATION_GATE",
    "SREV-037 owns the driver-side counted-string and boxed-path gate",
    "SREV-037 must accept the box-level BNOLINKS bootstrap auxiliary path",
    "The broader symbolic-link reparse design remains open",
]:
    require(spec, term, "spec")

for term in [
    "IPC_CREATE_DIR_OR_LINK_COUNTED_STRING",
    "objname must be boxed before creating the directory or symbolic link object",
    "target must be boxed before creating a symbolic link object",
    "a successful directory or symbolic link handle is either stored in Ipc_ObjDirs or closed before return",
]:
    require(srev_037, term, "SREV-037 adjacency")

for term in [
    "### SREV-299: IPC CreateObjects Bootstrap Allocation Gate",
    "IPC_CREATEOBJECTS_BOOTSTRAP_ALLOCATION_GATE",
    "srev-299-ipc-createobjects-bootstrap-allocation-gate.schema.json",
    "Sandboxie/core/dll/ipc.c",
    "Ipc_CreateObjects",
    "BNOLINKS",
    "Dll_BoxIpcPath",
    "SREV-037",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-299 source gate passed")
