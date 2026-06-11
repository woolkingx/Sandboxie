#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-059 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-059-gui-raw-input-size-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-059 failed: schema is not draft-07")
if schema.get("id") != "GUI_RAW_INPUT_SIZE_BOUNDARY":
    raise SystemExit("SREV-059 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "pData is optional but pcbSize is required",
    "RIDI_DEVICENAME pcbSize is a character count",
    "reject null pcbSize before sending a GUI proxy request",
    "reject Unicode character-to-byte overflow before request allocation",
    "gate RIDI_DEVICENAME Unicode character count against max_data divided by sizeof(WCHAR) before multiplying",
]:
    require(contracts, term, "schema")

dll = (ROOT / "Sandboxie/core/dll/guimisc.c").read_text()
svc = (ROOT / "Sandboxie/core/svc/GuiServer.cpp").read_text()
spec = (ROOT / "docs/plan/srev-059-gui-raw-input-size-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)

start = dll.index("_FX LONG Gui_GetRawInputDeviceInfo_impl(")
end = dll.index("// Gui_GetRawInputDeviceInfoA", start)
impl = dll[start:end]

for term in [
    "if (!pcbSize) {\n        SetLastError(ERROR_INVALID_PARAMETER);\n        return -1;\n    }",
    "if (uiCommand == RIDI_DEVICENAME && bUnicode) {\n            if (lenData > 0xFFFFFFFFUL / sizeof(WCHAR))",
    "if (lenData > 0xFFFFFFFFUL - sizeof(GUI_GET_RAW_INPUT_DEVICE_INFO_REQ) - 10)",
    "req = Dll_Alloc(reqSize);\n    if (!req) {\n        SetLastError(ERROR_NOT_ENOUGH_MEMORY);\n        return -1;\n    }",
    "req->cbSize = *pcbSize;",
    "*pcbSize = rpl->cbSize;",
]:
    require(impl, term, "DLL raw-input proxy")

if "dummy value so that we don't crash the helper service" in impl:
    raise SystemExit("SREV-059 failed: dummy pcbSize workaround remains")

start = svc.index("ULONG GuiServer::GetRawInputDeviceInfoSlave(")
end = svc.index("//---------------------------------------------------------------------------", start + 1)
slave = svc[start:end]

for term in [
    "ULONG max_data = MAX_RPL_BUF_SIZE - sizeof(GUI_GET_RAW_INPUT_DEVICE_INFO_RPL);",
    "if (req->uiCommand == RIDI_DEVICENAME && req->unicode) {\n            if (lenData > max_data / sizeof(WCHAR))\n                return STATUS_INVALID_PARAMETER;\n            lenData *= sizeof(WCHAR);\n        }",
    "if (lenData > max_data)\n        return STATUS_INVALID_PARAMETER;",
]:
    require(slave, term, "service raw-input proxy")

if slave.index("ULONG max_data = MAX_RPL_BUF_SIZE") > slave.index("if (req->uiCommand == RIDI_DEVICENAME"):
    raise SystemExit("SREV-059 failed: service max_data gate is not before RIDI_DEVICENAME multiply")

for term in [
    "https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getrawinputdeviceinfoa",
    "srev-059-gui-raw-input-size-boundary.schema.json",
    "`pcbSize` is a character count",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-059: GUI Raw Input Size Boundary",
    "GUI_RAW_INPUT_SIZE_BOUNDARY",
    "srev-059-gui-raw-input-size-boundary.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-059 schema/source gate passed")
