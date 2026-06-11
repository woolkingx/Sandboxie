---
kind: srev-ledger-entry
id: SREV-034
title: Credential A/W Conversion Block Ownership
status: patched-source-level-after-official-credentiala-credreada-credwritea-block-shape
owner: "Sandboxie/core/dll/cred.c:1264-1267"
spec: docs/plan/srev-034-cred-aw-conversion.md
schema: docs/plan/srev-034-cred-aw-conversion.schema.json
checker: docs/plan/check-srev-034.py
runtime_gate: "sandboxed `CredWriteA`/`CredReadA`/`CredEnumerateA` with full string fields and attributes returns a valid single ANSI credential block without mutating the source wide credential"
---
### SREV-034: Credential A/W Conversion Block Ownership

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official CREDENTIALA/CredReadA/CredWriteA block-shape analysis; needs Windows credential API runtime proof |
| Evidence | `Sandboxie/core/dll/cred.c:1264-1267` allocated a `CREDENTIALA` but set the conversion cursor to `((char*)credW) + sizeof(CREDENTIALW)`. `Cred_CopyW2A` also wrote ANSI output through a `WCHAR *`, and both A/W attribute-array cursors advanced by `sizeof(PCREDENTIAL_ATTRIBUTE*)` instead of `sizeof(CREDENTIAL_ATTRIBUTE*)`. |
| Data | `CREDENTIALA`, `CREDENTIALW`, their embedded string pointers, attribute arrays, credential blob pointer, and attribute value pointers. |
| Schema | Converted structure/string pointers must point inside the newly allocated output block. ANSI string output uses byte stores. Attribute arrays occupy `AttributeCount * sizeof(CREDENTIAL_ATTRIBUTEA/W)` bytes before converted keyword strings. |
| Topology | Hooked ANSI credential APIs cross into the internal wide-character credential store, then convert back to ANSI credential blocks returned to the caller. The conversion helper owns the output block; the input credential remains read-only. |
| Logic Risk | Read-back through `CredReadA` can corrupt the source wide credential block, build invalid ANSI pointer graphs, or overwrite adjacent memory when attributes are present. |
| Official Shape | `docs/plan/srev-034-cred-aw-conversion.md` records Microsoft `CREDENTIALA`, `CredWriteA`, `CredReadA`, and `CredFree` references. `docs/plan/srev-034-cred-aw-conversion.schema.json` records the small local conversion-block schema. |
| Fix | `Cred_CopyW2A` now writes through `char *`; `Cred_CREDENTIALW2A` starts its cursor inside `credA`; A/W conversions advance attribute arrays by `sizeof(CREDENTIAL_ATTRIBUTEA/W)`; allocation failures return NULL and ANSI write/read wrappers fail with `ERROR_NOT_ENOUGH_MEMORY`. |
| Acceptance Gate | `docs/plan/check-srev-034.py` validates the schema and source cursor/array ownership; `docs/plan/check-srev-034.sh` is the matrix wrapper. Windows gate: sandboxed `CredWriteA`/`CredReadA`/`CredEnumerateA` with full string fields and attributes returns a valid single ANSI credential block without mutating the source wide credential. |
