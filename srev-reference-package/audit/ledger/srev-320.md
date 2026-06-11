---
kind: srev-ledger-entry
id: SREV-320
title: Proc Child Token Compatibility Gates
status: comment-classified-after-official-process-token-shape-review-no-behavior-change
owner: Sandboxie/core/dll/proc.c
spec: docs/plan/srev-320-proc-child-token-compatibility-gates.md
schema: docs/plan/srev-320-proc-child-token-compatibility-gates.schema.json
checker: docs/plan/check-srev-320.py
runtime_gate: Windows Edge/Chrome CDM service child launch, Firefox -sandboxingKind child launch, Acrobat/plugin-container child launch, DeprecatedTokenHacks negative smoke, and DropChildProcessToken negative smoke
---
### SREV-320: Proc Child Token Compatibility Gates

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | comment classified after official process-token shape review; no source behavior change |
| Evidence | `Proc_CreateProcessInternalW` has image/config/command predicates that clear `hToken` before native process creation. The old source comments named these as MSEdge, Firefox, and Flash hacks, but the behavior shape is a local child-process token selection boundary. |
| Data | `Proc_CreateProcessInternalW`, `hToken`, `lpApplicationName`, `lpCommandLine`, `DeprecatedTokenHacks`, `DropChildProcessToken`, `DLL_IMAGE_GOOGLE_CHROME`, `DLL_IMAGE_MOZILLA_FIREFOX`, `DLL_IMAGE_ACROBAT_READER`, `DLL_IMAGE_PLUGIN_CONTAINER`, `--service-sandbox-type`, `-sandboxingKind`, and `__sys_CreateProcessInternalW`. |
| Schema | `PROC_CHILD_TOKEN_COMPATIBILITY_GATES` says public process creation either uses caller/default token shape or an explicit primary token shape; local `hToken` clearing is a process-token selection boundary, not a generic browser compatibility switch; Edge CDM token clearing stays under `DeprecatedTokenHacks`, `DLL_IMAGE_GOOGLE_CHROME`, and `--service-sandbox-type`; Firefox token clearing stays under `DLL_IMAGE_MOZILLA_FIREFOX` and `-sandboxingKind`; plugin-container / Acrobat token clearing stays under `DropChildProcessToken` or the existing image-type predicates; this SREV changes comments and proof only. |
| Topology | `caller process creation request -> Proc_CreateProcessInternalW -> existing image/config/command predicates -> hToken preserved or cleared -> native CreateProcessInternalW path`. |
| Logic Risk | Anonymous hack wording hides that each branch is a narrow token-selection gate. Future edits should not broaden, remove, or merge these predicates without Windows runtime proof for browser/plugin child-launch behavior, service port access, and DLL loading effects. |
| Official Shape | `docs/plan/srev-320-proc-child-token-compatibility-gates.md` records Microsoft `CreateProcessW`, `CreateProcessAsUserW`, and access-token references. `docs/plan/srev-320-proc-child-token-compatibility-gates.schema.json` records the JSON Schema draft-07 local `PROC_CHILD_TOKEN_COMPATIBILITY_GATES` contract. |
| Fix | Comment-only source clarification. The source now names the three branches as SREV-320 child-token gates and records that the existing predicates are the scope. No token value, condition, command-line predicate, image predicate, config setting, or native process-creation call changed. |
| Acceptance Gate | `docs/plan/check-srev-320.py` validates the draft-07 schema, official references, three source comments, preserved `DeprecatedTokenHacks` / Edge CDM predicate, preserved Firefox `-sandboxingKind` predicate, preserved plugin/Acrobat `DropChildProcessToken` predicate, stale hack wording removal from these branches, and split ledger fragment; `docs/plan/check-srev-320.sh` is the targeted wrapper. Windows gate: Edge/Chrome CDM service child launch, Firefox `-sandboxingKind` child launch, Acrobat/plugin-container child launch, `DeprecatedTokenHacks` negative smoke, and `DropChildProcessToken` negative smoke. |
