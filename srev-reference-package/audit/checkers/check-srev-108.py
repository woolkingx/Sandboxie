#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-108 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-108 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-108-epmapper-dynamic-port-scope-and-binding-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-108 failed: schema is not draft-07")
if schema.get("id") != "EPMAPPER_DYNAMIC_PORT_SCOPE_AND_BINDING_LIFETIME":
    raise SystemExit("SREV-108 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "caller process id maps to a sandbox box name",
    "RpcPortBindingIfId resolves through local RPC endpoint mapper inquiry",
    "RpcPortBindingSvc resolves through SCM service process id",
    "each successful RpcMgmtEpEltInqNextW binding handle is freed with RpcBindingFree",
    "RpcBindingToStringBindingW output is freed with RpcStringFreeW",
    "RpcMgmtEpEltInqDone deletes the inquiry context",
    "QueryServiceStatusEx with SC_STATUS_PROCESS_INFO",
    "SERVICE_STATUS_PROCESS carries dwProcessId",
    "process-id or global scope only",
    "process id 0 is the existing global dynamic-port compatibility path",
    "RpcPortFilter message ids are attached to the driver dynamic-port entry",
    "per-sandbox dynamic ports require a driver API schema extension",
    "must not be pretended in service-only code",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/svc/EpMapperServer.cpp").read_text()
api_defs = (ROOT / "Sandboxie/core/drv/api_defs.h").read_text()
driver = (ROOT / "Sandboxie/core/drv/ipc_port.c").read_text()
spec = (ROOT / "docs/plan/srev-108-epmapper-dynamic-port-scope-and-binding-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "PipeServer::GetCallerProcessId()",
    "SbieApi_QueryProcess(idProcess, boxname",
    "RpcPortBindingIfId",
    "RpcPortBindingSvc",
    "OpenSCManager(NULL, NULL, GENERIC_READ)",
    "OpenService(sc_handle, pwszServiceName, SERVICE_QUERY_STATUS | SERVICE_QUERY_CONFIG)",
    "SERVICE_STATUS_PROCESS service_status;",
    "QueryServiceStatusEx(svc_handle, SC_STATUS_PROCESS_INFO",
    "service_status.dwProcessId",
    "API_GET_DYNAMIC_PORT_FROM_PID",
    "RpcMgmtEpEltInqBegin(NULL, RPC_C_EP_MATCH_BY_IF, &ifidRequest, RPC_C_VERS_ALL",
    "RpcMgmtEpEltInqNextW(hContext, &ifidEndpoint, &hBinding, NULL, NULL)",
    "RpcBindingToStringBindingW(hBinding, &pwszPortName)",
    "RpcStringFreeW(&pwszPortName)",
    "RpcBindingFree(&hBinding)",
    "RpcMgmtEpEltInqDone(&hContext)",
    "API_OPEN_DYNAMIC_PORT",
    "(ULONG_PTR)0,",
    "RpcPortFilter",
    "API_OPEN_DYNAMIC_PORT has only process-id or global scope",
    "a driver/API schema extension rather than a service-only routing change",
    "Per-process or per-sandbox filtering requires a scoped dynamic-port key",
]:
    require(source, term, "EpMapperServer.cpp source shape")

loop_start = source.index("while ((status = RpcMgmtEpEltInqNextW")
loop_end = source.index("RpcMgmtEpEltInqDone(&hContext);", loop_start)
loop = source[loop_start:loop_end]

for term in [
    "RpcBindingToStringBindingW(hBinding, &pwszPortName)",
    "RpcStringFreeW(&pwszPortName)",
    "RpcBindingFree(&hBinding)",
    "if (rpl->h.status == STATUS_SUCCESS)",
    "break;",
]:
    require(loop, term, "endpoint inquiry loop")

if not (
    loop.index("RpcBindingToStringBindingW(hBinding, &pwszPortName)")
    < loop.index("RpcStringFreeW(&pwszPortName)")
    < loop.index("RpcBindingFree(&hBinding)")
    < loop.index("if (rpl->h.status == STATUS_SUCCESS)")
    < loop.index("break;")
):
    raise SystemExit("SREV-108 failed: endpoint inquiry lifetime order is wrong")

for stale in [
    "Todo: make it per sandbox instead",
    "Todo: Add per process ALPC message filter",
    "only for the one process. Todo",
]:
    reject(source, stale, "EpMapperServer.cpp")

api_block_start = api_defs.index("API_ARGS_BEGIN(API_OPEN_DYNAMIC_PORT_ARGS)")
api_block_end = api_defs.index("API_ARGS_CLOSE(API_OPEN_DYNAMIC_PORT_ARGS)", api_block_start)
api_block = api_defs[api_block_start:api_block_end]
for term in [
    "API_ARGS_FIELD(WCHAR*,port_name)",
    "API_ARGS_FIELD(HANDLE,process_id)",
    "API_ARGS_FIELD(WCHAR*,port_id)",
    "API_ARGS_FIELD(ULONG,filter_num)",
    "API_ARGS_FIELD(ULONG*,filter_ids)",
]:
    require(api_block, term, "API_OPEN_DYNAMIC_PORT_ARGS")
for forbidden in [
    "box",
    "sandbox",
    "session_id",
]:
    reject(api_block.lower(), forbidden, "API_OPEN_DYNAMIC_PORT_ARGS")

for term in [
    "IPC_DYNAMIC_PORT *Ipc_CreateDynamicPort",
    "port->FilterCount = FilterCount;",
    "memcpy(port->FilterIDs, FilterIDs",
    "_FX NTSTATUS Ipc_Api_OpenDynamicPort",
    "if (proc) // is caller sandboxed?",
    "PsGetCurrentProcessId() != Api_ServiceProcessId",
    "Ipc_Dynamic_Ports.pPortLock",
    "List_Insert_After(&Ipc_Dynamic_Ports.Ports",
    "if (pArgs->process_id.val != 0)",
    "Process_AddPath(proc, &proc->open_ipc_paths",
    "_FX NTSTATUS Ipc_CheckPortRequest_Dynamic",
    "_wcsicmp(Name->Name.Buffer, port->wstrPortName) == 0",
    "if (port->FilterCount > 0)",
    "Ipc_GetRpcMsgId(proc, port->wstrPortName",
    "if (port->FilterIDs[i] == uMsg)",
    "STATUS_ACCESS_DENIED",
]:
    require(driver, term, "ipc_port.c dynamic-port/filter topology")

for term in [
    "### SREV-108: EpMapper Dynamic Port Scope And Binding Lifetime",
    "EPMAPPER_DYNAMIC_PORT_SCOPE_AND_BINDING_LIFETIME",
    "srev-108-epmapper-dynamic-port-scope-and-binding-lifetime.schema.json",
    "RpcBindingFree",
    "API_OPEN_DYNAMIC_PORT",
    "Sandboxie/core/svc/EpMapperServer.cpp",
    "Sandboxie/core/drv/ipc_port.c",
]:
    require(ledger, term, "ledger")

print("SREV-108 schema/source gate passed")
