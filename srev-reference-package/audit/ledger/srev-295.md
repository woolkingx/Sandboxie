---
kind: srev-ledger-entry
id: SREV-295
title: GuiMsg Dispatch Stub Opcode Comment
status: patched-comment-topology-after-srev-062-stub-parser-review-no-behavior-change
owner: Sandboxie/core/dll/guimsg.c
spec: docs/plan/srev-295-guimsg-dispatch-stub-opcode-comment.md
schema: docs/plan/srev-295-guimsg-dispatch-stub-opcode-comment.schema.json
checker: docs/plan/check-srev-295.py
runtime_gate: Inherited SREV-062 Windows x64 DispatchMessageA/W short-stub runtime proof
---

### SREV-295: GuiMsg Dispatch Stub Opcode Comment

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-062 stub parser review; no behavior change |
| Evidence | `Gui_Hook_DispatchMessage8` parses Windows 8 era x64 `DispatchMessageA/W` short stubs. SREV-062 already owns the behavior fix and parser schema. The source comment still used `jmp xxx` / `jmp short xxx` placeholders. They were less precise than the SREV-062 schema and were being surfaced as comment-risk hits. |
| Data | `DispatchMessageA` export address, `DispatchMessageW` export address, A/W prefix bytes, `EB rel8`, `E9 rel32`, branch offsets, derived worker target, `DispatchMessage8` hook install, and SREV-062. |
| Schema | `GUIMSG_DISPATCH_STUB_OPCODE_COMMENT` says SREV-062 owns `DispatchMessage8` stub parser behavior; the source opcode comment uses `rel8` and `rel32` parser terms; `DispatchMessage` export executable bytes are a Sandboxie-local compatibility schema, not a Microsoft API contract; unknown `DispatchMessage` stub opcodes still fail closed; this SREV changes comments and proof only. |
| Topology | `SREV-062 behavior owner -> parser accepts EB rel8 and E9 rel32 -> unknown opcodes fail closed`; `SREV-295 comment owner -> source opcode table uses the same rel8 / rel32 terms -> no parser behavior change`. |
| Logic Risk | The old `xxx` placeholders were ambiguous. They could be read as arbitrary bytes instead of the signed relative displacement forms that the parser actually handles. The source should use the same vocabulary as the schema so future reviewers do not infer a wider accepted byte shape. |
| Official Shape | SREV-062 records the official API boundary: Microsoft documents `DispatchMessageA`, `DispatchMessageW`, and `GetProcAddress`, but does not document executable bytes at the export address. The executable-byte parser is therefore a Sandboxie-local compatibility schema, not a Win32 contract. |
| Fix | Comment-only source clarification. The source now names SREV-295 and replaces `jmp xxx` / `jmp short xxx` with `jmp rel32` / `jmp rel8`. No prefix checks, opcode checks, offset reads, target comparison, or hook installation changed. |
| Acceptance Gate | `docs/plan/check-srev-295.py` validates the draft-07 schema, official references, source opcode comment, unchanged `EB` / `E9` parser branches, shared target comparison, SREV-062 adjacency, stale `xxx` placeholder removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-295.sh` is the targeted wrapper. Runtime gate: inherited from SREV-062. Affected x64 Windows 8 era `DispatchMessageA/W` short-stub hooks still need Windows runtime proof. |
