---
kind: srev-ledger-entry
id: SREV-297
title: GuiProp SetWindowLong Stub Opcode Comment
status: patched-comment-topology-after-srev-063-stub-parser-review-no-behavior-change
owner: Sandboxie/core/dll/guiprop.c
spec: docs/plan/srev-297-guiprop-setwindowlong-stub-opcode-comment.md
schema: docs/plan/srev-297-guiprop-setwindowlong-stub-opcode-comment.schema.json
checker: docs/plan/check-srev-297.py
runtime_gate: Inherited SREV-063 Windows x64 SetWindowLong* short-stub runtime proof
---

### SREV-297: GuiProp SetWindowLong Stub Opcode Comment

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after SREV-063 stub parser review; no behavior change |
| Evidence | `Gui_Hook_SetWindowLong8` and `Gui_Hook_SetWindowLongPtr8` parse Windows 8/8.1 era x64 `SetWindowLong*` short stubs. SREV-063 already owns the behavior fix and parser schema. The source comments still used `jmp xxx` placeholders. They were less precise than the SREV-063 schema and were being surfaced as comment-risk hits. |
| Data | `SetWindowLongA/W` and `SetWindowLongPtrA/W` export addresses, A/W prefix bytes, `E9 rel32`, branch offsets, derived worker target, `SetWindowLong8` / `SetWindowLongPtr8` hook install, and SREV-063. |
| Schema | `GUIPROP_SETWINDOWLONG_STUB_OPCODE_COMMENT` says SREV-063 owns `SetWindowLong8` and `SetWindowLongPtr8` stub parser behavior; the source opcode comments use `rel32` parser terms; `SetWindowLong` export executable bytes are a Sandboxie-local compatibility schema, not a Microsoft API contract; unknown `SetWindowLong` stub layouts still fail initialization; this SREV changes comments and proof only. |
| Topology | `SREV-063 behavior owner -> parser accepts full A/W prefixes and E9 rel32 -> unknown or changed layouts fail initialization`; `SREV-297 comment owner -> source opcode tables use the same rel32 term -> no parser behavior change`. |
| Logic Risk | The old `xxx` placeholders were ambiguous. They could be read as arbitrary bytes instead of the signed relative displacement form that the parser actually handles. The source should use the same vocabulary as the schema so future reviewers do not infer a wider accepted byte shape. |
| Official Shape | SREV-063 records the official API boundary: Microsoft documents `SetWindowLongA`, `SetWindowLongW`, `SetWindowLongPtrA`, and `SetWindowLongPtrW`, but does not document executable bytes at the export address. The executable-byte parser is therefore a Sandboxie-local compatibility schema, not a Win32 contract. |
| Fix | Comment-only source clarification. The source now names SREV-297 and replaces `jmp xxx` with `jmp rel32` in both `SetWindowLong8` and `SetWindowLongPtr8` opcode tables. No prefix checks, opcode checks, offset reads, target comparison, fallback gate, or hook installation changed. |
| Acceptance Gate | `docs/plan/check-srev-297.py` validates the draft-07 schema, official references, source opcode comments, unchanged full A-side prefix/opcode gates, unchanged W-side prefix/opcode gates, shared target comparisons, SREV-063 adjacency, stale `xxx` placeholder removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-297.sh` is the targeted wrapper. Runtime gate: inherited from SREV-063. Affected x64 Windows 8/8.1 `SetWindowLong*` short-stub hooks still need Windows runtime proof. |
