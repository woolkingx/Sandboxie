# SREV-062: GUI DispatchMessage Stub Parser Boundary

## Data

`Sandboxie/core/dll/guimsg.c` has a custom x64 hook path for Windows 8 era
`DispatchMessageA` and `DispatchMessageW` short stubs. The hook reads the
exported function entry bytes, derives branch targets, and hooks the shared
`user32!DispatchMessageWorker` target when both stubs resolve to the same
address.

The relevant data nodes are:

```text
DispatchMessageA export address
DispatchMessageW export address
A-stub prefix/opcode
W-stub prefix/opcode
A branch offset
W branch offset
derived worker target
DispatchMessage8 hook install
```

## Official Shape

Microsoft documents `DispatchMessageA` and `DispatchMessageW` as same-shape
User32 APIs taking `const MSG *lpMsg` and returning `LRESULT`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-dispatchmessagea
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-dispatchmessagew
```

Microsoft documents `GetProcAddress` as returning an exported function or
variable address, or `NULL` on failure. It does not define the executable byte
layout at that address:

```text
https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress
```

Therefore the byte parser is a Sandboxie-local compatibility schema, not a
Win32 API contract. The parser must reject unknown local shapes before deriving
or comparing hook targets.

## Schema

Local schema:

```text
docs/plan/srev-062-gui-dispatch-message-stub-parser.schema.json
```

The accepted local x64 stub shape is:

```text
DispatchMessageA prefix: BA 01 00 00 00
DispatchMessageA opcode: EB rel8 or E9 rel32
DispatchMessageW prefix: 33 D2
DispatchMessageW opcode: EB rel8 or E9 rel32
A derived target == W derived target
```

Any other opcode shape is outside this local schema and must fail closed to the
normal `Gui_InitMsg` error path.

## Topology

```text
User32 export address -> local stub parser -> derived worker target -> Sandboxie hook install
```

The parser owns the executable-byte shape. `Gui_InitMsg` owns the decision to
abort GUI hook initialization if the parser cannot prove a safe worker target.

## Logic Risk

Before this patch, the A-stub offset was uninitialized when the A-side jump
opcode was neither `EB` nor `E9`. The W-side parser also allowed an unknown
opcode to continue as offset zero. A compatibility parser should not compare or
install a hook using a partially decoded or unknown executable shape.

## Fix

`Gui_Hook_DispatchMessage8` now initializes both offsets and returns `FALSE`
unless both the A and W stubs use one of the accepted jump opcodes. The hook
target is derived only after both sides have a schema-valid offset and resolve
to the same worker address.

## Acceptance Gate

`docs/plan/check-srev-062.py` validates the draft-07 schema, official reference
links, initialized offsets, fail-closed unknown-opcode branches for both A and W
stubs, the shared-target comparison, and the ledger entry.

Windows gate: affected x64 Windows 8 era user32 short stubs should still hook
the shared DispatchMessage worker when both stubs match the accepted schema.
Unknown or changed stub layouts should fail initialization rather than derive a
target from stale or uninitialized offset state.
