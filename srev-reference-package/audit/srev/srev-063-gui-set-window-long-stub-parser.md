# SREV-063: GUI SetWindowLong Stub Parser Boundary

## Data

`Sandboxie/core/dll/guiprop.c` has custom x64 hook paths for Windows 8/8.1 era
`SetWindowLongA/W` and `SetWindowLongPtrA/W` short stubs. The hooks read the
exported function entry bytes, derive branch targets, and install an internal
`SetWindowLong8` or `SetWindowLongPtr8` hook when the local stub shape proves a
safe target.

The relevant data nodes are:

```text
SetWindowLongA export address
SetWindowLongW export address
SetWindowLongPtrA export address
SetWindowLongPtrW export address
A-stub prefix/opcode
W-stub prefix/opcode
A branch offset
W branch offset
derived worker target
SetWindowLong8 / SetWindowLongPtr8 hook install
```

## Official Shape

Microsoft documents `SetWindowLongA/W` as User32 APIs that change a window
attribute or 32-bit extra-window-memory value:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlonga
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongw
```

Microsoft documents `SetWindowLongPtrA/W` as pointer-sized variants for
32-bit/64-bit compatible code:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptra
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptrw
```

As with other exported User32 functions, these documents define the API
parameters and return values, not the executable byte layout at the export
address. The short-stub byte parser is a Sandboxie-local compatibility schema.

## Schema

Local schema:

```text
docs/plan/srev-063-gui-set-window-long-stub-parser.schema.json
```

The accepted local x64 stub shape is:

```text
A prefix/opcode: 41 B9 01 00 00 00 E9 rel32
W prefix/opcode: 45 33 C9 E9 rel32
```

The Windows 10 build 10147 fallback may use the W export address directly only
after the A-side prefix and `E9 rel32` opcode are fully proven.

## Topology

```text
User32 SetWindowLong* export address -> local stub parser -> derived worker target -> Sandboxie hook install
```

The parser owns executable-byte legality. `Gui_InitProp` owns the decision to
abort GUI property hook initialization if the parser cannot prove a safe target.

## Logic Risk

Before this patch, the A-side parser checked only the first four bytes of the
documented local stub comment (`41 B9 01 00`) before reading the `rel32` at
`a + 7`. It did not prove the remaining immediate bytes or the `E9` jump opcode
at `a[6]`. The W-side parser already included the `E9` opcode in its checked
four-byte prefix.

## Fix

`Gui_Hook_SetWindowLong8` and `Gui_Hook_SetWindowLongPtr8` now require the full
A-side local stub prefix and jump opcode before reading the branch displacement.
The Windows 10 build 10147 SetWindowLong fallback is gated by the same full
A-side proof.

## Acceptance Gate

`docs/plan/check-srev-063.py` validates the draft-07 schema, official reference
links, full A-side prefix/opcode gates in both hook parsers, preservation of the
W-side prefix/opcode gate, and the ledger entry.

Windows gate: affected x64 Windows 8/8.1 User32 `SetWindowLong*` short stubs
should still hook when the local stub schema matches. Unknown or changed A-side
stub layouts should fail initialization rather than reading a branch
displacement from an unproven instruction shape.
