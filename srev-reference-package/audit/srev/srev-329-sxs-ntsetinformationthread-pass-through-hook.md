# SREV-329: SXS NtSetInformationThread Pass-Through Hook

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/sxs.c`, `Sandboxie/core/dll/gui.c`, `Sandboxie/core/drv/thread_token.c`, Microsoft `ZwSetInformationThread` reference |
| Output artifact | `docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.schema.json`, `docs/plan/check-srev-329.py`, `docs/plan/check-srev-329.sh`, ledger fragment, comment-only source clarification |
| Owner | `Sandboxie/core/dll/sxs.c` `NtSetInformationThread` pass-through hook |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Data

`Sandboxie/core/dll/sxs.c` installs an `NtSetInformationThread` hook from
`Sxs_InitKernel32`. The hook body does not alter arguments or status; it calls
`__sys_NtSetInformationThread` directly. The old comment said the Opera-specific
reason seemed no longer required, but the hook still changes call topology by
routing calls through Sandboxie's hook table and then to the saved native entry.

The relevant data nodes are:

```text
Sxs_InitKernel32
GetProcAddress(Dll_Ntdll, "NtSetInformationThread")
SBIEDLL_HOOK(Sxs_, NtSetInformationThread)
Sxs_NtSetInformationThread
__sys_NtSetInformationThread
ThreadHandle
ThreadInformationClass
ThreadInformation
ThreadInformationLength
Gui_ConnectToWindowStationAndDesktop reference path
Thread_SetInformationThread_ChangeNotifyToken driver path
```

## Official Shape

Microsoft documents `ZwSetInformationThread` / `NtSetInformationThread` as
receiving a thread handle, a `THREADINFOCLASS`, an information pointer, and a
buffer length, and returning `STATUS_SUCCESS` or an NTSTATUS error.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntddk/nf-ntddk-zwsetinformationthread
```

The same reference states that user-mode callers use the `NtSetInformationThread`
name. Sandboxie's local hook may bypass another user-mode patch, but it must
preserve the native call's argument and return-value shape.

## Schema

Local schema:

```text
docs/plan/srev-329-sxs-ntsetinformationthread-pass-through-hook.schema.json
```

`SXS_NTSETINFORMATIONTHREAD_PASS_THROUGH_HOOK` says:

- `NtSetInformationThread` owns the thread-information transition and NTSTATUS
  result;
- the SXS wrapper is a pass-through hook that must not rewrite arguments or
  statuses;
- the hook changes call topology even when it preserves native semantics;
- the adjacent GUI/driver comments define why the change-notify-token path may
  need a direct saved native entry;
- removing the hook requires Windows browser/runtime proof;
- this SREV changes comments and proof only.

## Topology

```text
Sxs_InitKernel32
  -> GetProcAddress(Dll_Ntdll, "NtSetInformationThread")
  -> SBIEDLL_HOOK(Sxs_, NtSetInformationThread)
  -> Sxs_NtSetInformationThread
  -> __sys_NtSetInformationThread(arguments unchanged)
  -> native NTSTATUS result
```

Adjacent evidence:

```text
Gui_ConnectToWindowStationAndDesktop
  -> change-notify-token path
  -> __sys_NtSetInformationThread if available
  -> NtSetInformationThread fallback

driver Thread_SetInformationThread_ChangeNotifyToken
  -> handles the special info class path
```

## Logic Risk

The old comment mixed an Opera-specific historical reason with a claim that the
path may no longer be required. Because the hook remains active, that comment
can misroute future work into deleting it as stale cleanup. The local contract
is narrower: the hook is a pass-through topology guard. It should preserve the
native `NtSetInformationThread` argument/result shape until a Windows runtime
matrix proves it can be removed.

## Fix

Comment-only source clarification. The source now names SREV-329 and states
that the hook is a narrow `NtSetInformationThread` pass-through guard for the
change-notify-token path referenced by `Gui_ConnectToWindowStationAndDesktop`.
It also records that removal needs Windows browser matrix proof because the hook
still changes call topology.

No `GetProcAddress`, `SBIEDLL_HOOK`, wrapper function signature, argument
forwarding, native `__sys_NtSetInformationThread` call, return value, or
adjacent GUI/driver change-notify-token behavior changed.

## Acceptance Gate

`docs/plan/check-srev-329.py` validates the draft-07 schema, official
reference, pass-through wrapper, hook installation, adjacent GUI/driver
change-notify-token evidence, stale Opera/workaround wording removal, combined
ledger entry, and split ledger fragment.

Windows gate: browser/runtime matrix covering Opera-like patched NTAPI stubs
and modern Chromium/Firefox/Thunderbird scenarios should prove whether removing
the SXS `NtSetInformationThread` pass-through hook preserves the
change-notify-token path and does not regress normal thread-information calls.
