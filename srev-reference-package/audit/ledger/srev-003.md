---
kind: srev-ledger-entry
id: SREV-003
title: UAC App Name Parser Comment Admits Wrong Input Shape
status: patched-source-level-after-official-shellexecute-command-line-shape-and-local-ua
owner: "Sandboxie/core/svc/serviceserver2.cpp:873"
spec: docs/plan/srev-003-uac-app-name-shape.md
schema: docs/plan/srev-003-uac-app-name-shape.schema.json
checker: docs/plan/check-srev-003.sh
runtime_gate: "MSI elevation prompt displays `Windows Installer`; normal executable elevation still displays the executable/command identity"
---
### SREV-003: UAC App Name Parser Comment Admits Wrong Input Shape

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official ShellExecute/command-line shape and local UAC packet analysis; needs Windows UAC prompt runtime proof |
| Evidence | `Sandboxie/core/svc/serviceserver2.cpp:873` checks `*MSI*` against `AppName`, while the inline comment says this value is the command line from `RunUacSlave4`. |
| Data | App display name vs command line. |
| Schema | A display name classifier cannot safely use command-line bytes without parsing executable identity. |
| Topology | Service-side UAC dialog display path. |
| Logic Risk | Mislabeling or failing to label MSI elevation requests; likely compatibility/UI confusion rather than sandbox escape. |
| Official Shape | `docs/plan/srev-003-uac-app-name-shape.md` records Microsoft `ShellExecuteW` file/parameter split plus command-line and filename parser posture. |
| Fix | The UAC display path now returns the `app` field only for the exact `*MSI*` token and otherwise preserves the previous command-line display value. The MSI execution branch also uses exact-length token checks before comparing five WCHARs. |
| Acceptance Gate | `docs/plan/check-srev-003.sh` proves the inline bug comment is gone, MSI classification is length-aware, and non-MSI display still falls back to the command line. Windows gate: MSI elevation prompt displays `Windows Installer`; normal executable elevation still displays the executable/command identity. |
