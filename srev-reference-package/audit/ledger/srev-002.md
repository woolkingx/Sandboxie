---
kind: srev-ledger-entry
id: SREV-002
title: Legacy SHA1 Password Hash Comment Admits Nibble Bug
status: patched-source-level-after-official-hash-api-and-legacy-format-analysis-needs-pa
owner: "Sandboxie/core/svc/sbieiniserver.cpp:683"
spec: docs/plan/srev-002-legacy-password-hash.md
schema: docs/plan/srev-002-legacy-password-hash.schema.json
checker: docs/plan/check-srev-002.sh
runtime_gate: known legacy-bug hash, canonical SHA1 hash, and current SHA256/salt password configs all authenticate as expected
---
### SREV-002: Legacy SHA1 Password Hash Comment Admits Nibble Bug

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official hash API and legacy-format analysis; needs password-vector runtime proof |
| Evidence | `Sandboxie/core/svc/sbieiniserver.cpp:683` computes `NibbleH = (data[i] & 0xF0) >> 8` and comments `bug bug should be >> 4`; `sbieiniserver.cpp:874-878` still uses this function to validate legacy 40-hex-character `EditPassword` values. |
| Data | Legacy stored 40-character SHA1 password hash. |
| Schema | A SHA1 hex encoding normally has two nibbles per byte, but existing stored configs may have been produced by the buggy encoder. |
| Topology | Service config authorization checks caller password before changing protected settings. |
| Logic Risk | Directly fixing the shift can break existing legacy password configs; leaving it keeps a weakened legacy comparison shape. |
| Official Shape | `docs/plan/srev-002-legacy-password-hash.md` records Microsoft CryptoAPI/CNG hash shape: APIs return binary digest bytes; printable hex encoding is local application logic. |
| Fix | The legacy SHA1 encoder now makes the historical high-nibble bug an explicit `LegacyBug` mode. Legacy 40-character verification accepts the historical buggy shape first, then canonical SHA1 hex. New password writes still use SHA256/salt. |
| Acceptance Gate | `docs/plan/check-srev-002.sh` proves the inline bug TODO is gone, the legacy/canonical read split exists, and the set-password path still writes SHA256/salt. Windows gate: known legacy-bug hash, canonical SHA1 hash, and current SHA256/salt password configs all authenticate as expected. |
