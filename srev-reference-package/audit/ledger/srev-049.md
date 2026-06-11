---
kind: srev-ledger-entry
id: SREV-049
title: COM ClosedRT Multi-String Drift
status: patched-source-level-after-official-rogetactivationfactory-hstring-and-local-clo
owner: "Sandboxie/core/dll/com.c:3440-3500"
spec: docs/plan/srev-049-com-closedrt-list.md
schema: docs/plan/srev-049-com-closedrt-list.schema.json
checker: docs/plan/check-srev-049.py
runtime_gate: "`ClosedRT` absent, normal, image-filtered, reload/drift, denied `Windows.System.Launcher`, denied `ToastNotificationManager`, and allowed runtime classes"
---
### SREV-049: COM ClosedRT Multi-String Drift

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official RoGetActivationFactory/HSTRING and local ClosedRT multi-string shape analysis; needs Windows WinRT activation runtime proof |
| Evidence | `Sandboxie/core/dll/com.c:3440-3500` `Com_LoadRTList` counted `ClosedRT` configuration entries in one pass, allocated exact capacity, and then copied entries after reading configuration again. `Com_Alloc` does not zero the buffer. A second-pass drift to fewer entries could leave the first WCHAR uninitialized, while a second-pass drift to more data could copy without preserving capacity for the final multi-string terminator. The same COM area has source comments saying Chrome can crash on one runtime activation failure shape and `ToastNotificationManager` can deadlock with boxed COM. |
| Data | `ClosedRT` configuration entries, optional image filter prefix, cached WCHAR multi-string, and `RoGetActivationFactory` runtime class ID. |
| Schema | `COM_CLOSED_RT_MULTI_STRING` is a NUL-separated WCHAR list terminated by an empty final string. Configuration drift between count and copy passes must produce a shorter valid list, not uninitialized data or overflow. |
| Topology | Configuration flows into `Com_LoadRTList`, then the cached list flows into `Com_IsClosedRT`, then the activation decision gates `Com_RoGetActivationFactory`. |
| Logic Risk | The compatibility deny-list protects crash/deadlock cases, so its cache must fail closed as a valid empty or shortened list. Letting memory initialization or config timing define the list corrupts the activation policy boundary. |
| Official Shape | `docs/plan/srev-049-com-closedrt-list.md` records Microsoft `RoGetActivationFactory` and `HSTRING` references. `docs/plan/srev-049-com-closedrt-list.schema.json` records the JSON Schema draft-07 local `COM_CLOSED_RT_MULTI_STRING` contract. |
| Fix | `Com_LoadRTList` initializes the first WCHAR before the second pass, computes each entry length once, copies only when the entry leaves room for the final empty string, and writes the terminator at `cur_pos`. |
| Acceptance Gate | `docs/plan/check-srev-049.py` validates the draft-07 schema, official references, initialized sentinel, per-entry remaining-capacity gate, removal of the old `total_len - 1` terminator, and ledger entry; `docs/plan/check-srev-049.sh` is the matrix wrapper. Windows gate: `ClosedRT` absent, normal, image-filtered, reload/drift, denied `Windows.System.Launcher`, denied `ToastNotificationManager`, and allowed runtime classes. |
