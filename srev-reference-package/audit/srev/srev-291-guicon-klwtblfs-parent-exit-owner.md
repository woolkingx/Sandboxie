# SREV-291: GuiCon klwtblfs Parent-Exit Owner

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/guicon.c`, `Sandboxie/core/dll/proc.c`, SREV-076, Microsoft thread-handle references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gui_InitConsole2` klwtblfs parent-exit helper |
| Acceptance gate | Targeted checker validates source comment, Kaspersky image gate, `Proc_WaitForParentExit` topology, proc.c adjacency, SREV-076 handoff adjacency, stale wording removal, and ledger fragment |

## Data

`Gui_InitConsole2` has a special image-name branch:

```text
Dll_ImageName == klwtblfs.exe
  -> CreateThread(... Proc_WaitForParentExit, (void *)1 ...)
  -> close returned thread handle if it exists
```

`Proc_WaitForParentExit((void *)1)` owns waiting for the parent and exiting this
process when the parent exits. Separately, `Proc_AlternateCreateProcess` blocks
`klwtblfs.exe` when SandboxieDcomLaunch is about to create it.

SREV-076 owns the main console helper thread handoff and cleanup. This branch is
adjacent but separate: it starts a parent-exit worker before the normal console
helper `Gui_ConsoleHwnd` gate.

## Official Shape

Microsoft documents `CreateThread` as creating a thread and returning a handle
to the new thread on success, or `NULL` on failure.

Microsoft documents `CloseHandle` as closing an open object handle. Closing a
thread handle does not terminate the associated thread; it only releases the
caller-owned handle reference.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createthread`
- `https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle`

## Schema

Local schema:

```text
docs/plan/srev-291-guicon-klwtblfs-parent-exit-owner.schema.json
```

Contract id:

```text
GUICON_KLWTBLFS_PARENT_EXIT_OWNER
```

## Boundary

```text
Gui_InitConsole2
  -> image-name predicate for klwtblfs.exe
  -> parent-exit worker thread
  -> Proc_WaitForParentExit(DoExitProcess=1)
```

The branch owns only the already-running image parent-exit helper. It does not
own DcomLaunch create-process blocking, normal console helper startup, or
Kaspersky compatibility policy outside this image-specific lifetime edge.

## Topology

```text
proc.c DcomLaunch create-process path
  -> blocks starting klwtblfs.exe

guicon.c already-running image path
  -> CreateThread(Proc_WaitForParentExit, DoExitProcess=1)
  -> CloseHandle(thread handle) after successful creation
  -> worker owns parent-exit process termination
```

## Logic Risk

The old comments used generic third-party and hack wording. That can hide the
actual owner split: `proc.c` handles create-process blocking, while `guicon.c`
only starts a parent-exit worker for an already-running image. Treating this as
a general console helper workaround could mix it with SREV-076's thread-handoff
resource ownership or remove the image-specific lifetime edge without proving
the DcomLaunch path covers every case.

## Fix

Comment-only source clarification. The source now names SREV-291, the
`klwtblfs.exe` parent-exit worker, the `proc.c` DcomLaunch create-process block,
and the `Proc_WaitForParentExit` `DoExitProcess` edge. No image predicate,
thread creation call, handle close, normal console helper handoff, or create
process policy changed.

## Acceptance Gate

`docs/plan/check-srev-291.py` validates the draft-07 schema, official
references, source comment, `_wcsicmp(Dll_ImageName, L"klwtblfs.exe")` gate,
`CreateThread(... Proc_WaitForParentExit, (void *)1 ...)`, thread-handle close,
`proc.c` DcomLaunch blocking adjacency, SREV-076 console helper adjacency,
stale wording removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows Kaspersky/klwtblfs compatibility matrix or equivalent
instrumented process-lifetime smoke proving SandboxieDcomLaunch blocking and
already-running parent-exit behavior, plus SREV-076 console helper regression
checks.
