#!/usr/bin/env python3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LOCAL = ROOT / "docs/plan/local"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"LTEST-003 failed: {label} missing {needle!r}")


spec = (LOCAL / "ltest-003-uac-packet-readprocessmemory-access-denied.md").read_text()
ledger = (LOCAL / "ltest-003.md").read_text()
svc = (ROOT / "Sandboxie/core/svc/serviceserver2.cpp").read_text()
secure = (ROOT / "Sandboxie/core/dll/secure.c").read_text()

for term in [
    "LTEST-003: UAC Packet ReadProcessMemory Access Denied",
    "SBIE2218 Failed to get elevated privileges: [84 / 00000005]",
    "SBIE2219 Request was issued by program Start.exe [DefaultBox]",
    "COMRuntime 18221",
    "npp.8.5.6.Installer.x64.exe",
    "errlvl = 0x84",
    "ReadProcessMemory",
    "Secure_HandleElevation",
    "MSGID_SERVICE_UAC",
    "No-source-change",
]:
    require(spec, term, "spec")

for term in [
    "Capture `idProcess`, `pkt_addr`, `pkt_len`",
    "granted process access mask",
    "token integrity/elevation/appcontainer flags",
    "VirtualQueryEx",
    "Do not change UAC behavior before official AppInfo/RPC and process-memory API",
]:
    require(spec, term, "capture plan")

for term in [
    "kind: local-test-entry",
    "id: LTEST-003",
    "status: runtime-capture-open-no-source-change",
    "owner: Sandboxie/core/svc/serviceserver2.cpp",
    "Sandboxie/core/dll/secure.c",
    "checker: docs/plan/local/check-ltest-003.py",
]:
    require(ledger, term, "ledger header")

for term in [
    "### LTEST-003: UAC Packet ReadProcessMemory Access Denied",
    "`SBIE2218 [84 / 00000005]`",
    "`SECURE_UAC_PACKET`",
    "`ReadProcessMemory`",
    "None yet. This is a local-only runtime capture entry.",
]:
    require(ledger, term, "ledger body")

for term in [
    "errlvl = 0x84;",
    "ReadProcessMemory(hProcess, (void *)(ULONG_PTR)pkt_addr, pkt,",
    "ReportError2218(idProcess, errlvl);",
]:
    require(svc, term, "serviceserver2 source")

for term in [
    "Secure_HandleElevation",
    "req.h.msgid = MSGID_SERVICE_UAC;",
    "req.uac_pkt_addr = (ULONG64)(ULONG_PTR)pkt;",
    "req.uac_pkt_len  = pkt_len;",
]:
    require(secure, term, "secure source")

print("LTEST-003 runtime capture gate passed")
