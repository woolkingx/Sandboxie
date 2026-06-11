---
kind: srev-ledger-entry
id: SREV-063
title: GUI SetWindowLong Stub Parser Boundary
status: patched-source-level-after-official-setwindowlong-setwindowlongptr-shape-plus-lo
owner: Sandboxie/core/dll/guiprop.c
spec: docs/plan/srev-063-gui-set-window-long-stub-parser.md
schema: docs/plan/srev-063-gui-set-window-long-stub-parser.schema.json
checker: docs/plan/check-srev-063.py
runtime_gate: "affected x64 Windows 8/8.1 `SetWindowLong*` short-stub hooks still resolve when the accepted schema matches; unknown A-side layouts fail initialization instead of reading a displacement from unproven bytes"
---
### SREV-063: GUI SetWindowLong Stub Parser Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official SetWindowLong/SetWindowLongPtr shape plus local x64 short-stub parser analysis; needs Windows 8/8.1 era x64 user32 stub runtime proof |
| Evidence | `Sandboxie/core/dll/guiprop.c` `Gui_Hook_SetWindowLong8` and `Gui_Hook_SetWindowLongPtr8` read exported User32 entry bytes to derive internal hook targets. Microsoft documents the API parameter/return shapes, not the executable byte layout. Before this patch, the A-side parser checked only `41 B9 01 00` before reading a `rel32` at `a + 7`; it did not prove bytes 4-5 or the `E9` jump opcode at byte 6. The W-side parser already checked `45 33 C9 E9`. |
| Data | `SetWindowLongA/W` and `SetWindowLongPtrA/W` export addresses, A/W prefix bytes, A/W branch offsets, derived worker target, and `SetWindowLong8` / `SetWindowLongPtr8` hook install. |
| Schema | `GUI_SET_WINDOW_LONG_STUB_PARSER` says the local A-side parser accepts only `41 B9 01 00 00 00 E9 rel32`, while the W-side parser accepts `45 33 C9 E9 rel32`; branch offsets may be read only after the required local opcode shape is proven. |
| Topology | User32 export addresses flow into a Sandboxie-owned executable-byte parser, then into internal hook targets only after the local stub schema is proven. |
| Logic Risk | Reading a branch displacement from an unproven A-side instruction shape can derive a hook target from non-jump bytes when Microsoft changes a short stub layout or when an unexpected thunk/prologue appears. |
| Official Shape | `docs/plan/srev-063-gui-set-window-long-stub-parser.md` records Microsoft `SetWindowLongA/W` and `SetWindowLongPtrA/W` references. `docs/plan/srev-063-gui-set-window-long-stub-parser.schema.json` records the JSON Schema draft-07 local `GUI_SET_WINDOW_LONG_STUB_PARSER` contract. |
| Fix | Both `Gui_Hook_SetWindowLong8` and `Gui_Hook_SetWindowLongPtr8` now require the full A-side prefix plus `E9` opcode before reading `a + 7`. The Windows 10 build 10147 fallback in `Gui_Hook_SetWindowLong8` uses the same full A-side gate. |
| Acceptance Gate | `docs/plan/check-srev-063.py` validates the draft-07 schema, official references, full A-side prefix/opcode gates, W-side prefix/opcode preservation, fallback gating, and ledger entry; `docs/plan/check-srev-063.sh` is the matrix wrapper. Windows gate: affected x64 Windows 8/8.1 `SetWindowLong*` short-stub hooks still resolve when the accepted schema matches; unknown A-side layouts fail initialization instead of reading a displacement from unproven bytes. |
