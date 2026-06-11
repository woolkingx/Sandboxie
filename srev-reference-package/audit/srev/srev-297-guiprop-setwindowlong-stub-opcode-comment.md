# SREV-297: GuiProp SetWindowLong Stub Opcode Comment

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/guiprop.c`, SREV-063, Microsoft `SetWindowLongA/W` and `SetWindowLongPtrA/W` references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gui_Hook_SetWindowLong8` / `Gui_Hook_SetWindowLongPtr8` opcode documentation comments |
| Acceptance gate | Targeted checker validates source opcode wording, unchanged parser gates, SREV-063 adjacency, stale `xxx` placeholders removal, and ledger fragment |

## Data

`Gui_Hook_SetWindowLong8` and `Gui_Hook_SetWindowLongPtr8` parse Windows 8/8.1
era x64 `SetWindowLong*` short stubs. SREV-063 already owns the behavior fix
and parser schema:

```text
SetWindowLongA/PtrA prefix: 41 B9 01 00 00 00
SetWindowLongA/PtrA opcode: E9 rel32
SetWindowLongW/PtrW prefix: 45 33 C9
SetWindowLongW/PtrW opcode: E9 rel32
A derived target == W derived target
```

The source comments still used `jmp xxx` placeholders. They were less precise
than the SREV-063 schema and were being surfaced as comment-risk hits.

## Official Shape

SREV-063 records the official API boundary: Microsoft documents
`SetWindowLongA`, `SetWindowLongW`, `SetWindowLongPtrA`, and
`SetWindowLongPtrW` as User32 APIs for changing window attributes or extra
window-memory values. Microsoft documents the API parameters and return values,
not the executable bytes at the export address. The executable-byte parser is
therefore a Sandboxie-local compatibility schema, not a Win32 contract.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlonga`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongw`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptra`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwindowlongptrw`

## Schema

Local schema:

```text
docs/plan/srev-297-guiprop-setwindowlong-stub-opcode-comment.schema.json
```

Contract id:

```text
GUIPROP_SETWINDOWLONG_STUB_OPCODE_COMMENT
```

## Boundary

```text
User32 SetWindowLong* export address
  -> Sandboxie-local byte parser
  -> accepted E9 rel32 branch
  -> derived SetWindowLong8 / SetWindowLongPtr8 hook target
```

The comment may document the local parser shape, but it must not imply a
Microsoft-owned executable-byte ABI.

## Topology

```text
SREV-063 behavior owner
  -> parser accepts the full A/W prefixes and E9 rel32
  -> unknown or changed layouts fail initialization

SREV-297 comment owner
  -> source opcode tables use the same rel32 term
  -> no parser behavior change
```

## Logic Risk

The old `xxx` placeholders were ambiguous. They could be read as arbitrary
bytes instead of the signed relative displacement form that the parser actually
handles. The source should use the same vocabulary as the schema so future
reviewers do not infer a wider accepted byte shape.

## Fix

Comment-only source clarification. The source now names SREV-297 and replaces
`jmp xxx` with `jmp rel32` in both `SetWindowLong8` and
`SetWindowLongPtr8` opcode tables. No prefix checks, opcode checks, offset
reads, target comparison, fallback gate, or hook installation changed.

## Acceptance Gate

`docs/plan/check-srev-297.py` validates the draft-07 schema, official
references, source opcode comments, unchanged full A-side prefix/opcode gates,
unchanged W-side prefix/opcode gates, shared target comparisons, SREV-063
adjacency, stale `xxx` placeholder removal, combined ledger entry, and split
ledger fragment.

Runtime gate: inherited from SREV-063. Affected x64 Windows 8/8.1
`SetWindowLong*` short-stub hooks still need Windows runtime proof.
