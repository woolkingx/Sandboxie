---
kind: srev-ledger-entry
id: SREV-291
title: GuiCon klwtblfs Parent-Exit Owner
status: patched-comment-topology-after-proc-dcomlaunch-and-srev-076-parent-exit-review-no-behavior-change
owner: Sandboxie/core/dll/guicon.c
spec: docs/plan/srev-291-guicon-klwtblfs-parent-exit-owner.md
schema: docs/plan/srev-291-guicon-klwtblfs-parent-exit-owner.schema.json
checker: docs/plan/check-srev-291.py
runtime_gate: Windows Kaspersky klwtblfs compatibility or instrumented process-lifetime smoke plus SREV-076 console helper regression checks
---

### SREV-291: GuiCon klwtblfs Parent-Exit Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched comment/topology after proc.c DcomLaunch and SREV-076 parent-exit review; no behavior change |
| Evidence | `Gui_InitConsole2` has an image-specific `klwtblfs.exe` branch that starts `Proc_WaitForParentExit` with `(void *)1` and closes the returned thread handle if creation succeeds. `proc.c` separately blocks `klwtblfs.exe` from the SandboxieDcomLaunch create-process path. SREV-076 owns the normal console helper thread handoff. The old comments described this as a generic third-party workaround/hack instead of naming the parent-exit owner split. |
| Data | `Dll_ImageName`, `klwtblfs.exe`, `CreateThread`, `Proc_WaitForParentExit`, `DoExitProcess`, thread handle, `CloseHandle`, `Dll_ImageType == DLL_IMAGE_SANDBOXIE_DCOMLAUNCH`, `Proc_AlternateCreateProcess`, and SREV-076 console helper handoff. |
| Schema | `GUICON_KLWTBLFS_PARENT_EXIT_OWNER` says `Gui_InitConsole2` owns only the already-running `klwtblfs.exe` parent-exit worker branch; `proc.c` owns SandboxieDcomLaunch create-process blocking for `klwtblfs.exe`; `Proc_WaitForParentExit` owns waiting for the parent and exiting when `DoExitProcess` is enabled; SREV-076 owns normal console helper handoff and cleanup; `CreateThread` failure preserves the existing fall-through behavior; this SREV changes comments and proof only. |
| Topology | `proc.c DcomLaunch create-process path -> blocks starting klwtblfs.exe`; `guicon.c already-running image path -> CreateThread(Proc_WaitForParentExit, DoExitProcess=1) -> CloseHandle(thread handle) after successful creation -> worker owns parent-exit process termination`. |
| Logic Risk | Generic third-party wording hides the owner split and can lead future work to remove the already-running parent-exit edge because `proc.c` blocks one create-process path, or to mix this image-specific worker with SREV-076's normal console helper resource ownership. |
| Official Shape | Microsoft documents `CreateThread` as returning a thread handle or `NULL` and `CloseHandle` as closing a caller-owned handle without terminating the associated thread. |
| Fix | Comment-only source clarification. The source now names SREV-291, the `klwtblfs.exe` parent-exit worker, the `proc.c` DcomLaunch create-process block, and the `Proc_WaitForParentExit` `DoExitProcess` edge. No image predicate, thread creation call, handle close, normal console helper handoff, or create-process policy changed. |
| Acceptance Gate | `docs/plan/check-srev-291.py` validates the draft-07 schema, official references, source comment, `_wcsicmp(Dll_ImageName, L"klwtblfs.exe")` gate, `CreateThread(... Proc_WaitForParentExit, (void *)1 ...)`, thread-handle close, `proc.c` DcomLaunch blocking adjacency, SREV-076 console helper adjacency, stale wording removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-291.sh` is the targeted wrapper. Runtime gate: Windows Kaspersky/klwtblfs compatibility matrix or equivalent instrumented process-lifetime smoke proving SandboxieDcomLaunch blocking and already-running parent-exit behavior, plus SREV-076 console helper regression checks. |
