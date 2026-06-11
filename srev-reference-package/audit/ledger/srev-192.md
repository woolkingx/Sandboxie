---
kind: srev-ledger-entry
id: SREV-192
title: GUI COPYDATA Wire Length Contract
status: patched-source-level-after-official-copydatastruct-and-wm-copydata-shape-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/GuiWire.h
spec: docs/plan/srev-192-gui-copydata-wire-length-contract.md
schema: docs/plan/srev-192-gui-copydata-wire-length-contract.schema.json
checker: docs/plan/check-srev-192.py
runtime_gate: Windows SbieSvc and DLL build plus normal WM_COPYDATA DDE copydata short-header and short-tail malformed request proof
---
### SREV-192: GUI COPYDATA Wire Length Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `COPYDATASTRUCT` and `WM_COPYDATA` shape review; needs Windows runtime proof |
| Evidence | `Sandboxie/core/svc/GuiWire.h` was the top unnamed reviewable core file after SREV-191. It defines `GUI_SEND_COPYDATA_REQ`, which is consumed by `Sandboxie/core/svc/GuiServer.cpp` and produced by `Sandboxie/core/dll/guimsg.c` and `Sandboxie/core/dll/guidde.c`. `SendCopyDataSlave` checked `args->req_len < sizeof(GUI_SEND_COPYDATA)`, but `GUI_SEND_COPYDATA` is the enum request id, not `GUI_SEND_COPYDATA_REQ`. The service then read `req->cds_len` from the request. The local wire tail was also declared as `WCHAR cds_buf[1]` even though `COPYDATASTRUCT.cbData` is a byte count and `lpData` is `PVOID`. |
| Data | `GUI_SEND_COPYDATA_REQ`, `cds_key`, `cds_len`, `cds_buf`, `Gui_SendCopyData`, `Gui_DDE_DATA_Posting`, `GuiServer::SendCopyDataSlave`, `COPYDATASTRUCT`, `WM_COPYDATA`, `SendMessage`, `SendMessageTimeout`, DDE copydata bridge, and `args->req_len`. |
| Schema | `GUI_COPYDATA_WIRE_LENGTH_CONTRACT` says `GuiWire.h` owns the local wire shape, `cds_buf` is a byte tail, `cds_len` is a byte count, the fixed header is `FIELD_OFFSET(GUI_SEND_COPYDATA_REQ, cds_buf)`, the enum request id is not a structure size owner, service validation must prove the fixed header before reading `cds_len`, and sender allocation must use fixed header plus byte payload length. |
| Topology | Legal flow is `sender COPYDATASTRUCT -> DLL GUI_SEND_COPYDATA_REQ fixed header + byte tail -> SbieSvc fixed header gate -> cds_len cap -> fixed header + cds_len range gate -> host COPYDATASTRUCT.cbData/lpData -> SendMessage/SendMessageTimeout/DDE route`. |
| Logic Risk | A malformed request shorter than the fixed `GUI_SEND_COPYDATA_REQ` header can pass a `sizeof(enum)` gate and make SbieSvc read `cds_len` outside the supplied request shape. Misdeclaring the tail as `WCHAR` also hides that `WM_COPYDATA` carries arbitrary bytes, including DDE data. |
| Official Shape | `docs/plan/srev-192-gui-copydata-wire-length-contract.md` records Microsoft `COPYDATASTRUCT` and `WM_COPYDATA` references. `docs/plan/srev-192-gui-copydata-wire-length-contract.schema.json` records the JSON Schema draft-07 local `GUI_COPYDATA_WIRE_LENGTH_CONTRACT` contract. |
| Fix | `GUI_SEND_COPYDATA_REQ::cds_buf` is now `UCHAR`. `SendCopyDataSlave` uses `FIELD_OFFSET(GUI_SEND_COPYDATA_REQ, cds_buf)` as the fixed header gate, rejects short fixed headers before reading `cds_len`, checks `fixed_len + cds_len` for wrap and request containment, and no longer uses `sizeof(GUI_SEND_COPYDATA)`. `guimsg.c` and `guidde.c` now allocate the request as fixed header plus byte payload length. |
| Acceptance Gate | `docs/plan/check-srev-192.py` validates the draft-07 schema, official references, byte-tail wire shape, stale wide-tail removal, fixed-header service gate ordering, stale enum-size gate removal, DLL allocation shape, and split ledger fragment; `docs/plan/check-srev-192.sh` is the matrix wrapper. Runtime gate: Windows SbieSvc and DLL build plus normal `WM_COPYDATA`, DDE copydata, short-header malformed request, and short-tail malformed request proof. |
