#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-314 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-314 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-314-nsi-network-change-notification-shim.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-314 failed: schema is not draft-07")
if schema.get("id") != "NSI_NETWORK_CHANGE_NOTIFICATION_SHIM":
    raise SystemExit("SREV-314 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/custom.c":
    raise SystemExit("SREV-314 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "private winnsi compatibility result mapping",
    "public network-change notification ownership belongs to documented NetIO/IP Helper APIs",
    "calls the native NsiRpcRegisterChangeNotification export before mapping results",
    "only EPT_S_NOT_REGISTERED may be translated to NO_ERROR",
    "every other native RPC_STATUS must pass through unchanged",
    "comments and proof only",
]:
    require(contracts, term, "schema")

custom = (ROOT / "Sandboxie/core/dll/custom.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
dll_h = (ROOT / "Sandboxie/core/dll/dll.h").read_text()
spec = (ROOT / "docs/plan/srev-314-nsi-network-change-notification-shim.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-314.md").read_text()

for term in [
    "{ L\"winnsi.dll\",            NsiRpc_Init,                    0}, // SREV-314: private NSI network-change notification shim",
    "BOOLEAN NsiRpc_Init(HMODULE);",
]:
    require(ldr + dll_h, term, "loader registration")

init_start = custom.index("_FX BOOLEAN NsiRpc_Init(HMODULE module)")
init_end = custom.index("//  SREV-314:", init_start)
init = custom[init_start:init_end]
for term in [
    "Ldr_GetProcAddrNew(DllName_winnsi, L\"NsiRpcRegisterChangeNotification\", \"NsiRpcRegisterChangeNotification\");",
    "SBIEDLL_HOOK(NsiRpc_, NsiRpcRegisterChangeNotification);",
    "return TRUE;",
]:
    require(init, term, "NsiRpc_Init")

func_start = custom.index("_FX RPC_STATUS NsiRpc_NsiRpcRegisterChangeNotification(")
func_end = custom.index("//---------------------------------------------------------------------------\n// Nsi_Init", func_start)
func = custom[func_start:func_end]
for term in [
    "RPC_STATUS ret = __sys_NsiRpcRegisterChangeNotification(p1, p2, p3, p4, p5, p6, p7);",
    "if (EPT_S_NOT_REGISTERED == ret)",
    "ret = NO_ERROR;",
    "return ret;",
]:
    require(func, term, "NsiRpc_NsiRpcRegisterChangeNotification")

native = func.index("__sys_NsiRpcRegisterChangeNotification")
map_gate = func.index("if (EPT_S_NOT_REGISTERED == ret)", native)
success = func.index("ret = NO_ERROR;", map_gate)
ret = func.index("return ret;", success)
if not native < map_gate < success < ret:
    raise SystemExit("SREV-314 failed: native-call/map/pass-through ordering is wrong")

comment_start = custom.index("//  SREV-314:")
comment = custom[comment_start:func_start]
for term in [
    "WinINet can register network-change notifications",
    "private winnsi NsiRpcRegisterChangeNotification export",
    "Sandboxie does not",
    "own the NSI service notification topology",
    "endpoint-mapper",
    "NO_ERROR",
    "every other native result passes",
]:
    require(comment, term, "source comment")

for stale in [
    "WININET workaround",
    "The fix can be either",
    "We choose Fix 2",
    "I am not sure",
]:
    reject(ldr + comment, stale, "old NSI comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "NSI_NETWORK_CHANGE_NOTIFICATION_SHIM",
    "EPT_S_NOT_REGISTERED becomes NO_ERROR",
    "every other result passes through unchanged",
    "No hook registration condition, export name, native call",
    "Runtime gate: Windows WinINet/NSI smoke",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-314: NSI Network Change Notification Shim",
    "NSI_NETWORK_CHANGE_NOTIFICATION_SHIM",
    "srev-314-nsi-network-change-notification-shim.schema.json",
    "Sandboxie/core/dll/custom.c",
    "NsiRpc_NsiRpcRegisterChangeNotification",
    "NsiRpcRegisterChangeNotification",
    "EPT_S_NOT_REGISTERED",
    "NO_ERROR",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-314 source gate passed")
