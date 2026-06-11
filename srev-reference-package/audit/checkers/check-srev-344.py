#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-344 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-344 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-344-wfp-transaction-abort-cleanup.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-344 failed: schema is not draft-07")
if schema.get("id") != "WFP_TRANSACTION_ABORT_CLEANUP":
    raise SystemExit("SREV-344 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/wfp.c":
    raise SystemExit("SREV-344 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "dynamic WFP engine session",
    "explicit rollback edge",
    "final dynamic-session cleanup edge",
    "Abort status must be captured and logged",
    "_Analysis_assume_lock_not_held_ stays paired",
    "Callout unregister cleanup remains separate",
    "Windows runtime proof is still required",
]:
    require(contracts, term, "schema")

wfp = (ROOT / "Sandboxie/core/drv/wfp.c").read_text()
spec = (ROOT / "docs/plan/srev-344-wfp-transaction-abort-cleanup.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-344.md").read_text()

install_start = wfp.index("_FX BOOLEAN WFP_Install_Callbacks(void)")
install_end = wfp.index("//---------------------------------------------------------------------------\n// WFP_Uninstall_Callbacks", install_start)
install_block = wfp[install_start:install_end]

for term in [
    "FWPM_SESSION wdf_session = { 0 };",
    "BOOLEAN in_transaction = FALSE;",
    "BOOLEAN callout_registered = FALSE;",
    "wdf_session.flags = FWPM_SESSION_FLAG_DYNAMIC;",
    "FwpmEngineOpen(NULL, RPC_C_AUTHN_WINNT, NULL, &wdf_session, &WFP_engine_handle)",
    "FwpmTransactionBegin(WFP_engine_handle, 0)",
    "in_transaction = TRUE;",
    "WFP_RegisterSubLayer();",
    "WFP_RegisterCallout(&WPF_SEND_CALLOUT_GUID_V4",
    "WFP_RegisterCallout(&WPF_RECV_CALLOUT_GUID_V6",
    "FwpmTransactionCommit(WFP_engine_handle)",
    "in_transaction = FALSE;",
    "SREV-344: abort is the primary rollback edge",
    "dynamic session below is the final owner cleanup edge",
    "NTSTATUS abort_status = FwpmTransactionAbort(WFP_engine_handle);",
    "_Analysis_assume_lock_not_held_(WFP_engine_handle);",
    "if (!NT_SUCCESS(abort_status))",
    "DbgPrint(\"Sbie WFP transaction abort failed, status 0x%08x\\r\\n\", abort_status);",
    "FwpsCalloutUnregisterById(WFP_send_callout_id_v4);",
    "FwpsCalloutUnregisterById(WFP_recv_callout_id_v6);",
    "FwpmEngineClose(WFP_engine_handle);",
    "WFP_engine_handle = NULL;",
]:
    require(install_block, term, "WFP_Install_Callbacks")

for stale in [
    "Potential leak if \"FwpmTransactionAbort\" fails",
]:
    reject(install_block, stale, "abort leak comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "session is destroyed",
    "BFE",
    "first aborts any existing transaction",
    "dynamic session",
    "FwpmTransactionAbort",
    "Runtime gate:",
]:
    require(spec, term, "spec official shape")

for term in [
    "### SREV-344: WFP Transaction Abort Cleanup",
    "WFP_TRANSACTION_ABORT_CLEANUP",
    "srev-344-wfp-transaction-abort-cleanup.schema.json",
    "Sandboxie/core/drv/wfp.c",
    "WFP_Install_Callbacks",
    "FwpmTransactionAbort",
    "FwpmEngineClose",
    "abort_status",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-344 source gate passed")
