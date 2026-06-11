---
kind: srev-ledger-entry
id: SREV-077
title: FormatMessage Insert Array Gate
status: patched-source-level-after-official-formatmessagew-argument-array-shape-and-loca
owner: Sandboxie/core/dll/support.c
spec: docs/plan/srev-077-format-message-insert-gate.md
schema: docs/plan/srev-077-format-message-insert-gate.schema.json
checker: docs/plan/check-srev-077.py
runtime_gate: "localized message with `.2.` and NULL inserts returns the first formatted string without crashing; localized message with valid inserts still rewrites `.2.` / `.3.` / `.4.` and frees the replaced output correctly"
---
### SREV-077: FormatMessage Insert Array Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `FormatMessageW` argument-array shape and local right-to-left `.N.` marker compatibility analysis; needs Windows localized message runtime proof |
| Evidence | `Sandboxie/core/dll/support.c` `SbieDll_FormatMessage_2` supports Hebrew/Arabic `.2.` / `.3.` / `.4.` markers by rewriting them into `%2` / `%3` / `%4` markers and running a second `FormatMessage` pass. Microsoft documents `FORMAT_MESSAGE_ARGUMENT_ARRAY` as making `Arguments` an array of insert values, with each insert sequence requiring a corresponding element; `FORMAT_MESSAGE_ALLOCATE_BUFFER` output is caller-owned and released with `LocalFree`. Before this patch, the compatibility path dereferenced `ins[1]` and `ins[2]` after finding `.2.` in the message text. `SbieDll_FormatMessage0` can call the same path with `ins == NULL`, so a localized message containing `.2.` could crash in the compatibility path instead of preserving the first formatted output. |
| Data | First `FormatMessage` output text, optional insert array, `.2.` / `.3.` / `.4.` marker scan, temporary rewritten text, second `FormatMessage` pass, replacement output buffer, and `LocalFree` ownership. |
| Schema | `FORMAT_MESSAGE_INSERT_ARRAY_GATE` says the second `FormatMessage` pass may run only when an insert array exists; NULL inserts have no legal owner for `%2` / `%3` / `%4` replacement values; markers inside insert strings remain rejected; successful replacement transfers output ownership and frees the old buffer. |
| Topology | `SbieDll_FormatMessage` obtains a first output buffer from `FormatMessage`; `SbieDll_FormatMessage_2` optionally rewrites local `.N.` markers and calls `FormatMessage` again with the insert array. The rewrite helper owns only this compatibility pass and may consume insert slots only after proving the insert-array boundary. |
| Logic Risk | A right-to-left text-file convenience marker should not turn a no-insert message lookup into a null pointer dereference. The old path treated a marker in message text as proof that `ins` existed, but the caller API allows `SbieDll_FormatMessage0` to request messages with no insert array. |
| Official Shape | `docs/plan/srev-077-format-message-insert-gate.md` records Microsoft `FormatMessageW` and `LocalFree` references. `docs/plan/srev-077-format-message-insert-gate.schema.json` records the JSON Schema draft-07 local `FORMAT_MESSAGE_INSERT_ARRAY_GATE` contract. |
| Fix | `SbieDll_FormatMessage_2` now returns `0` immediately when `ins` is NULL. That preserves the original formatted output and runs the second `FormatMessage` pass only when insert-array data exists. |
| Comment Contract | The source comment now names SREV-077's RTL marker compatibility pass and states that `.N.` markers are rewritten into `FormatMessage` inserts only when an insert array exists; this is a comment-only clarification with no behavior change. |
| Acceptance Gate | `docs/plan/check-srev-077.py` validates the draft-07 schema, official references, NULL insert-array gate before `ins[1]` / `ins[2]`, unchanged marker-in-insert rejection, unchanged output ownership transfer, and ledger entry; `docs/plan/check-srev-077.sh` is the matrix wrapper. Windows gate: localized message with `.2.` and NULL inserts returns the first formatted string without crashing; localized message with valid inserts still rewrites `.2.` / `.3.` / `.4.` and frees the replaced output correctly. |
