#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-286 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-286 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-286-snapshot-path-builder-tls-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-286 failed: schema is not draft-07")
if schema.get("id") != "SNAPSHOT_PATH_BUILDER_TLS_GATE":
    raise SystemExit("SREV-286 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/file_snapshots.c":
    raise SystemExit("SREV-286 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "File_MakeSnapshotPath owns snapshot path assembly into TMPL_NAME_BUFFER",
    "Dll_GetTlsNameBuffer output must be checked before wcsncpy or wcscpy writes into it",
    "Cur_Snapshot null and missing boxed prefix remain fail-closed builder inputs",
    "Callers may use the snapshot path only after the builder returns non-null",
    "SREV-196 owns the local TLS name-buffer allocation failure contract",
    "SREV-060 owns snapshot relocation copy-path conversion before this builder",
    "this SREV does not change snapshot traversal relocation policy prefix selection or File_Delete_v2 behavior",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/file_snapshots.c").read_text()
spec = (ROOT / "docs/plan/srev-286-snapshot-path-builder-tls-gate.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-286.md").read_text()
srev_060 = (ROOT / "docs/plan/ledger/srev-060.md").read_text()
srev_196 = (ROOT / "docs/plan/ledger/srev-196.md").read_text()
srev_196_spec = (ROOT / "docs/plan/srev-196-dll-tls-name-buffer-allocation-contract.md").read_text()

start = source.index("_FX WCHAR* File_MakeSnapshotPath(")
end = source.index("//---------------------------------------------------------------------------\n// File_FindSnapshotPath", start)
builder = source[start:end]

for term in [
    "if (!Cur_Snapshot)\n\t\treturn NULL;",
    "ULONG prefixLen = File_FindBoxPrefix(CopyPath);",
    "if (prefixLen == 0)\n\t\treturn NULL;",
    "WCHAR* TmplName = Dll_GetTlsNameBuffer(TlsData, TMPL_NAME_BUFFER,",
    "if (!TmplName)\n\t\treturn NULL;",
    "wcsncpy(TmplName, CopyPath, prefixLen + 1);",
    "wcscpy(TmplName + prefixLen + 1, File_Snapshot_Prefix);",
    "wcscpy(TmplName + prefixLen + 1 + File_Snapshot_PrefixLen, Cur_Snapshot->ID);",
    "wcscpy(TmplName + prefixLen + 1 + File_Snapshot_PrefixLen + Cur_Snapshot->IDlen, CopyPath + prefixLen);",
    "return TmplName;",
]:
    require(builder, term, "File_MakeSnapshotPath source")

if not builder.index("if (!TmplName)") < builder.index("wcsncpy(TmplName, CopyPath, prefixLen + 1);"):
    raise SystemExit("SREV-286 failed: TmplName gate does not precede first write")

reject(
    builder,
    "WCHAR* TmplName = Dll_GetTlsNameBuffer(TlsData, TMPL_NAME_BUFFER, (wcslen(CopyPath) + File_Snapshot_PrefixLen + FILE_MAX_SNAPSHOT_ID + 1) * sizeof(WCHAR));\n\n\twcsncpy(TmplName, CopyPath, prefixLen + 1);",
    "pre-gate TmplName write",
)

for term in [
    "WCHAR* TmplName = File_MakeSnapshotPath(Cur_Snapshot, CopyPath);\n\t\t\tif (!TmplName)\n\t\t\t\tbreak;",
    "WCHAR* TmplName = File_MakeSnapshotPath(Cur_Snapshot, CopyPath);\n\t\t\tif (!TmplName)\n\t\t\t\tbreak; // SREV-286: snapshot path publication unavailable",
]:
    require(source, term, "caller stop gate")

reject(source, "break; // something went wrong", "stale source comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SNAPSHOT_PATH_BUILDER_TLS_GATE",
    "TMPL_NAME_BUFFER",
    "Dll_GetTlsNameBuffer",
    "wcsncpy",
    "wcscpy",
    "SREV-196",
    "SREV-060",
]:
    require(spec, term, "spec")

for term in [
    "Dll_GetTlsNameBuffer",
    "never publish a failed name-buffer allocation",
    "failed name-buffer",
]:
    require(srev_196 + srev_196_spec, term, "SREV-196 adjacency")

for term in [
    "File Snapshot Relocation Copy Path Gate",
    "snapshot relocation",
    "File_GetName",
]:
    require(srev_060, term, "SREV-060 adjacency")

for term in [
    "### SREV-286: Snapshot Path Builder TLS Gate",
    "SNAPSHOT_PATH_BUILDER_TLS_GATE",
    "srev-286-snapshot-path-builder-tls-gate.schema.json",
    "Sandboxie/core/dll/file_snapshots.c",
    "File_MakeSnapshotPath",
    "TMPL_NAME_BUFFER",
    "SREV-196",
    "SREV-060",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-286 source gate passed")
