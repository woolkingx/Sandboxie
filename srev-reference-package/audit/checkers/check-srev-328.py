#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-328 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-328 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-328 failed: schema is not draft-07")
if schema.get("id") != "SXS_RPCSS_ALT_CREATEACTCTX_TOPOLOGY":
    raise SystemExit("SREV-328 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/sxs.c":
    raise SystemExit("SREV-328 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "CreateActCtxW owns the final activation-context handle",
    "Sandboxie owns only the optional SXS service projection",
    "SandboxieRpcSs must not synchronously re-enter",
    "Sxs_UseAltCreateActCtx routes to native CreateActCtxW",
    "the *UseAltCreateActCtx* sentinel is a local topology gate",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

sxs = (ROOT / "Sandboxie/core/dll/sxs.c").read_text()
rpcss_sxs = (ROOT / "Sandboxie/apps/com/RpcSs/sxs.c").read_text()
spec = (ROOT / "docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-328.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

init_start = sxs.index("_FX BOOLEAN Sxs_InitKernel32(")
init_end = sxs.index("NtSetInformationThread = GetProcAddress", init_start)
init_func = sxs[init_start:init_end]

create_start = sxs.index("_FX HANDLE Sxs_CreateActCtxW(")
create_end = sxs.index("// Sxs_CreateActCtxW_Alt", create_start)
create_func = sxs[create_start:create_end]

alt_start = sxs.index("_FX HANDLE Sxs_CreateActCtxW_Alt(")
alt_end = sxs.index("// Sxs_QueryActCtxW", alt_start)
alt_func = sxs[alt_start:alt_end]

call_start = sxs.index("_FX void *Sxs_CallService(")
call_end = sxs.index("// Sxs_ActivationContextNotificationRoutine", call_start)
call_func = sxs[call_start:call_end]

for term in [
    "if (Sxs_UseAltCreateActCtx)\n        return Sxs_CreateActCtxW_Alt(ActCtx);",
    "BOOLEAN UseAltCreateActCtx = FALSE;",
    "void *MappedBase = Sxs_CallService(&args, &UseAltCreateActCtx);",
    "} else if (UseAltCreateActCtx) {",
    "hActCtx = Sxs_CreateActCtxW_Alt(ActCtx);",
]:
    require(create_func, term, "Sxs_CreateActCtxW source")

for term in [
    "SREV-328: in SandboxieRpcSs, avoid re-entering the in-sandbox SXS",
    "alternate path calls the native CreateActCtxW owner",
    "optional boxed-path translation",
    "recursion gate",
    "hActCtx = __sys_CreateActCtxW(ActCtx);",
    "++TlsData->proc_create_process;",
    "--TlsData->proc_create_process;",
]:
    require(alt_func, term, "Sxs_CreateActCtxW_Alt source")

reject(alt_func, "workaround:  in the context of RpcSs", "RpcSs SXS workaround label")
reject(alt_func, "use the real SXS from CSRSS", "CSRSS owner shortcut")

for term in [
    "if (Dll_ImageType == DLL_IMAGE_SANDBOXIE_RPCSS || Dll_AppContainerToken ||",
    "Config_GetSettingsForImageName_bool(L\"DisableBoxedWinSxS\", FALSE))",
    "Sxs_UseAltCreateActCtx = TRUE;",
]:
    require(init_func, term, "Sxs_Init source")

require(sxs, "static const WCHAR *Sxs_QueueName = L\"RPCSS_SXS\";", "core SXS queue name")

for term in [
    "STATUS_BAD_INITIAL_PC",
    "*UseAltCreateActCtx = TRUE;",
    "len2 == 20 && memcmp(buf2, \"*UseAltCreateActCtx*\", 20) == 0",
]:
    require(call_func, term, "Sxs_CallService source")

for term in [
    "static const WCHAR *Sxs_QueueName   = L\"RPCSS_SXS\";",
    "Sxs_Thread",
    "Sxs_Request(data_ptr, data_len, &rsp_data, &rsp_len);",
    "memcpy(data, \"*UseAltCreateActCtx*\", 20);",
    "Sxs_GenerateHelper(&args, LangNames);",
    "args->hSection = (HANDLE)(ULONG_PTR)-1;",
]:
    require(rpcss_sxs, term, "RpcSs SXS service source")

for term in [
    "SXS_RPCSS_ALT_CREATEACTCTX_TOPOLOGY",
    "No `Sxs_UseAltCreateActCtx` predicate",
    "Windows gate: SandboxieRpcSs startup",
    "not a general SXS policy bypass",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-328",
    "owner: Sandboxie/core/dll/sxs.c",
    "spec: docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.md",
    "schema: docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.schema.json",
    "checker: docs/plan/check-srev-328.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-328: SXS RpcSs Alt CreateActCtx Topology",
    "SXS_RPCSS_ALT_CREATEACTCTX_TOPOLOGY",
    "Sxs_CreateActCtxW_Alt",
    "RPCSS_SXS",
    "*UseAltCreateActCtx*",
]:
    require(ledger, term, "combined ledger")

print("SREV-328 schema/source gate passed")
