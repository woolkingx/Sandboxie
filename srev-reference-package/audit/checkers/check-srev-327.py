#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-327 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-327 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-327-secure-appinfo-binding-handle-layout-probe.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-327 failed: schema is not draft-07")
if schema.get("id") != "SECURE_APPINFO_BINDING_HANDLE_LAYOUT_PROBE":
    raise SystemExit("SREV-327 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/secure.c":
    raise SystemExit("SREV-327 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "official RPC binding handles are opaque RPC runtime objects",
    "RpcBindingInqObject is the supported first route",
    "RPC_ASYNC_STATE owns only the documented async state and notification shape",
    "Secure_CheckElevation uses RpcBindingInqObject first",
    "fallback layout probe must keep the small-handle guard",
    "OFFSET_OF_BINDING_GUID values are local evidence",
    "official object UUID query or fallback layout probe matched",
    "adds an official object UUID query path",
    "SREV-326 and SREV-327 share docs/plan/srev-326-327-secure-runtime-capture.schema.json",
]:
    require(contracts, term, "schema contracts")

matrix = "\n".join(
    "\n".join(value) if isinstance(value, list) else str(value)
    for value in schema["runtime_capture_matrix"].values()
)
for term in [
    "supported Windows 10 releases",
    "supported Windows 11 releases",
    "x64 process",
    "WOW64 process where supported",
    "type-1 process elevation",
    "type-2 token elevation",
    "RPC_ASYNC_STATE.Size",
    "NotificationType",
    "u.hEvent",
    "small real-handle-like value",
    "readable local pointer",
    "unreadable pointer",
    "official RPC handle-like value if observed",
    "RpcBindingInqObject status",
    "object UUID returned by RpcBindingInqObject",
    "official object UUID match or miss",
    "OFFSET_OF_BINDING_GUID",
    "__try exception code",
    "fallback guard fired before memcmp",
    "non-AppInfo async RPC call",
    "ordinary non-elevation RPC path",
]:
    require(matrix, term, "schema runtime capture matrix")

secure = (ROOT / "Sandboxie/core/dll/secure.c").read_text()
rpcrt = (ROOT / "Sandboxie/core/dll/rpcrt.c").read_text()
spec = (ROOT / "docs/plan/srev-327-secure-appinfo-binding-handle-layout-probe.md").read_text()
shared_playbook = (ROOT / "docs/plan/srev-326-327-secure-runtime-capture-playbook.md").read_text()
shared_schema = json.loads((ROOT / "docs/plan/srev-326-327-secure-runtime-capture.schema.json").read_text())
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-327.md").read_text()

if shared_schema.get("id") != "SECURE_RUNTIME_CAPTURE_EVIDENCE":
    raise SystemExit("SREV-327 failed: shared secure capture schema has wrong id")
require(shared_playbook, "Non-AppInfo async RPC", "shared capture playbook")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

start = secure.index("ALIGNED BOOLEAN __cdecl Secure_CheckElevation(")
end = secure.index("// Secure_HandleElevation", start)
func = secure[start:end]
helper_start = secure.index("static BOOLEAN Secure_IsElevationBindingGuid(")
helper_end = secure.index("// Secure_CheckElevation", helper_start)
helper = secure[helper_start:helper_end]

for term in [
    "typedef RPC_STATUS (RPC_ENTRY *P_RpcBindingInqObject)",
    "static P_RpcBindingInqObject        __sys_RpcBindingInqObject",
]:
    require(secure, term, "secure source declarations")

for term in [
    "GetProcAddress(module, \"RpcBindingInqObject\")",
    "__sys_RpcBindingInqObject(",
    "(RPC_BINDING_HANDLE)BindingHandle",
    "return (memcmp(&ObjectUuid, BindingGuid, 16) == 0);",
    "SREV-327: prefer the official RPC binding API.",
    "RpcBindingInqObject",
    "returns the object UUID associated with a binding handle",
    "compatibility fallback for observed",
    "ptr = (UCHAR *)BindingHandle;",
    "SREV-327 fallback: observed AppInfo binding layout probe",
    "not official",
    "Keep the small-handle guard before reading the local",
    "if (ptr < (UCHAR*)0x1fff)",
    "memcmp(ptr + BindingGuidOffset, BindingGuid, 16)",
]:
    require(helper, term, "Secure_IsElevationBindingGuid source")

guard = helper.index("if (ptr < (UCHAR*)0x1fff)")
memcmp_pos = helper.index("memcmp(ptr + BindingGuidOffset, BindingGuid, 16)")
if not guard < memcmp_pos:
    raise SystemExit("SREV-327 failed: fallback small-handle guard must precede binding GUID memcmp")

for term in [
    "const SIZEOF_RPC_ASYNC_STATE =  0x70;",
    "const OFFSET_OF_BINDING_GUID =  0x18;",
    "const SIZEOF_RPC_ASYNC_STATE =  0x44;",
    "const OFFSET_OF_BINDING_GUID =  0x10;",
    "if (! Args)",
    "AsyncState = Args->AsyncState;",
    "if (! AsyncState)",
    "if (AsyncState->Size != SIZEOF_RPC_ASYNC_STATE)",
    "if (AsyncState->NotificationType != RpcNotificationTypeEvent)",
    "if (!AsyncState->u.hEvent)",
    "Secure_IsElevationBindingGuid(",
    "Args->BindingHandle, elevation_binding_##n, OFFSET_OF_BINDING_GUID",
    "if (IS_BINDING_GUID(1))",
    "Secure_Elevation_Type = 1;",
    "Secure_Elevation_ResultHandle = Args->u.Args1.ProcessHandle;",
    "IS_BINDING_GUID(2_Vista) || IS_BINDING_GUID(2_Win7)",
    "Secure_Elevation_Type = 2;",
    "Secure_Elevation_ResultHandle = (HANDLE *)",
]:
    require(func, term, "Secure_CheckElevation source")

for stale in [
    "The name \"BindingHandle\" implies a handle.",
    "Windows 10 is passing in real handles sometimes.",
    "HACK to filter out handles",
]:
    reject(func, stale, "source BindingHandle comment")

for term in [
    "pStack[0] -> RPC_ASYNC_STATE",
    "return Secure_CheckElevation((struct SECURE_UAC_ARGS*)pStack);",
]:
    require(rpcrt, term, "RPCRT Secure_CheckElevation caller")

for term in [
    "SECURE_APPINFO_BINDING_HANDLE_LAYOUT_PROBE",
    "docs/plan/srev-326-327-secure-runtime-capture-playbook.md",
    "docs/plan/srev-326-327-secure-runtime-capture.schema.json",
    "RpcBindingInqObject",
    "official object UUID query",
    "fallback GUID probe result",
    "No async-state predicate, notification gate",
    "Windows gate: capture AppInfo UAC elevation calls",
    "docs/plan/check-srev-326-327-secure-runtime-capture.sh",
    "Runtime Capture Matrix",
    "non-AppInfo async RPC call",
    "unreadable page at the binding pointer",
    "not official RPC handle shape",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-327",
    "status: patched-source-level-with-rpc-binding-object-uuid-query-needs-windows-runtime-proof",
    "owner: Sandboxie/core/dll/secure.c",
    "spec: docs/plan/srev-327-secure-appinfo-binding-handle-layout-probe.md",
    "schema: docs/plan/srev-327-secure-appinfo-binding-handle-layout-probe.schema.json",
    "checker: docs/plan/check-srev-327.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-327: Secure AppInfo Binding Handle Layout Probe",
    "SECURE_APPINFO_BINDING_HANDLE_LAYOUT_PROBE",
    "Secure_CheckElevation",
    "RPC_ASYNC_STATE",
    "OFFSET_OF_BINDING_GUID",
    "Runtime Capture Matrix",
    "non-AppInfo async RPC",
]:
    require(ledger, term, "combined ledger")

print("SREV-327 schema/source gate passed")
