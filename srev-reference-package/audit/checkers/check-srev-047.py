#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-047 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-047 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-047-key-low-label-boxed-path.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-047 failed: schema is not draft-07")
if schema.get("id") != "KEY_LOW_LABEL_BOXED_PATH":
    raise SystemExit("SREV-047 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "path_len is a byte count",
    "kernel-owned NUL-terminated buffer",
    "embedded NUL inside the counted path payload is invalid",
    "key sandbox root, not the file sandbox root",
    "Box_IsBoxedPath(proc->box, key, path) is true",
    "out-of-box registry-key paths are denied",
]:
    require(contracts, term, "schema")

for term in [
    "path_len",
    "path_str",
    "boxed_key_path",
]:
    require("\n".join(schema["properties"].keys()), term, "draft-07 properties")

src = (ROOT / "Sandboxie/core/drv/key.c").read_text()
spec = (ROOT / "docs/plan/srev-047-key-low-label-boxed-path.md").read_text()
ledger = read_combined_ledger(ROOT)

start = src.index("_FX NTSTATUS Key_Api_SetLowLabel(")
end = src.index("// Key_MountHive", start) if "// Key_MountHive" in src[start:] else src.index("\n}", start) + 2
low_label = src[start:end]

for term in [
    "path_len = args->path_len.val;",
    "if ((path_len & 1) || (! path_len) || (path_len > 512 * sizeof(WCHAR)))",
    "path = Mem_Alloc(proc->pool, path_len + sizeof(WCHAR));",
    "if (! path)",
    "for (i = 0; i < path_len / sizeof(WCHAR); ++i)",
    "if (path[i] == L'\\0')",
    "status = STATUS_INVALID_PARAMETER;",
    "goto finish;",
    "if (Box_IsBoxedPath(proc->box, key, &objname))",
    "status = STATUS_ACCESS_DENIED;",
    "ZwOpenKey(&handle, KEY_ALL_ACCESS | WRITE_DAC, &objattrs);",
    "ZwSetSecurityObject(handle,",
    "finish:",
    "Mem_Free(path, path_len + sizeof(WCHAR));",
]:
    require(low_label, term, "Key_Api_SetLowLabel")

for term in [
    "path_len = args->path_len.val & ~1;",
    "Box_IsBoxedPath(proc->box, file, &objname)",
    "if (! Box_IsBoxedPath",
    "Mem_Free(path, path_len + 8);",
]:
    reject(low_label, term, "Key_Api_SetLowLabel")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwopenkey",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwsetsecurityobject",
    "srev-047-key-low-label-boxed-path.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-047: Key Low-Label Boxed Path",
    "KEY_LOW_LABEL_BOXED_PATH",
    "srev-047-key-low-label-boxed-path.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-047 schema/source gate passed")
