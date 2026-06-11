---
kind: srev-ledger-entry
id: SREV-026
title: LoadKey Hive Path Wire Buffer Is Too Small
status: patched-source-level-after-official-unicode-string-and-local-service-wire-analys
owner: "Sandboxie/core/dll/key.c:4796"
spec: docs/plan/srev-026-load-key-path-wire-size.md
schema: docs/plan/srev-026-load-key-path-wire-size.schema.json
checker: docs/plan/check-srev-026.sh
runtime_gate: normal COMPONENTS/SCHEMA hive load still succeeds; long valid paths below 1024 WCHARs reach service validation; over-capacity paths fail closed before copy
---
### SREV-026: LoadKey Hive Path Wire Buffer Is Too Small

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official Unicode-string and local service-wire analysis; needs Windows TrustedInstaller LoadKey runtime proof |
| Evidence | `Sandboxie/core/dll/key.c:4796` rejected translated hive file paths longer than 127 WCHARs with a source comment saying `req->FilePath` should be much longer; `Sandboxie/core/svc/filewire.h:100-101` fixed both `KeyPath` and `FilePath` at 128 WCHARs. |
| Data | `FILE_LOAD_KEY_REQ { KeyPath, FilePath }` crossing from hooked DLL to SbieSvc for registry hive load. |
| Schema | OS object strings are counted Unicode strings; the 128-WCHAR request fields were a Sandboxie wire limit, not an OS path limit. The request capacity must be shared by sender and receiver. |
| Topology | DLL translates the hive file path, copies it into the service request, and SbieSvc validates the path against allowed COMPONENTS/SCHEMA hive locations before calling `NtLoadKey`. |
| Logic Risk | Valid long Windows install or redirected hive paths can fail in the DLL before reaching the service allowlist; magic `127` constants also risk sender/receiver drift if the wire struct changes. |
| Official Shape | `docs/plan/srev-026-load-key-path-wire-size.md` records Microsoft `UNICODE_STRING` byte-count/capacity shape and the local `FILE_LOAD_KEY_REQ` owner contract. |
| Fix | `FILE_LOAD_KEY_PATH_CHARS` now names the shared capacity and sets both path fields to 1024 WCHARs. Sender checks use `FILE_LOAD_KEY_PATH_CHARS`; receiver termination uses `FILE_LOAD_KEY_PATH_CHARS - 1`. |
| Acceptance Gate | `docs/plan/check-srev-026.sh` proves the old 128-WCHAR magic is gone from the LoadKey sender/receiver and both sides use the shared constant. Windows gate: normal COMPONENTS/SCHEMA hive load still succeeds; long valid paths below 1024 WCHARs reach service validation; over-capacity paths fail closed before copy. |
