#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-069 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-069-sxs-actctx-temp-buffer-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-069 failed: schema is not draft-07")
if schema.get("id") != "SXS_ACTCTX_TEMP_BUFFER_GATE":
    raise SystemExit("SREV-069 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "CreateActCtxW receives an ACTCTXW pointer",
    "ACTCTXW lpSource is a null-terminated path string",
    "wmemcpy requires valid source and destination buffers",
    "args.Directory may be copied into only after Dll_AllocTemp returns a non-null buffer",
    "MySource may be passed to SbieDll_GetHandlePath only after Dll_AllocTemp returns a non-null buffer",
    "TruePath2 may receive a trailing-slash copy only after Dll_AllocTemp returns a non-null buffer",
    "fall through to the underlying CreateActCtxW owner",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/sxs.c").read_text()
spec = (ROOT / "docs/plan/srev-069-sxs-actctx-temp-buffer-gate.md").read_text()
ledger = read_combined_ledger(ROOT)

create_start = src.index("_FX HANDLE Sxs_CreateActCtxW(")
create_end = src.index("// Sxs_CreateActCtxW_Alt", create_start)
create_func = src[create_start:create_end]

alt_start = src.index("_FX HANDLE Sxs_CreateActCtxW_Alt(")
alt_end = src.index("// Sxs_QueryActCtxW", alt_start)
alt_func = src[alt_start:alt_end]

query2_start = src.index("_FX void Sxs_QueryActCtxW_2(")
query2_end = src.index("// Sxs_Init", query2_start)
query2_func = src[query2_start:query2_end]

for term in [
    "args.Directory = Dll_AllocTemp((len + 4) * sizeof(WCHAR));\n        if (! args.Directory) {\n            LastError = STATUS_INSUFFICIENT_RESOURCES;\n            goto finish;\n        }\n        wmemcpy(args.Directory, args.SourcePath, len + 1);",
]:
    require(create_func, term, "Sxs_CreateActCtxW source")

if create_func.index("if (! args.Directory)") > create_func.index("wmemcpy(args.Directory, args.SourcePath"):
    raise SystemExit("SREV-069 failed: args.Directory gate appears after copy")

for term in [
    "MySource = Dll_AllocTemp(sizeof(WCHAR) * 8192);\n            if (! MySource) {\n                CloseHandle(hFile);\n                goto skip_path_translation;\n            }",
    "status = SbieDll_GetHandlePath(hFile, MySource, &IsBoxedPath);",
    "skip_path_translation:",
    "hActCtx = __sys_CreateActCtxW(ActCtx);",
]:
    require(alt_func, term, "Sxs_CreateActCtxW_Alt source")

if alt_func.index("if (! MySource)") > alt_func.index("SbieDll_GetHandlePath(hFile, MySource"):
    raise SystemExit("SREV-069 failed: MySource gate appears after write")
if alt_func.index("skip_path_translation:") > alt_func.index("hActCtx = __sys_CreateActCtxW(ActCtx);"):
    raise SystemExit("SREV-069 failed: skip label does not fall through before system call")

for term in [
    "WCHAR *TruePath2 =\n                        Dll_AllocTemp((TruePath_len + 2) * sizeof(WCHAR));\n                    if (TruePath2) {\n                        wmemcpy(TruePath2, TruePath, TruePath_len);",
    "TruePath2[TruePath_len] = L'\\\\';",
    "TruePath2[TruePath_len + 1] = L'\\0';",
    "TruePath = TruePath2;",
]:
    require(query2_func, term, "Sxs_QueryActCtxW_2 source")

if query2_func.index("if (TruePath2)") > query2_func.index("wmemcpy(TruePath2, TruePath"):
    raise SystemExit("SREV-069 failed: TruePath2 gate appears after copy")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createactctxw",
    "https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-actctxw",
    "https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memcpy-wmemcpy?view=msvc-170",
    "srev-069-sxs-actctx-temp-buffer-gate.schema.json",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-069: SXS ActCtx Temp Buffer Gate",
    "SXS_ACTCTX_TEMP_BUFFER_GATE",
    "srev-069-sxs-actctx-temp-buffer-gate.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-069 schema/source gate passed")
