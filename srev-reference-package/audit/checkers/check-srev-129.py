#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-129 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-129 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-129-netapi-useadd-auth-identity-length-gate.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-129 failed: schema is not draft-07")
if schema.get("id") != "NETAPI_USEADD_AUTH_IDENTITY_LENGTH_GATE":
    raise SystemExit("SREV-129 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "UseAdd validates every NETAPI_USE_ADD_REQ wire field before PipeServer::ImpersonateCaller or NetUseAdd can run",
    "ui4_auth_identity_length uses the NETAPI_USE_ADD_REQ fixed 2048 byte wire buffer limit",
    "ui4_auth_identity_length equal to ULONG -1 remains the null auth identity sentinel",
    "ui4_auth_identity_length greater than 2048 sets ERROR_INVALID_PARAMETER and exits before impersonation",
    "valid ui4_auth_identity bytes are locally terminated before USE_INFO_4 points at the wire buffer",
    "LaunchSlave still runs only after NetUseAdd succeeds",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/netapiserver.cpp").read_text()
wire = (ROOT / "Sandboxie/core/svc/netapiwire.h").read_text()
client = (ROOT / "Sandboxie/core/dll/netapi.c").read_text()
spec = (ROOT / "docs/plan/srev-129-netapi-useadd-auth-identity-length-gate.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "struct tagNETAPI_USE_ADD_REQ",
    "UCHAR   level;",
    "ULONG   ui4_auth_identity_length;",
    "UCHAR   ui4_auth_identity[2048+2];",
    "WCHAR   ui0_local[256+1];",
    "WCHAR   ui1_password[256+1];",
    "struct tagNETAPI_USE_ADD_RPL",
]:
    require(wire, term, "wire schema")

for term in [
    "_FX ULONG NetApi_NetUseAdd(",
    "if (info4->ui4_auth_identity_length > 2048)\n            goto abort;",
    "req->ui4_auth_identity_length = info4->ui4_auth_identity_length;",
    "memcpy(req->ui4_auth_identity, info4->ui4_auth_identity,",
    "req->ui4_auth_identity_length = -1;",
    "rpl = (NETAPI_USE_ADD_RPL *)SbieDll_CallServer(&req->h);",
]:
    require(client, term, "client request construction")

useadd = source[
    source.index("MSG_HEADER *NetApiServer::UseAdd"):
    source.index("// LaunchSlave")
]

for term in [
    "typedef struct _USE_INFO_4",
    "if (req->h.length != sizeof(NETAPI_USE_ADD_REQ))",
    "if (req->level > 4)",
    "if (req->ui4_auth_identity_length == -1) {\n            info4->ui4_auth_identity_length = 0;\n            info4->ui4_auth_identity = NULL;",
    "} else if (req->ui4_auth_identity_length > 2048)\n            error_code = ERROR_INVALID_PARAMETER;\n        else {",
    "req->ui4_auth_identity[req->ui4_auth_identity_length + 0] = 0;",
    "req->ui4_auth_identity[req->ui4_auth_identity_length + 1] = 0;",
    "info4->ui4_auth_identity = req->ui4_auth_identity;",
    "info4->ui4_auth_identity_length = req->ui4_auth_identity_length;",
    "if (error_code)\n        goto finish;",
    "if (parm_index) {\n        error_code = ERROR_INVALID_PARAMETER;\n        goto finish;\n    }",
    "error_code = PipeServer::ImpersonateCaller();",
    "error_code = NetUseAdd(NULL, req->level, (UCHAR *)&info, &parm_index);",
    "if (error_code == 0)\n        LaunchSlave(req->ui0_local_len, req->ui0_local);",
]:
    require(useadd, term, "NetApiServer::UseAdd")

if useadd.index("if (error_code)\n        goto finish;") > useadd.index("error_code = PipeServer::ImpersonateCaller();"):
    raise SystemExit("SREV-129 failed: error_code gate is after impersonation")
if useadd.index("if (error_code)\n        goto finish;") > useadd.index("error_code = NetUseAdd("):
    raise SystemExit("SREV-129 failed: error_code gate is after NetUseAdd")
if useadd.index("if (parm_index)") > useadd.index("error_code = PipeServer::ImpersonateCaller();"):
    raise SystemExit("SREV-129 failed: parm_index gate moved after impersonation")

reject(
    useadd,
    "} else if (req->ui4_auth_identity_length > 2048)\n            error_code = ERROR_INVALID_PARAMETER;\n        else {\n            req->ui4_auth_identity[req->ui4_auth_identity_length + 0] = 0;\n            req->ui4_auth_identity[req->ui4_auth_identity_length + 1] = 0;\n            info4->ui4_auth_identity = req->ui4_auth_identity;\n            info4->ui4_auth_identity_length = req->ui4_auth_identity_length;\n        }\n    }\n\n    if (parm_index)",
    "old ungated error_code path",
)

for term in [
    "### SREV-129: NetApi UseAdd Auth Identity Length Gate",
    "NETAPI_USEADD_AUTH_IDENTITY_LENGTH_GATE",
    "srev-129-netapi-useadd-auth-identity-length-gate.schema.json",
    "Sandboxie/core/svc/netapiserver.cpp",
    "Sandboxie/core/svc/netapiwire.h",
    "Sandboxie/core/dll/netapi.c",
    "NetApiServer::UseAdd",
    "NETAPI_USE_ADD_REQ",
    "ui4_auth_identity_length",
    "PipeServer::ImpersonateCaller",
    "NetUseAdd",
    "LaunchSlave",
]:
    require(ledger, term, "ledger")

print("SREV-129 schema/source gate passed")
