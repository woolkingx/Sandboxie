#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-083 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-083-gui-device-notification-fake-handle.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-083 failed: schema is not draft-07")
if schema.get("id") != "GUI_DEVICE_NOTIFICATION_FAKE_HANDLE":
    raise SystemExit("SREV-083 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "non-NULL fake handle owned by gui.c",
    "process-local cookie",
    "succeeds locally only for the fake handle",
    "forwarded to the real user32 owner",
    "does not convert arbitrary handles",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-083-gui-device-notification-fake-handle.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "static ULONG Gui_DeviceNotificationCookie = 0;",
    "return (ULONG_PTR)&Gui_DeviceNotificationCookie;",
    "if (Handle != (ULONG_PTR)&Gui_DeviceNotificationCookie)",
    "return __sys_UnregisterDeviceNotification(Handle);",
    "SetLastError(0);",
    "UNREFERENCED_PARAMETER(hRecipient);",
    "UNREFERENCED_PARAMETER(NotificationFilter);",
    "UNREFERENCED_PARAMETER(Flags);",
]:
    require(src, term, "gui.c")

if "0x12345678" in src:
    raise SystemExit("SREV-083 failed: stale magic fake handle remains")

start = src.index("_FX BOOL Gui_UnregisterDeviceNotification")
end = src.index("//---------------------------------------------------------------------------", start + 1)
func = src[start:end]
if "return TRUE;" not in func:
    raise SystemExit("SREV-083 failed: fake unregister success missing")
if "return __sys_UnregisterDeviceNotification(Handle);" not in func:
    raise SystemExit("SREV-083 failed: non-fake handle is not forwarded")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "### SREV-083: GUI Device Notification Fake Handle Boundary",
    "GUI_DEVICE_NOTIFICATION_FAKE_HANDLE",
    "srev-083-gui-device-notification-fake-handle.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-083 schema/source gate passed")
