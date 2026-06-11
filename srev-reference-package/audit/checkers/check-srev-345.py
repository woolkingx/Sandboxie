#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-345 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-345 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-345-wfp-rule-load-fail-closed-logging.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-345 failed: schema is not draft-07")
if schema.get("id") != "WFP_RULE_LOAD_FAIL_CLOSED_LOGGING":
    raise SystemExit("SREV-345 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/wfp.c":
    raise SystemExit("SREV-345 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "WFP_LoadRules owns NetworkAccess rule construction",
    "NetFw_AllocRule failure logs MSG_1201",
    "WFP_UpdateProcess owns the fail-closed transition",
    "must not duplicate the MSG_1201 popup",
    "Partially loaded NewNetFwRules move to OldNetFwRules",
    "BlockInternet true is the local fail-closed state",
    "This SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

wfp = (ROOT / "Sandboxie/core/drv/wfp.c").read_text()
spec = (ROOT / "docs/plan/srev-345-wfp-rule-load-fail-closed-logging.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-345.md").read_text()

load_start = wfp.index("BOOLEAN WFP_LoadRules(LIST* NetFwRules, PROCESS* proc)")
load_end = wfp.index("//---------------------------------------------------------------------------\n// WFP_InitProcess", load_start)
load_block = wfp[load_start:load_end]

update_start = wfp.index("BOOLEAN WFP_UpdateProcess(PROCESS* proc)")
update_end = wfp.index("//---------------------------------------------------------------------------\n// WFP_DeleteProcess", update_start)
update_block = wfp[update_start:update_end]

for term in [
    "List_Init(NetFwRules);",
    "Conf_Get(proc->box->name, L\"NetworkAccess\", index);",
    "Process_MatchImageAndGetValue(proc->box, value, proc->image_name, &level);",
    "NETFW_RULE* rule = NetFw_AllocRule(NULL, level);",
    "Log_Msg_Process(MSG_1201, NULL, NULL, proc->box->session_id, proc->pid);",
    "return FALSE;",
    "NetFw_ParseRule(rule, found_value);",
    "NetFw_AddRule(NetFwRules, rule);",
]:
    require(load_block, term, "WFP_LoadRules")

for term in [
    "ok = WFP_LoadRules(&NewNetFwRules, proc);",
    "if (!ok) {",
    "memcpy(&OldNetFwRules, &NewNetFwRules, sizeof(LIST));",
    "SREV-345: WFP_LoadRules logs the allocation failure at the",
    "rule owner. This refresh path owns fail-closed policy and",
    "cleanup of any partially loaded rule list.",
    "BlockInternet = TRUE;",
    "wfp_proc->BlockInternet = BlockInternet;",
    "WFP_FreeRules(&OldNetFwRules);",
]:
    require(update_block, term, "WFP_UpdateProcess")

reject(update_block, "// todo: log error", "WFP_UpdateProcess TODO")
reject(update_block, "on roule failure we lust block everything", "WFP_UpdateProcess typo comment")

if update_block.count("MSG_1201") != 0:
    raise SystemExit("SREV-345 failed: WFP_UpdateProcess duplicates MSG_1201")
if update_block.index("memcpy(&OldNetFwRules, &NewNetFwRules, sizeof(LIST));") > update_block.index("BlockInternet = TRUE;"):
    raise SystemExit("SREV-345 failed: partial rules are not staged before fail-closed state")
if update_block.index("BlockInternet = TRUE;") > update_block.index("wfp_proc->BlockInternet = BlockInternet;"):
    raise SystemExit("SREV-345 failed: fail-closed state is not set before map publication")
if update_block.index("memcpy(&OldNetFwRules, &NewNetFwRules, sizeof(LIST));") > update_block.index("WFP_FreeRules(&OldNetFwRules);"):
    raise SystemExit("SREV-345 failed: partial rules are not staged before cleanup")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "No new Windows API edge is introduced by this SREV",
    "SREV-162 records the official Microsoft",
    "kernel error-log DDI shape",
    "`WFP_LoadRules` logs the allocation failure",
    "`WFP_UpdateProcess` owns fail-closed policy",
    "No rule parsing",
    "Runtime gate:",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-345: WFP Rule Load Fail-Closed Logging Boundary",
    "WFP_RULE_LOAD_FAIL_CLOSED_LOGGING",
    "srev-345-wfp-rule-load-fail-closed-logging.schema.json",
    "Sandboxie/core/drv/wfp.c",
    "WFP_LoadRules",
    "WFP_UpdateProcess",
    "MSG_1201",
    "BlockInternet",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-345 source gate passed")
