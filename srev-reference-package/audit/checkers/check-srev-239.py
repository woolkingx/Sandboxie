#!/usr/bin/env python3
import json
from pathlib import Path

from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-239 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-239 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-239-wfp-driver-header-topology.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-239 failed: schema is not draft-07")
if schema.get("id") != "WFP_DRIVER_HEADER_TOPOLOGY_CONTRACT":
    raise SystemExit("SREV-239 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/wfp.h":
    raise SystemExit("SREV-239 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "driver WFP module declaration header",
    "module lifecycle process entry points",
    "does not own WFP engine sessions BFE state callbacks callout sublayer filter registration",
    "Runtime behavior changes belong to wfp.c driver.c process.c file.c",
    "driver initialization process lifecycle settings refresh and WFP callout topology",
]:
    require(contracts, term, "schema contract")

spec = (ROOT / "docs/plan/srev-239-wfp-driver-header-topology.md").read_text()
header = (ROOT / "Sandboxie/core/drv/wfp.h").read_text()
wfp = (ROOT / "Sandboxie/core/drv/wfp.c").read_text()
driver = (ROOT / "Sandboxie/core/drv/driver.c").read_text()
process = (ROOT / "Sandboxie/core/drv/process.c").read_text()
file_source = (ROOT / "Sandboxie/core/drv/file.c").read_text()
srev027_spec = (ROOT / "docs/plan/srev-027-wfp-classify-logging-irql.md").read_text()
ledger = read_combined_ledger(ROOT)
fragment = (ROOT / "docs/plan/ledger/srev-239.md").read_text()

for term in [
    '#include "driver.h"',
    "BOOLEAN WFP_Init(void);",
    "BOOLEAN WFP_Load(void);",
    "void WFP_Unload(void);",
    "BOOLEAN WFP_InitProcess(PROCESS *proc);",
    "BOOLEAN WFP_UpdateProcess(PROCESS *proc);",
    "void WFP_DeleteProcess(PROCESS *proc);",
]:
    require(header, term, "header declaration")

for forbidden in [
    "FwpmBfeStateSubscribeChanges",
    "FwpmEngineOpen",
    "FwpsCalloutRegister",
    "FwpmFilterAdd",
    "WFP_classify",
    "WFP_Processes",
    "WFP_MapLock",
    "NetFw_BlockTraffic",
    "Conf_Get_Boolean",
    "Api_SetFunction",
]:
    reject(header, forbidden, "runtime owner code in header")

for term in [
    '#include "wfp.h"',
    "#include <fwpsk.h>",
    "_FX BOOLEAN WFP_Init(void)",
    "return WFP_Load();",
    "_FX BOOLEAN WFP_Load(void)",
    "FwpmBfeStateSubscribeChanges(",
    "FwpmBfeStateGet() == FWPM_SERVICE_RUNNING",
    "_FX void WFP_Unload(void)",
    "WFP_Uninstall_Callbacks();",
    "_FX BOOLEAN WFP_Install_Callbacks(void)",
    "FwpmEngineOpen(",
    "FwpmTransactionBegin(",
    "WFP_RegisterCallout(&WPF_SEND_CALLOUT_GUID_V4",
    "FWP_ACTION_CALLOUT_TERMINATING",
    "FwpsCalloutRegister1(",
    "FwpmFilterAdd(",
    "BOOLEAN WFP_InitProcess(PROCESS* proc)",
    "BOOLEAN WFP_UpdateProcess(PROCESS* proc)",
    "void WFP_DeleteProcess(PROCESS* proc)",
    "void WFP_classify(",
    "classifyOut->actionType = FWP_ACTION_BLOCK;",
    "classifyOut->actionType = FWP_ACTION_PERMIT;",
]:
    require(wfp, term, "wfp.c owner topology")

for term in [
    '#include "wfp.h"',
    "ok = WFP_Init();",
    "WFP_Unload();",
]:
    require(driver, term, "driver lifecycle caller")

for term in [
    '#include "wfp.h"',
    "if (!fail && !WFP_InitProcess(proc))",
    "WFP_DeleteProcess(proc);",
]:
    require(process, term, "process lifecycle caller")

for term in [
    '#include "wfp.h"',
    "ok = WFP_UpdateProcess(proc);",
    "this api call is also used to update network access permissions",
]:
    require(file_source, term, "file/settings refresh caller")

for term in [
    "SREV-027: WFP Classify NetFwTrace Logging Cannot Use Session Monitor Inline",
    "owner: \"Sandboxie/core/drv/wfp.c:914\"",
    "WFP `classifyFn` may run at `IRQL <= DISPATCH_LEVEL`",
    "Do not log inline from `WFP_classify`",
]:
    require(ledger, term, "existing WFP owner coverage")

for term in [
    "fwps_callout_classify_fn0",
    "IRQL <= DISPATCH_LEVEL",
    "nonpaged/deferred logger",
    "Driver Verifier IRQL checking",
]:
    require(srev027_spec, term, "SREV-027 official shape")

for term in [
    "No source patch",
    "declaration/topology header",
    "No new Windows/API runtime behavior is defined by this header",
    "future concrete-owner SREV Windows",
]:
    require(spec, term, "spec classification")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-239",
    "owner: Sandboxie/core/drv/wfp.h",
    "docs-only-source-topology-reviewed",
    "srev-239-wfp-driver-header-topology.schema.json",
    "check-srev-239.py",
]:
    require(fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-239 source gate passed")
