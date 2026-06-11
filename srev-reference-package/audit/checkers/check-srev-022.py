#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-022 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-022 failed: stale {label} remains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-022-font-token-subject-context.schema.json").read_text())
if schema.get("id") != "FONT_TOKEN_SUBJECT_CONTEXT_SHAPE":
    raise SystemExit("SREV-022 failed: schema missing FONT_TOKEN_SUBJECT_CONTEXT_SHAPE")
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-022 failed: schema is not draft-07")

contracts = "\n".join(schema["contracts"])
for term in [
    "Token reference behavior must not change until Windows runtime proves both font compatibility and reference ownership",
    "default FontTokenMode auto scoped path must restore and dereference",
    "FontTokenMode legacy preserves the old unscoped compatibility behavior",
    "FontTokenMode strict or off disables the unsupported subject-context rewrite",
    "minifilter IRP_MJ_CREATE must pass FILE_FONT_TOKEN_SWAP through CompletionContext",
    "legacy XP parse-proc must wrap the system parse continuation",
    "Source comments must not describe the active path as replacing PrimaryToken in ACCESS_STATE",
    "runtime capture must prove who owns the substituted token reference",
    "shared kernel runtime capture records must use feature_path font-token-subject-context",
]:
    require(contracts, term, "schema")

matrix = "\n".join(
    "\n".join(value) if isinstance(value, list) else str(value)
    for value in schema["runtime_capture_matrix"].values()
)
for term in [
    "supported Windows 10 releases",
    "supported Windows 11 releases",
    "XP or Server 2003 target",
    "minifilter IRP_MJ_CREATE path through file_flt.c",
    "legacy XP parse-proc path through file_xp.c",
    "kernel-mode win32k delayed font open",
    "user-mode file open negative control",
    "active impersonation negative control",
    "non-sandboxed process negative control",
    "exact font read/execute mask",
    "denied write/delete mask",
    "real %SystemRoot%\\Fonts path",
    "sandbox-boxed font path from the GDI helper",
    "reparse or symlinked font path",
    "proc->primary_token pointer",
    "object reference delta before and after create path",
    "ClientToken field selected",
    "PrimaryToken fallback selected",
    "downstream release or no-release observation",
    "Digital Guardian or equivalent callback-sensitive endpoint regression",
    "token reference count",
    "driver unload readback",
]:
    require(matrix, term, "schema runtime capture matrix")

src = (ROOT / "Sandboxie/core/drv/file.c").read_text()
flt = (ROOT / "Sandboxie/core/drv/file_flt.c").read_text()
xp = (ROOT / "Sandboxie/core/drv/file_xp.c").read_text()
spec = (ROOT / "docs/plan/srev-022-font-token-subject-context.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "SREV-022: this compatibility path handles delayed kernel-mode font",
    "substitutes the sandbox process's saved original token into the",
    "subject context for this access check.",
    "ACCESS_STATE and SECURITY_SUBJECT_CONTEXT fields are system-owned DDI",
    "internals, so this remains a runtime-gated compatibility path rather",
    "than a supported ownership contract.",
    "typedef struct _FILE_FONT_TOKEN_SWAP",
    "FileFontTokenMode_Scoped",
    "FontTokenMode",
    "FileFontTokenMode_Legacy",
    "FileFontTokenMode_Off",
    "SREV-022: default to a scoped compatibility fallback.",
    "FontTokenMode=legacy keeps the old unscoped behavior",
    "ObReferenceObject(proc->primary_token)",
    "AccessState->SubjectSecurityContext.ClientToken = proc->primary_token",
    "File_RestoreTokenIfFontRequest",
    "ObDereferenceObject(Swap->ReferencedToken)",
    "Mem_Free(Swap, sizeof(FILE_FONT_TOKEN_SWAP));",
    "*pbSetDirty = TRUE",
]:
    require(src, term, "driver source")

for term in [
    "FILE_CALLBACK_WITH_POST(IRP_MJ_CREATE)",
    "File_PostOperation",
    "FILE_FONT_TOKEN_SWAP *FontTokenSwap = NULL;",
    "FontTokenSwap = File_ReplaceTokenIfFontRequest(",
    "*CompletionContext = FontTokenSwap;",
    "return FLT_PREOP_SUCCESS_WITH_CALLBACK;",
    "File_RestoreTokenIfFontRequest((FILE_FONT_TOKEN_SWAP *)CompletionContext);",
    "FLT_POSTOP_FINISHED_PROCESSING",
]:
    require(flt, term, "minifilter source")

for term in [
    "FILE_FONT_TOKEN_SWAP *FontTokenSwap = NULL;",
    "FontTokenSwap = File_ReplaceTokenIfFontRequest(",
    "File_Device_NtParseProc(",
    "File_RestoreTokenIfFontRequest(FontTokenSwap);",
    "return status;",
]:
    require(xp, term, "XP parse-proc source")

font_start = src.index("_FX FILE_FONT_TOKEN_SWAP *File_ReplaceTokenIfFontRequest(")
font_end = src.index("// File_Api_Rename", font_start)
font_func = src[font_start:font_end]
for stale in [
    "$Workaround$ - 3rd party fix",
    "HACK ALERT! this causes a resource leak",
    "to work around this",
    "replace the PrimaryToken in the ACCESS_STATE",
]:
    reject(font_func, stale, "font token source comment")

for term in [
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobject",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_access_state",
    "https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_security_subject_context",
    "Do not blind-patch",
    "scoped fallback",
    "FontTokenMode=legacy",
    "FontTokenMode=strict/off",
    "File_RestoreTokenIfFontRequest",
    "minifilter post-create",
    "legacy XP parse-proc wrapper",
    "Runtime Capture Matrix",
    "Shared Runtime Capture Evidence",
    "srev-022-027-kernel-runtime-capture-playbook.md",
    "srev-022-027-kernel-runtime-capture.schema.json",
    "font-token-subject-context",
    "Windows gate: validate captured font-token records",
    "downstream security/file-system path",
    "Digital Guardian or equivalent callback-sensitive endpoint",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-022: Font Token Subject Context Rewrite Has Unsupported Ownership Shape",
    "patched source-level scoped font-token fallback",
    "needs Windows runtime proof",
    "Runtime Capture Matrix",
    "concrete runtime capture matrix",
]:
    require(ledger, term, "ledger")

print("SREV-022 schema/source gate passed")
