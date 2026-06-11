---
kind: srev-ledger-entry
id: SREV-146
title: Debug Format Buffer Termination
status: patched-source-level-after-official-vsnprintf-review-needs-windows-runtime-proof
owner: Sandboxie/core/dll/debug.c
spec: docs/plan/srev-146-debug-format-buffer-termination.md
schema: docs/plan/srev-146-debug-format-buffer-termination.schema.json
checker: docs/plan/check-srev-146.py
runtime_gate: Windows WITH_DEBUG DLL build and long debug-format runtime proof
---

### SREV-146: Debug Format Buffer Termination

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official `_vsnprintf` review; needs Windows DLL build/runtime proof |
| Evidence | `Sandboxie/core/dll/debug.c` was the top unnamed reviewable core file after SREV-145. `Sandboxie/core/dll/SboxDll.vcxproj` defines `WITH_DEBUG`, so `DbgPrint` and `DbgTrace` are part of the DLL build surface. Before this SREV, both helpers passed `sizeof(tmp1)` to `P_vsnprintf` and then consumed `tmp1` as a C string through `OutputDebugStringA` or `%S` conversion. Microsoft documents `_vsnprintf` as not null-terminating the buffer when output is truncated. |
| Data | `WITH_DEBUG`, `DbgPrint`, `DbgTrace`, `P_vsnprintf`, `_vsnprintf`, `tmp1[510]`, `OutputDebugStringA`, `Sbie_snwprintf`, and `SbieApi_MonitorPutMsg`. |
| Schema | `DEBUG_FORMAT_BUFFER_TERMINATION` says the debug helpers own the local stack buffer before any string-consuming debug or monitor API reads it; `_vsnprintf` is counted but does not guarantee null termination on truncation; callers must reserve one byte with `sizeof(tmp1) - 1`, initialize the buffer, and force the final byte to `'\0'` after formatting. |
| Topology | Legal flow is variadic debug format, local `tmp1`, `_vsnprintf` with one byte reserved, forced final terminator, then `OutputDebugStringA` or `Sbie_snwprintf` / `SbieApi_MonitorPutMsg`. |
| Logic Risk | A long debug format string could leave `tmp1` unterminated and make the debug output path read past the stack buffer while writing debug output or converting to a wide monitor message. |
| Official Shape | `docs/plan/srev-146-debug-format-buffer-termination.md` records the Microsoft `_vsnprintf` reference. `docs/plan/srev-146-debug-format-buffer-termination.schema.json` records the JSON Schema draft-07 local `DEBUG_FORMAT_BUFFER_TERMINATION` contract. |
| Fix | `DbgPrint` and `DbgTrace` now initialize `tmp1[0]`, pass `sizeof(tmp1) - 1` to `P_vsnprintf`, and force `tmp1[sizeof(tmp1) - 1] = '\0'` before string consumers read the buffer. |
| Acceptance Gate | `docs/plan/check-srev-146.py` validates the draft-07 schema, official reference, `WITH_DEBUG` project definition, both debug helper termination patterns, and the ledger fragment; `docs/plan/check-srev-146.sh` is the matrix wrapper. Runtime/build gate: Windows DLL build with `WITH_DEBUG`; long formatted debug strings through `DbgPrint` and `DbgTrace` truncate cleanly without reading past `tmp1`; normal short debug strings still reach `OutputDebugStringA` and `SbieApi_MonitorPutMsg`. |
