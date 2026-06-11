---
kind: srev-ledger-entry
id: SREV-062
title: GUI DispatchMessage Stub Parser Boundary
status: patched-source-level-after-official-dispatchmessagea-w-and-getprocaddress-shape-
owner: Sandboxie/core/dll/guimsg.c
spec: docs/plan/srev-062-gui-dispatch-message-stub-parser.md
schema: docs/plan/srev-062-gui-dispatch-message-stub-parser.schema.json
checker: docs/plan/check-srev-062.py
runtime_gate: "affected x64 Windows 8 era `DispatchMessageA/W` short-stub hook still resolves to the shared worker; unknown or changed stub layouts fail initialization instead of deriving a target from invalid offset state"
---
### SREV-062: GUI DispatchMessage Stub Parser Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official DispatchMessageA/W and GetProcAddress shape plus local x64 short-stub parser analysis; needs Windows 8 era x64 user32 stub runtime proof |
| Evidence | `Sandboxie/core/dll/guimsg.c` `Gui_Hook_DispatchMessage8` reads the exported `DispatchMessageA` and `DispatchMessageW` entry bytes to derive a shared `user32!DispatchMessageWorker` hook target. Microsoft documents the A/W APIs and exported-address lookup, but not executable entry-byte layout. Before this patch, an unknown A-side jump opcode left `a_offset` uninitialized, and an unknown W-side opcode continued as offset zero. |
| Data | `DispatchMessageA` export address, `DispatchMessageW` export address, A/W prefix bytes, A/W jump opcodes, A/W branch offsets, derived worker target, and `DispatchMessage8` hook install. |
| Schema | `GUI_DISPATCH_MESSAGE_STUB_PARSER` says the local parser accepts only the known A prefix plus `EB rel8`/`E9 rel32` and the known W prefix plus `EB rel8`/`E9 rel32`; unknown opcodes must fail closed before target comparison. |
| Topology | User32 export addresses flow into a Sandboxie-owned executable-byte parser, then into the derived worker hook target only after both sides match the local schema and resolve to the same address. |
| Logic Risk | A compatibility hook should not install or compare targets from partially decoded executable bytes. Continuing with an uninitialized or synthetic offset can corrupt the hook target decision when Microsoft changes a short stub layout. |
| Official Shape | `docs/plan/srev-062-gui-dispatch-message-stub-parser.md` records Microsoft `DispatchMessageA`, `DispatchMessageW`, and `GetProcAddress` references. `docs/plan/srev-062-gui-dispatch-message-stub-parser.schema.json` records the JSON Schema draft-07 local `GUI_DISPATCH_MESSAGE_STUB_PARSER` contract. |
| Fix | `Gui_Hook_DispatchMessage8` now initializes both offsets and returns `FALSE` unless both A and W stubs have accepted `EB` or `E9` jump opcodes. Hook installation remains gated on A/W derived-target equality. |
| Acceptance Gate | `docs/plan/check-srev-062.py` validates the draft-07 schema, official references, initialized offsets, fail-closed branches for unknown A/W opcodes, shared-target comparison, and ledger entry; `docs/plan/check-srev-062.sh` is the matrix wrapper. Windows gate: affected x64 Windows 8 era `DispatchMessageA/W` short-stub hook still resolves to the shared worker; unknown or changed stub layouts fail initialization instead of deriving a target from invalid offset state. |
