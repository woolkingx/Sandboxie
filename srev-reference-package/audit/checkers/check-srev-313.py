#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-313 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-313 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-313-hnet-firewall-dynamic-port-shim.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-313 failed: schema is not draft-07")
if schema.get("id") != "HNET_FIREWALL_DYNAMIC_PORT_SHIM":
    raise SystemExit("SREV-313 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/netapi.c":
    raise SystemExit("SREV-313 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "private hnetcfg compatibility shim",
    "host Windows Firewall policy mutation belongs to Windows Firewall COM policy owners",
    "reports S_OK success without calling the native IcfOpenDynamicFwPort export",
    "HNet_Init may hook IcfOpenDynamicFwPort only when hnetcfg.dll exports it",
    "comments and HRESULT spelling only",
]:
    require(contracts, term, "schema")

netapi = (ROOT / "Sandboxie/core/dll/netapi.c").read_text()
ldr = (ROOT / "Sandboxie/core/dll/ldr.c").read_text()
spec = (ROOT / "docs/plan/srev-313-hnet-firewall-dynamic-port-shim.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-313.md").read_text()

for term in [
    "{ L\"hnetcfg.dll\",           HNet_Init,                      0}, // SREV-313: private hnetcfg firewall dynamic-port shim",
    "BOOLEAN HNet_Init(HMODULE);",
]:
    require(ldr + (ROOT / "Sandboxie/core/dll/dll.h").read_text(), term, "loader registration")

func_start = netapi.index("_FX HRESULT HNet_IcfOpenDynamicFwPort(")
func_end = netapi.index("//---------------------------------------------------------------------------\n// HNet_Init", func_start)
func = netapi[func_start:func_end]

for term in [
    "SREV-313: Winsock bind may call the private hnetcfg export",
    "Sandboxie does not own host Windows Firewall",
    "policy mutation",
    "report local success without opening a firewall",
    "return S_OK;",
]:
    require(func, term, "HNet_IcfOpenDynamicFwPort")

reject(func, "return 0;", "literal HRESULT success")
reject(func, "__sys_IcfOpenDynamicFwPort(", "native firewall call inside shim")

init_start = netapi.index("_FX BOOLEAN HNet_Init(HMODULE module)")
init_end = netapi.index("//---------------------------------------------------------------------------\n//\n// Network Shares", init_start)
init = netapi[init_start:init_end]

for term in [
    "GetProcAddress(module, \"IcfOpenDynamicFwPort\");",
    "if (IcfOpenDynamicFwPort) {",
    "SBIEDLL_HOOK(HNet_,IcfOpenDynamicFwPort);",
    "return TRUE;",
]:
    require(init, term, "HNet_Init")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "HNET_FIREWALL_DYNAMIC_PORT_SHIM",
    "S_OK",
    "Windows Firewall policy",
    "No hook registration condition, export name, native-call suppression",
    "Runtime gate: Windows bind/firewall smoke",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-313: HNet Firewall Dynamic Port Shim",
    "HNET_FIREWALL_DYNAMIC_PORT_SHIM",
    "srev-313-hnet-firewall-dynamic-port-shim.schema.json",
    "Sandboxie/core/dll/netapi.c",
    "HNet_IcfOpenDynamicFwPort",
    "IcfOpenDynamicFwPort",
    "S_OK",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-313 source gate passed")
