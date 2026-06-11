---
kind: srev-ledger-entry
id: SREV-255
title: Credential ANSI Todo Boundary Comment
status: patched-comment-topology-after-srev-245-ansi-array-boundary-review-no-behavior-change
owner: Sandboxie/core/dll/cred.c
spec: docs/plan/srev-255-cred-ansi-todo-boundary-comment.md
schema: docs/plan/srev-255-cred-ansi-todo-boundary-comment.schema.json
checker: docs/plan/check-srev-255.py
runtime_gate: Inherited from SREV-245 Windows credential smoke is needed before ANSI local credential visibility or returned-array ownership can be claimed fixed
---

### SREV-255: Credential ANSI Todo Boundary Comment

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-245 ANSI array boundary review; no behavior change |
| Evidence | SREV-245 already records the real behavior gap: the ANSI credential-array APIs call the native `CredReadDomainCredentialsA` / `CredEnumerateA` paths directly, while the W siblings inspect and merge Sandboxie's PStore-backed credential namespace. The source still carried two bare `// todo` comments at that boundary. A bare todo does not name the legal output shape, the owner of the future conversion, or the reason this path must not simply call W and return W-owned data through an ANSI API. |
| Data | `Cred_CredReadDomainCredentialsA`, `Cred_CredEnumerateA`, `__sys_CredReadDomainCredentialsA`, `__sys_CredEnumerateA`, `PCREDENTIALA **`, `CredFree`, and SREV-245's ANSI credential-array conversion contract. |
| Schema | `CRED_ANSI_TODO_BOUNDARY_COMMENT` says the current ANSI array APIs remain direct native passthroughs; the source comments must point to SREV-245 as the owner of the unfinished virtualization boundary; future behavior change requires a `CredFree`-compatible ANSI array conversion owner; this SREV must not change hook registration, native passthrough calls, credential conversion helpers, PStore merge behavior, or WinCred flags. |
| Topology | `CredReadDomainCredentialsA / CredEnumerateA -> documented SREV-245 boundary comment -> native Advapi credential API passthrough`. Future topology remains the one named by SREV-245: ANSI input conversion -> W local owner path -> W result array -> ANSI single-block array conversion -> caller frees with CredFree-compatible free path. |
| Logic Risk | The dangerous failure mode is not merely "todo remains"; it is a future patch that sees the W path and returns W-owned data through the ANSI API, or returns several separately allocated ANSI credential blocks behind one `PCREDENTIALA **` array. That would violate the official free/ownership shape. |
| Official Shape | `docs/plan/srev-255-cred-ansi-todo-boundary-comment.md` inherits Microsoft `CredEnumerateA`, `CredReadDomainCredentialsA`, and `CredFree` references from SREV-245. `docs/plan/srev-255-cred-ansi-todo-boundary-comment.schema.json` records the JSON Schema draft-07 local `CRED_ANSI_TODO_BOUNDARY_COMMENT` contract. |
| Fix | Comment-only source clarification. The two bare todo comments now state that ANSI array virtualization is owned by SREV-245 and that native passthrough stays until a `CredFree`-compatible ANSI array conversion owner exists. No behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-255.py` validates the draft-07 schema, SREV-245 adjacency, source comments, removal of the bare todo comments from the two ANSI functions, native passthrough preservation, and the ledger fragment; `docs/plan/check-srev-255.sh` is the targeted wrapper. Runtime gate is inherited from SREV-245: Windows credential smoke is still needed before claiming ANSI local credential visibility or returned-array ownership is fixed. |
