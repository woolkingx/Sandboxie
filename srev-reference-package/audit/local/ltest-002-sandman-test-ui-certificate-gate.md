# LTEST-002: SandMan Test UI Certificate Gate

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> boundary -> action -> verify |
| Input artifact | `SandboxiePlus/SandMan/SandMan.cpp`, `CSandMan::CheckCertificate`, global Sandboxie config, and LTEST-001 core `Test=true` runtime gate |
| Output artifact | One local-only SandMan UI gate that honors `[GlobalSettings] Test=true` before showing supporter-certificate warning dialogs |
| Owner | `SandboxiePlus/SandMan/SandMan.cpp` owns the UI warning decision only; core feature enforcement remains owned by the driver |
| Acceptance gate | Source readback proves SandMan reads `Sandboxie.ini [GlobalSettings] Test`, accepts the same true spellings as LTEST-001, returns from `CheckCertificate` before constructing the supporter warning, and does not mutate `g_CertInfo` or certificate state |

## Data

- Global Sandboxie configuration setting: `Test=true`.
- UI gate: `CSandMan::CheckCertificate`.
- Certificate state projection: `g_CertInfo`.
- Local test namespace: `LTEST-002`.

## Schema

`SANDMAN_TEST_UI_CERTIFICATE_GATE`:

- `Test=true` is a local SandMan UI test setting, not a supporter certificate.
- The setting is read from `Sandboxie.ini [GlobalSettings] Test`.
- Accepted true spellings are `true`, `yes`, `y`, `1`, and `on`.
- `CSandMan::CheckCertificate` must return true under the local UI test gate before building and showing the supporter-certificate message box.
- The local UI test gate must not mutate `g_CertInfo`, certificate parsing, secure certificate state, driver feature flags, or core process enforcement.
- This local test entry is not an SREV and must not be included in the upstream-facing SREV/KPATH ledger.

## Topology

```text
Sandboxie.ini [GlobalSettings] Test=true
  -> SandMan theAPI->SbieIniGet("GlobalSettings", "Test", 0)
  -> CSandMan_IsLocalTestMode()
  -> CSandMan::CheckCertificate returns true before QMessageBox
```

The driver remains the owner of process enforcement. This UI gate only suppresses
the SandMan supporter warning during disposable local test builds where LTEST-001
has already made the core runtime path testable.

## Logic Risk

LTEST-001 makes the core runtime path testable, but SandMan can still show the
supporter warning because its UI gate only reads `g_CertInfo`. That warning is a
separate UI decision, not proof that the driver blocked the process. The local
test path should keep those layers aligned without pretending the user has a
real supporter certificate.

## Fix

`SandMan.cpp` defines a local helper that reads `[GlobalSettings] Test` through
the existing Sandboxie API surface and accepts `true`, `yes`, `y`, `1`, and `on`.
`CSandMan::CheckCertificate` returns true under that helper before constructing
the supporter-certificate warning.

The fix does not mutate `g_CertInfo`, does not alter certificate reload or
parsing, and does not change driver enforcement. It is local-only scaffolding for
the fork's private test workflow.

## Acceptance Gate

`docs/plan/local/check-ltest-002.py` validates the draft-07 schema, local ledger
fragment, helper source, accepted `Test=true` spellings, early `CheckCertificate`
return before `QMessageBox`, and non-mutation of `g_CertInfo`.

Linux verification is source-level only. Windows UI/runtime proof remains a
local manual or VM smoke gate.
