---
kind: srev-ledger-entry
id: SREV-349
title: GUI ClipCursor Reply Contract
status: patched-source-level-after-official-clipcursor-reply-review-needs-windows-runtime-proof
owner: Sandboxie/core/svc/GuiWire.h
spec: docs/plan/srev-349-gui-clipcursor-reply-contract.md
schema: docs/plan/srev-349-gui-clipcursor-reply-contract.schema.json
checker: docs/plan/check-srev-349.py
runtime_gate: Windows SbieSvc and DLL build with brokered ClipCursor success, failure, NULL-release, and DPI context restore smoke
---

### SREV-349: GUI ClipCursor Reply Contract

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official ClipCursor reply review; needs Windows runtime proof |
| Evidence | Microsoft documents `ClipCursor` as a Win32 `BOOL` API that returns nonzero on success, zero on failure, and exposes failure detail through `GetLastError`; it also requires `WINSTA_WRITEATTRIBUTES` on the window station. Before this SREV, `Gui_ClipCursor` asked `Gui_CallProxy` for only `sizeof(ULONG)` and treated any reply as success, while `ClipCursorSlave` called `ClipCursor(rect)` and ignored the return value. A nearby TODO said to add a reply and return the real value. `Gui_CallProxy` treats a nonzero first reply `ULONG` as transport status, so `ClipCursor`'s `TRUE` cannot be placed in the first reply field. |
| Data | `Gui_ClipCursor`, `GUI_CLIP_CURSOR_REQ`, `GUI_CLIP_CURSOR_RPL`, `ClipCursorSlave`, `ClipCursor`, `GetLastError`, `SetLastError`, `Gui_CallProxy`, `Gui_ClipCursorActive`, `Gui_ResetClipCursor`, `GetThreadDpiAwarenessContext`, and `SetThreadDpiAwarenessContext`. |
| Schema | `GUI_CLIPCURSOR_REPLY_CONTRACT` says `ClipCursor` returns a Win32 `BOOL` and failure details are read through `GetLastError`; `GUI_CLIP_CURSOR` reply first `ULONG` is transport status and must remain zero for successful proxy transport; `ClipCursor` retval must be carried after status so `Gui_CallProxy` does not treat `TRUE` as an NTSTATUS failure; `ClipCursorSlave` executes the host-side call and captures retval plus error; `Gui_ClipCursor` returns the brokered retval and restores the brokered error with `SetLastError`; the DPI awareness context is temporarily applied in the service and restored after the call. |
| Topology | `sandboxed caller -> Gui_ClipCursor(lpRect) -> GUI_CLIP_CURSOR_REQ { have_rect, RECT, dpi_awareness_ctx } -> ClipCursorSlave -> optional SetThreadDpiAwarenessContext(request context) -> ClipCursor(rect or NULL) -> GUI_CLIP_CURSOR_RPL { status=0, error, retval } -> restore old DPI awareness context -> Gui_ClipCursor sets LastError and returns retval`. |
| Logic Risk | Returning success for a failed brokered `ClipCursor` violates the Win32 API shape and can make applications believe they own the shared cursor clip rectangle when SbieSvc failed to set it. A one-field `BOOL` reply would also collide with `Gui_CallProxy`'s first-field status convention. |
| Official Shape | Microsoft documents the `ClipCursor` return/error contract, shared cursor-resource release responsibility, `WINSTA_WRITEATTRIBUTES` access requirement, and DPI thread context set/restore shape. |
| Fix | `GuiWire.h` now defines `GUI_CLIP_CURSOR_RPL` with `status`, `error`, and `retval`. `ClipCursorSlave` records the service-side `ClipCursor` return value and failure error, sets `args->rpl_len`, and restores the previous DPI awareness context. `Gui_ClipCursor` now requests the full reply, returns `retval`, and restores `GetLastError` from the reply. |
| Acceptance Gate | `docs/plan/check-srev-349.py` validates the draft-07 schema, official references, `GUI_CLIP_CURSOR_RPL` ABI shape, `Gui_CallProxy` first-field status constraint, service-side `ClipCursor` `retval/error` capture, DLL-side `SetLastError` and `BOOL` return, stale TODO removal, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-349.sh` is the targeted wrapper. Runtime gate: Windows SbieSvc/DLL build plus `ClipCursor(&rect)` success and failure smoke proving brokered callers receive the same `BOOL` / `GetLastError` shape as native `ClipCursor`, including `ClipCursor(NULL)` release and DPI awareness restore behavior. |
