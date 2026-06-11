---
kind: local-test-entry
id: LTEST-002
title: SandMan Test UI Certificate Gate
status: patched-source-level-needs-windows-ui-runtime-proof
owner: SandboxiePlus/SandMan/SandMan.cpp
paths:
  - SandboxiePlus/SandMan/SandMan.cpp
spec: docs/plan/local/ltest-002-sandman-test-ui-certificate-gate.md
schema: docs/plan/local/ltest-002-sandman-test-ui-certificate-gate.schema.json
checker: docs/plan/local/check-ltest-002.py
runtime_gate: Windows SandMan smoke with Sandboxie.ini [GlobalSettings] Test=true proving supporter-certificate warning dialogs are suppressed while driver feature enforcement remains owned by LTEST-001 core gates
---
### LTEST-002: SandMan Test UI Certificate Gate

| Field | Content |
|---|---|
| Severity | [low] |
| Status | patched source-level local UI gate; needs Windows UI/runtime proof |
| Evidence | LTEST-001 proves the core driver `Test=true` gate can bypass local supporter-certificate process termination gates, but SandMan still has an independent UI warning path in `CSandMan::CheckCertificate`. That UI path should honor the same local test intent without mutating certificate state. This entry is local-only and not an SREV. |
| Data | `Test=true`, `CSandMan_IsLocalTestMode`, `CSandMan::CheckCertificate`, `g_CertInfo`, and `QMessageBox`. |
| Schema | `SANDMAN_TEST_UI_CERTIFICATE_GATE` says `Test=true` is a local SandMan UI test setting, not a supporter certificate; the setting is read from `Sandboxie.ini [GlobalSettings] Test`; accepted true spellings are `true`, `yes`, `y`, `1`, and `on`; `CSandMan::CheckCertificate` returns true before showing the supporter warning; the gate must not mutate `g_CertInfo`, certificate parsing state, driver feature flags, or core process enforcement. |
| Topology | `Sandboxie.ini [GlobalSettings] Test=true -> theAPI->SbieIniGet("GlobalSettings", "Test", 0) -> CSandMan_IsLocalTestMode -> CSandMan::CheckCertificate -> return true before QMessageBox`. |
| Logic Risk | UI warning state and driver enforcement are separate layers. If SandMan ignores local `Test=true`, local runtime tests get blocked or confused by a UI warning even when the core gate is already in test mode. |
| Fix | `SandMan.cpp` now defines `CSandMan_IsLocalTestMode`, which reads the global `Test` setting and accepts `true`, `yes`, `y`, `1`, and `on`. `CSandMan::CheckCertificate` returns true under that helper before constructing the supporter-certificate warning. No `g_CertInfo` state, certificate parser, driver feature flags, or core process path changed. |
| Acceptance Gate | `docs/plan/local/check-ltest-002.py` validates the draft-07 schema, local ledger entry, helper source, accepted `Test=true` spellings, early `CheckCertificate` return before `QMessageBox`, and non-mutation of `g_CertInfo`; `docs/plan/local/check-ltest-002.sh` is the targeted wrapper. Windows gate: run a SandMan smoke with `[GlobalSettings] Test=true` and confirm the supporter warning dialog is suppressed. |
