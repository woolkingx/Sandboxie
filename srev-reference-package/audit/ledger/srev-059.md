---
kind: srev-ledger-entry
id: SREV-059
title: GUI Raw Input Size Boundary
status: patched-source-level-after-official-getrawinputdeviceinfoa-w-parameter-shape-and
owner: Sandboxie/core/dll/guimisc.c
spec: docs/plan/srev-059-gui-raw-input-size-boundary.md
schema: docs/plan/srev-059-gui-raw-input-size-boundary.schema.json
checker: docs/plan/check-srev-059.py
runtime_gate: "normal A/W raw-input queries, `pData == NULL` size query, null `pcbSize` failure in caller process, and oversized Unicode device-name request rejection without helper-service crash"
---
### SREV-059: GUI Raw Input Size Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official GetRawInputDeviceInfoA/W parameter shape and local GUI proxy wire-size analysis; needs Windows raw-input proxy runtime proof |
| Evidence | `Sandboxie/core/dll/guimisc.c` `Gui_GetRawInputDeviceInfo_impl` had a source comment saying `GetRawInputDeviceInfoA` accesses `pcbSize` without checking for NULL, so the hook used a dummy zero value to avoid crashing the helper service. Microsoft documents `pData` as optional but `pcbSize` as required. The same path converted Unicode `RIDI_DEVICENAME` character counts to bytes before request allocation without overflow gates, and `Sandboxie/core/svc/GuiServer.cpp` multiplied the service-side character count before checking the bounded reply data capacity. |
| Data | Caller `hDevice`, `uiCommand`, optional `pData`, required `pcbSize`, `RIDI_DEVICENAME` character count, DLL request byte length, service reply `max_data`, and GUI wire request/reply buffers. |
| Schema | `GUI_RAW_INPUT_SIZE_BOUNDARY` says the DLL hook may omit `pData` but must not send a GUI proxy request without caller-owned `pcbSize`; Unicode `RIDI_DEVICENAME` character counts must be proven to fit before character-to-byte multiplication on both DLL and service sides. |
| Topology | Caller size pointer flows into the DLL request builder, then through the GUI wire request, then into the service-owned bounded reply buffer before User32 is called. `pcbSize` is the size owner; the service owns the max reply data capacity. |
| Logic Risk | A proxy boundary should not manufacture a legal-looking request from an illegal Win32 call shape. Null `pcbSize` should fail in the caller process, not be converted into a service request. Multiplying an untrusted character count before a max-data gate can overflow and let a forged request call User32 with a small proxy buffer and huge size. |
| Official Shape | `docs/plan/srev-059-gui-raw-input-size-boundary.md` records Microsoft `GetRawInputDeviceInfoA` references. `docs/plan/srev-059-gui-raw-input-size-boundary.schema.json` records the JSON Schema draft-07 local `GUI_RAW_INPUT_SIZE_BOUNDARY` contract. |
| Fix | `Gui_GetRawInputDeviceInfo_impl` now rejects null `pcbSize`, checks Unicode character-to-byte overflow and request-size addition before allocation, checks `Dll_Alloc`, and always treats `pcbSize` as the required caller-owned size pointer. `GuiServer::GetRawInputDeviceInfoSlave` now computes `max_data` before conversion and rejects Unicode `RIDI_DEVICENAME` character counts larger than `max_data / sizeof(WCHAR)` before multiplying. |
| Acceptance Gate | `docs/plan/check-srev-059.py` validates the draft-07 schema, official reference, DLL null-`pcbSize` rejection, overflow gates, allocation gate, removal of the dummy-size workaround, service pre-multiply max-data gate, and ledger entry; `docs/plan/check-srev-059.sh` is the matrix wrapper. Windows gate: normal A/W raw-input queries, `pData == NULL` size query, null `pcbSize` failure in caller process, and oversized Unicode device-name request rejection without helper-service crash. |
