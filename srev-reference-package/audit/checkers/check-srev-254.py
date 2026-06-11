#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-254 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-254 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-254-com-built-in-winrt-denylist-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-254 failed: schema is not draft-07")
if schema.get("id") != "COM_BUILT_IN_WINRT_DENYLIST_BOUNDARY":
    raise SystemExit("SREV-254 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Com_RoGetActivationFactory owns the local activation-factory hook",
    "WindowsGetStringRawBuffer is the HSTRING inspection boundary",
    "Com_IsClosedRT owns the built-in runtime-class deny-list",
    "boxed COM owns activation",
    "Open COM plus compartment mode routes activation",
    "does not change denied runtime classes",
]:
    require(contracts, term, "schema")

src = (ROOT / "Sandboxie/core/dll/com.c").read_text()
spec = (ROOT / "docs/plan/srev-254-com-built-in-winrt-denylist-boundary.md").read_text()
srev_049 = (ROOT / "docs/plan/srev-049-com-closedrt-list.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-254.md").read_text()

start = src.index("_FX BOOLEAN Com_IsClosedRT(")
end = src.index("// Com_RoGetActivationFactory", start)
closed_rt = src[start:end]

for term in [
    "!(Ipc_OpenCOM && Dll_CompartmentMode)",
    "SbieApi_QueryConfBool(NULL, L\"DisableRTBlacklist\", FALSE)",
    "Dll_ImageType == DLL_IMAGE_GOOGLE_CHROME",
    "wcscmp(strClassId, L\"Windows.System.Launcher\") == 0",
    "wcscmp(strClassId, L\"Windows.UI.Notifications.ToastNotificationManager\") == 0",
    "Com_LoadRTList(setting, &Com_ClosedRT);",
]:
    require(closed_rt, term, "Com_IsClosedRT")

for term in [
    "Chrome's FindAppUriHandlersAsync path needs WinRT broker state outside the boxed COM contract;",
    "keep this runtime class on the built-in ClosedRT deny-list unless open COM owns the activation.",
    "ToastNotificationManager also crosses into user-notification COM state outside the boxed COM contract.",
]:
    require(closed_rt, term, "Com_IsClosedRT comment")

for term in [
    "fatal crash",
    "simplest workaround",
    "causes a deadlock",
]:
    reject(closed_rt, term, "Com_IsClosedRT comment")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SREV-049 fixed the `Com_LoadRTList` cached `ClosedRT` multi-string memory",
    "Com_LoadRTList",
    "RoGetActivationFactory",
]:
    require(spec, term, "spec adjacency")

for term in [
    "The comments around `Com_IsClosedRT` admit two compatibility blocks",
    "RoGetActivationFactory",
    "HSTRING",
]:
    require(srev_049, term, "SREV-049 adjacency")

for term in [
    "### SREV-254: COM Built-In WinRT Denylist Boundary",
    "COM_BUILT_IN_WINRT_DENYLIST_BOUNDARY",
    "srev-254-com-built-in-winrt-denylist-boundary.schema.json",
    "Sandboxie/core/dll/com.c",
    "Windows.System.Launcher",
    "Windows.UI.Notifications.ToastNotificationManager",
    "SREV-049",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-254 source gate passed")
