# SREV-295: GuiMsg Dispatch Stub Opcode Comment

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/guimsg.c`, SREV-062, Microsoft `DispatchMessageA/W` and `GetProcAddress` references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gui_Hook_DispatchMessage8` opcode documentation comment |
| Acceptance gate | Targeted checker validates source opcode wording, unchanged parser gates, SREV-062 adjacency, stale `xxx` placeholders removal, and ledger fragment |

## Data

`Gui_Hook_DispatchMessage8` parses Windows 8 era x64 `DispatchMessageA/W`
short stubs. SREV-062 already owns the behavior fix and parser schema:

```text
DispatchMessageA prefix: BA 01 00 00 00
DispatchMessageA opcode: EB rel8 or E9 rel32
DispatchMessageW prefix: 33 D2
DispatchMessageW opcode: EB rel8 or E9 rel32
A derived target == W derived target
```

The source comment still used `jmp xxx` / `jmp short xxx` placeholders. They
were not incorrect for humans, but they were less precise than the SREV-062
schema and were being surfaced as comment-risk hits.

## Official Shape

SREV-062 records the official API boundary: Microsoft documents
`DispatchMessageA`, `DispatchMessageW`, and `GetProcAddress`, but does not
document executable bytes at the export address. The executable-byte parser is
therefore a Sandboxie-local compatibility schema, not a Win32 contract.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-dispatchmessagea`
- `https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-dispatchmessagew`
- `https://learn.microsoft.com/en-us/windows/win32/api/libloaderapi/nf-libloaderapi-getprocaddress`

## Schema

Local schema:

```text
docs/plan/srev-295-guimsg-dispatch-stub-opcode-comment.schema.json
```

Contract id:

```text
GUIMSG_DISPATCH_STUB_OPCODE_COMMENT
```

## Boundary

```text
User32 export address
  -> Sandboxie-local byte parser
  -> accepted EB rel8 / E9 rel32 branch
  -> derived DispatchMessage worker hook target
```

The comment may document the local parser shape, but it must not imply a
Microsoft-owned executable-byte ABI.

## Topology

```text
SREV-062 behavior owner
  -> parser accepts EB rel8 and E9 rel32
  -> unknown opcodes fail closed

SREV-295 comment owner
  -> source opcode table uses the same rel8 / rel32 terms
  -> no parser behavior change
```

## Logic Risk

The old `xxx` placeholders were ambiguous. They could be read as arbitrary bytes
instead of the signed relative displacement forms that the parser actually
handles. The source should use the same vocabulary as the schema so future
reviewers do not infer a wider accepted byte shape.

## Fix

Comment-only source clarification. The source now names SREV-295 and replaces
`jmp xxx` / `jmp short xxx` with `jmp rel32` / `jmp rel8`. No prefix checks,
opcode checks, offset reads, target comparison, or hook installation changed.

## Acceptance Gate

`docs/plan/check-srev-295.py` validates the draft-07 schema, official
references, source opcode comment, unchanged `EB` / `E9` parser branches,
shared target comparison, SREV-062 adjacency, stale `xxx` placeholder removal,
combined ledger entry, and split ledger fragment.

Runtime gate: inherited from SREV-062. Affected x64 Windows 8 era
`DispatchMessageA/W` short-stub hooks still need Windows runtime proof.
