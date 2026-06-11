#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-326/327 capture failed: {label} missing {needle!r}")


playbook = (ROOT / "docs/plan/srev-326-327-secure-runtime-capture-playbook.md").read_text()
schema = json.loads(
    (ROOT / "docs/plan/srev-326-327-secure-runtime-capture.schema.json").read_text()
)
srev326 = (ROOT / "docs/plan/srev-326-secure-bits-wuau-accesscheck-bypass.md").read_text()
srev327 = (ROOT / "docs/plan/srev-327-secure-appinfo-binding-handle-layout-probe.md").read_text()
check326 = (ROOT / "docs/plan/check-srev-326.py").read_text()
check327 = (ROOT / "docs/plan/check-srev-327.py").read_text()

if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-326/327 capture failed: schema is not draft-07")
if schema.get("id") != "SECURE_RUNTIME_CAPTURE_EVIDENCE":
    raise SystemExit("SREV-326/327 capture failed: wrong schema id")

for term in [
    "official API shape -> Windows runtime capture -> local compatibility decision",
    "local allowlist/probe works once -> official semantics are satisfied",
    "feature path: `accesscheck-bypass`",
    "feature path: `appinfo-binding-probe`",
    "MAXIMUM_ALLOWED",
    "GenericAll",
    "GrantedAccess",
    "AccessStatus",
    "LastError",
    "BindingHandle value class",
    "RpcBindingInqObject",
    "object UUID",
    "guard-before-`memcmp` proof",
    "Non-allowlisted caller using same hook",
    "Non-AppInfo async RPC",
]:
    require(playbook, term, "playbook")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-accesscheckbytype",
    "https://learn.microsoft.com/en-us/windows/win32/rpc/binding-handles",
    "https://learn.microsoft.com/en-us/windows/win32/api/rpcasync/ns-rpcasync-rpc_async_state",
    "https://learn.microsoft.com/en-us/windows/win32/api/rpcdce/nf-rpcdce-rpcbindinginqobject",
]:
    require(playbook, term, "playbook official reference")

schema_text = json.dumps(schema, sort_keys=True)
for term in [
    "record_id",
    "windows_build",
    "architecture",
    "sandboxie_commit",
    "feature_path",
    "accesscheck-bypass",
    "appinfo-binding-probe",
    "route_result",
    "native-forward",
    "real-token-forward",
    "probe-exception",
    "caller_class",
    "sandboxie-bits",
    "sandboxie-wuau",
    "wuauclt",
    "non-allowlisted",
    "desired_access",
    "generic_mapping",
    "security_descriptor_class",
    "object-type-specific",
    "token_shape",
    "native_ran",
    "granted_access",
    "access_status",
    "last_error",
    "call_path",
    "async_state_size",
    "binding_value_class",
    "rpc_binding_inq_object_status",
    "rpc_binding_object_uuid",
    "official_object_uuid_result",
    "small-handle-like",
    "readable-local-pointer",
    "unreadable-pointer",
    "rpc-handle-like-opaque",
    "offset_of_binding_guid",
    "guard_fired_before_memcmp",
    "appinfo_call_identity",
]:
    require(schema_text, term, "schema")

for term in [
    "Runtime Verification Matrix",
    "Windows gate: run the runtime verification matrix above before release.",
    "non-allowlisted callers plus deny-descriptor cases",
]:
    require(srev326, term, "SREV-326 adjacency")
    require(check326, term, "SREV-326 checker adjacency")

for term in [
    "Runtime Capture Matrix",
    "Windows gate: capture AppInfo UAC elevation calls",
    "RpcBindingInqObject",
    "non-AppInfo async RPC call",
    "unreadable page at the binding pointer",
]:
    require(srev327, term, "SREV-327 adjacency")
    require(check327, term, "SREV-327 checker adjacency")

print("SREV-326/327 secure runtime capture gate passed")
