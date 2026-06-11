#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-289 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-289 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-289-gui-device-notification-init-gate-owner.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-289 failed: schema is not draft-07")
if schema.get("id") != "GUI_DEVICE_NOTIFICATION_INIT_GATE_OWNER":
    raise SystemExit("SREV-289 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/gui.c":
    raise SystemExit("SREV-289 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "Gui_Init owns only the BlockRegisterDeviceNotification configuration gate for Gui_Init3",
    "Gui_Init3 owns the RegisterDeviceNotificationA W and UnregisterDeviceNotification hook group installation",
    "SREV-083 owns the fake notification handle and unregister forwarding runtime behavior",
    "A and W RegisterDeviceNotification hooks preserve the existing same-address alias branch",
    "this SREV changes comments and proof only",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/gui.c").read_text()
spec = (ROOT / "docs/plan/srev-289-gui-device-notification-init-gate-owner.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-289.md").read_text()
srev_083 = (ROOT / "docs/plan/ledger/srev-083.md").read_text()

init_start = source.index("_FX BOOLEAN Gui_Init(HMODULE module)")
init_end = source.index("//---------------------------------------------------------------------------\n// Gui_Init2", init_start)
init_block = source[init_start:init_end]

for term in [
    "if (ok && SbieApi_QueryConfBool(NULL, L\"BlockRegisterDeviceNotification\", FALSE))",
    "ok = Gui_Init3(module); // SREV-289: optional SREV-083 notification-block hook group",
]:
    require(init_block, term, "Gui_Init gate")

reject(init_block, "todo remove later", "Gui_Init call-site comment")

init3_start = source.index("_FX BOOLEAN Gui_Init3(HMODULE module)")
init3_end = source.index("//---------------------------------------------------------------------------\n// Gui_InitWindows7", init3_start)
init3 = source[init3_start:init3_end]

for term in [
    "if (__sys_RegisterDeviceNotificationA ==\n                                        __sys_RegisterDeviceNotificationW) {",
    "SBIEDLL_HOOK_GUI(RegisterDeviceNotificationW);",
    "SBIEDLL_HOOK_GUI(RegisterDeviceNotificationA);",
    "SBIEDLL_HOOK_GUI(UnregisterDeviceNotification);",
    "return TRUE;",
]:
    require(init3, term, "Gui_Init3 hook topology")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "GUI_DEVICE_NOTIFICATION_INIT_GATE_OWNER",
    "BlockRegisterDeviceNotification",
    "Gui_Init3",
    "RegisterDeviceNotificationA/W",
    "UnregisterDeviceNotification",
    "SREV-083",
]:
    require(spec, term, "spec")

for term in [
    "GUI_DEVICE_NOTIFICATION_FAKE_HANDLE",
    "RegisterDeviceNotificationA/W",
    "UnregisterDeviceNotification",
    "fake handle",
    "non-fake unregister handles are forwarded",
]:
    require(srev_083 + (ROOT / "docs/plan/srev-083-gui-device-notification-fake-handle.md").read_text(), term, "SREV-083 adjacency")

for term in [
    "### SREV-289: GUI Device Notification Init Gate Owner",
    "GUI_DEVICE_NOTIFICATION_INIT_GATE_OWNER",
    "srev-289-gui-device-notification-init-gate-owner.schema.json",
    "Sandboxie/core/dll/gui.c",
    "Gui_Init3",
    "BlockRegisterDeviceNotification",
    "SREV-083",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-289 source gate passed")
