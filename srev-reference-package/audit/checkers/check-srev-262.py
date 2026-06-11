#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-262 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-262 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-262-dllmain-pca-restart-comment-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-262 failed: schema is not draft-07")
if schema.get("id") != "DLLMAIN_PCA_RESTART_COMMENT_OWNER":
    raise SystemExit("SREV-262 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "SREV-085 owns the PCA job restart topology",
    "restart is needed before Sandboxie job attach",
    "AppContainer processes skip this PCA restart path",
    "does not change flags policy reads monitor output",
]:
    require(contracts, term, "schema")

dllmain = (ROOT / "Sandboxie/core/dll/dllmain.c").read_text()
srev_085 = (ROOT / "docs/plan/srev-085-pca-restart-command-line-shape.md").read_text()
srev_085_check = (ROOT / "docs/plan/check-srev-085.py").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-262.md").read_text()

comment_start = dllmain.index("SREV-085 owns this PCA job restart topology.")
comment_end = dllmain.index("int MustRestartProcess = 0;", comment_start)
comment_block = dllmain[comment_start:comment_end]

for term in [
    "SREV-085 owns this PCA job restart topology.",
    "PCA job are replaced through SbieSvc before Sandboxie job attach;",
    "AppContainer processes skip this restart path.",
]:
    require(comment_block, term, "dllmain.c PCA comment")

for stale in [
    "workaround for Program Compatibility Assistant (PCA)",
    "to start a second instance of this process outside the PCA job",
    "note: restart fails if running as AppContainer",
]:
    reject(comment_block, stale, "dllmain.c PCA comment")

for term in [
    "SBIE_FLAG_PROCESS_IN_PCA_JOB",
    "SBIE_FLAG_PROCESS_IN_APP_PKG",
    "NoRestartOnPCA",
    "MustRestartProcess = 1;",
    "Proc_RestartProcessOutOfPcaJob();",
]:
    require(dllmain, term, "dllmain.c PCA decision")

for term in [
    "SREV-262 later clarified the `dllmain.c` source comment",
    "PCA/AppContainer restart gate and SREV-085 comment\nowner",
]:
    require(srev_085, term, "SREV-085 spec adjacency")

for term in [
    "SREV-085 owns this PCA job restart topology.",
    "PCA job are replaced through SbieSvc before Sandboxie job attach;",
    "AppContainer processes skip this restart path.",
    "SREV-262",
]:
    require(srev_085_check, term, "SREV-085 checker adjacency")

for term in [
    "### SREV-262: DLL Main PCA Restart Comment Owner",
    "DLLMAIN_PCA_RESTART_COMMENT_OWNER",
    "srev-262-dllmain-pca-restart-comment-owner.schema.json",
    "Sandboxie/core/dll/dllmain.c",
    "Proc_RestartProcessOutOfPcaJob",
    "SREV-085",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-262 source gate passed")
