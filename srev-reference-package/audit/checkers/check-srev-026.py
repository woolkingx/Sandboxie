#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-026 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-026 failed: {label} still contains {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-026-load-key-path-wire-size.schema.json").read_text())
if schema.get("id") != "LOAD_KEY_PATH_WIRE_SIZE":
    raise SystemExit("SREV-026 failed: schema missing LOAD_KEY_PATH_WIRE_SIZE")

wire = (ROOT / "Sandboxie/core/svc/filewire.h").read_text()
sender = (ROOT / "Sandboxie/core/dll/key.c").read_text()
receiver = (ROOT / "Sandboxie/core/svc/fileserver.cpp").read_text()
spec = (ROOT / "docs/plan/srev-026-load-key-path-wire-size.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "#define FILE_LOAD_KEY_PATH_CHARS 1024",
    "WCHAR KeyPath[FILE_LOAD_KEY_PATH_CHARS];",
    "WCHAR FilePath[FILE_LOAD_KEY_PATH_CHARS];",
]:
    require(wire, term, "wire header")

for term in [
    "wcslen(WorkPath) >= FILE_LOAD_KEY_PATH_CHARS",
    "wcslen(TruePath) >= FILE_LOAD_KEY_PATH_CHARS",
]:
    require(sender, term, "sender DLL")

for stale in [
    "make req->FilePath much longer",
    "wcslen(WorkPath) > 127",
    "wcslen(TruePath) > 127",
]:
    reject(sender, stale, "sender DLL")

for term in [
    "req->KeyPath[FILE_LOAD_KEY_PATH_CHARS - 1] = L'\\0';",
    "req->FilePath[FILE_LOAD_KEY_PATH_CHARS - 1] = L'\\0';",
]:
    require(receiver, term, "receiver service")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string",
    "FILE_LOAD_KEY_PATH_CHARS",
    "1024 WCHARs",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-026: LoadKey Hive Path Wire Buffer Is Too Small",
    "FILE_LOAD_KEY_PATH_CHARS",
    "128-WCHAR",
]:
    require(ledger, term, "ledger")

print("SREV-026 schema/source gate passed")
