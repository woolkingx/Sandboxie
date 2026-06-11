---
kind: srev-ledger-entry
id: SREV-245
title: Credential ANSI Enumeration And Domain Read Boundary
status: docs-only-boundary-gap-recorded-needs-ansi-array-conversion-design-and-windows-runtime-proof
owner: Sandboxie/core/dll/cred.c
spec: docs/plan/srev-245-cred-ansi-enumeration-domain-read-boundary.md
schema: docs/plan/srev-245-cred-ansi-enumeration-domain-read-boundary.schema.json
checker: docs/plan/check-srev-245.py
runtime_gate: Windows credential smoke for ANSI enumerate/domain-read visibility plus CredFree-compatible returned array ownership
---

### SREV-245: Credential ANSI Enumeration And Domain Read Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | docs-only boundary gap recorded; needs ANSI credential-array conversion design and Windows credential runtime proof before source behavior change |
| Evidence | `Sandboxie/core/dll/cred.c` used to have `// todo` comments on `Cred_CredReadDomainCredentialsA` and `Cred_CredEnumerateA`. Both ANSI hooks call native `__sys_CredReadDomainCredentialsA` / `__sys_CredEnumerateA` directly. The comments now point at this SREV's owner boundary: ANSI array virtualization is not implemented until a `CredFree`-compatible ANSI array conversion owner exists. The W siblings first inspect Sandboxie's PStore-backed credential namespace and either return local credentials or merge local credentials with native `__sys_CredEnumerateW` output. |
| Data | `Cred_CredReadDomainCredentialsA`, `Cred_CredReadDomainCredentialsW`, `Cred_CredEnumerateA`, `Cred_CredEnumerateW`, `Cred_CREDENTIAL_TARGET_INFORMATIONA2W`, `Cred_CREDENTIALW2A`, `Cred_UnserializeN`, `Cred_SimpleCred`, `Cred_DomainCred`, `__sys_CredReadDomainCredentialsA/W`, `__sys_CredEnumerateA/W`, `PCREDENTIALA **`, `PCREDENTIALW **`, `CredFree`, and Sandboxie's PStore-backed credential items. |
| Schema | `CRED_ANSI_ENUM_DOMAIN_BOUNDARY` says `cred.c` owns local credential virtualization before a credential enumerate or domain-read result leaves the sandboxed process; `CredEnumerateA` and `CredReadDomainCredentialsA` return ANSI credential-array output slots, not opaque native passthrough buffers; the official ANSI result is an array of `PCREDENTIALA` pointers in one allocated return block that the caller frees with `CredFree`; a future source patch must convert ANSI inputs to the wide local owner path, merge local PStore and native results through the same policy as the W path, and return a valid ANSI single-block result; it must not return `PCREDENTIALW **` data through an ANSI API and must not return several separately allocated `CREDENTIALA` blocks as if they were one CredFree-owned block. |
| Topology | Current W topology is credential writes -> converted W credential -> Sandboxie PStore namespace -> W read/enumerate owner -> local PStore result plus native W fallback/merge -> W credential-array block. Current A topology is direct ANSI native passthrough, so local PStore entries can be missed by ANSI callers. Required future topology is ANSI input conversion -> W local owner path -> W result array -> ANSI single-block array conversion -> caller frees through the expected credential free path. |
| Logic Risk | The direct ANSI passthrough splits the credential boundary by encoding path: W callers can see Sandboxie's local virtualized credentials, while A callers can miss them and observe only the native credential set. A partial fix that returns W pointers through an A API or returns multiple separately allocated A credentials would violate the official output ownership shape. |
| Official Shape | `docs/plan/srev-245-cred-ansi-enumeration-domain-read-boundary.md` records Microsoft `CredEnumerateA/W`, `CredReadDomainCredentialsA/W`, and `CredFree` references. `docs/plan/srev-245-cred-ansi-enumeration-domain-read-boundary.schema.json` records the JSON Schema draft-07 local `CRED_ANSI_ENUM_DOMAIN_BOUNDARY` contract. |
| Fix | No source patch in this SREV. This records the boundary gap and the required owner shape for a future patch: an explicit ANSI single-block array conversion helper, not direct W-array reuse and not a bundle of independently allocated A credential blocks. |
| Acceptance Gate | `docs/plan/check-srev-245.py` validates the draft-07 schema, official WinCred references, current source evidence for the two ANSI direct passthroughs and their SREV-245 owner-boundary comments, W-path local PStore merge/fallback topology, SREV-034/SREV-116 adjacency, and the split ledger fragment. Runtime/build gate: Windows credential smoke where sandboxed `CredWriteA` / `CredWriteDomainCredentialsA` entries are visible through `CredEnumerateA` / `CredReadDomainCredentialsA`, native host credentials still merge according to intended policy, and returned ANSI arrays can be released by the expected credential free path without leaks or invalid pointer graphs. |
