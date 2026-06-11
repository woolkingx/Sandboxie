#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-003 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-003 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-003-uac-app-name-shape.schema.json").read_text())
if schema.get("id") != "UAC_APP_NAME_SHAPE":
    raise SystemExit("SREV-003 failed: schema missing UAC_APP_NAME_SHAPE")

contracts = "\n".join(schema["contracts"])
for term in [
    "ShellExecuteW lpFile and lpParameters are separate",
    "*MSI* token belongs to app",
    "exact five-WCHAR field length",
]:
    require(contracts, term, "schema contracts")

src = (ROOT / "Sandboxie/core/svc/serviceserver2.cpp").read_text()
spec = (ROOT / "docs/plan/srev-003-uac-app-name-shape.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "Service_UacIsMsiToken",
    "ValueLen == 5",
    'wcscmp(AppName, L"*MSI*") == 0',
    "HeapFree(GetProcessHeap(), 0, cmd)",
    "HeapFree(GetProcessHeap(), 0, app)",
]:
    require(src, term, "service source")

reject(src, "bug bug", "service source")
reject(src, 'memcmp(app, L"*MSI*"', "service source")

out = src.find("if (OutAppName) {")
helper = src.find("Service_UacIsMsiToken(app, app_len)", out)
ret_cmd = src.find("*OutAppName = cmd;", out)
if min(out, helper, ret_cmd) < 0 or not helper < ret_cmd:
    raise SystemExit("SREV-003 failed: OutAppName branch must split MSI app token from cmd")

branch = src.find("// elevation type 2")
for tok in [
    "Service_UacIsMsiToken(app, app_len)",
    "Service_UacIsMsiToken(cmd, cmd_len)",
    "Service_UacIsMsiToken(dir, dir_len)",
]:
    if src.find(tok, branch) < 0:
        raise SystemExit(f"SREV-003 failed: MSI execution branch missing {tok!r}")

for term in ["ShellExecuteW", "CommandLineToArgvW", "PathFindFileNameW"]:
    require(spec, term, "spec")

require(ledger, "### SREV-003: UAC App Name Parser Comment Admits Wrong Input Shape", "ledger")
require(ledger, "Sandboxie/core/svc/serviceserver2.cpp", "ledger")

print("SREV-003 schema/source gate passed")
