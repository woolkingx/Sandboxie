---
kind: srev-ledger-entry
id: SREV-075
title: WriteProcessMemory Workaround Output Gate
status: patched-source-level-after-official-writeprocessmemory-output-parameter-shape-an
owner: Sandboxie/core/dll/file_misc.c
spec: docs/plan/srev-075-file-wpm-output-gate.md
schema: docs/plan/srev-075-file-wpm-output-gate.schema.json
checker: docs/plan/check-srev-075.py
runtime_gate: "Firefox/Thunderbird suppressed `ntdll` patch write with NULL output, valid output, invalid output pointer, and non-workaround writes through the real API"
---
### SREV-075: WriteProcessMemory Workaround Output Gate

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `WriteProcessMemory` output-parameter shape and local Firefox/Thunderbird `ntdll` write-workaround analysis; needs Windows Firefox/Thunderbird runtime proof |
| Evidence | `Sandboxie/core/dll/file_misc.c` `File_WriteProcessMemory` has a Firefox/Thunderbird workaround that suppresses writes targeting `NtSetInformationThread` or `NtMapViewOfSection` in `ntdll` and returns success. Microsoft documents `WriteProcessMemory` `lpNumberOfBytesWritten` as optional output: NULL may be ignored; non-NULL receives bytes written; failure returns zero with error via `GetLastError`. Before this patch, the fake-success branch wrote `*lpNumberOfBytesWritten = nSize` directly, so an invalid caller output pointer could crash inside Sandboxie's workaround instead of failing the wrapper. |
| Data | `hProcess`, `lpBaseAddress`, `lpBuffer`, `nSize`, optional `lpNumberOfBytesWritten`, Firefox/Thunderbird image gate, selected `ntdll` target addresses, and real `__sys_WriteProcessMemory` fallback. |
| Schema | `FILE_WPM_WORKAROUND_OUTPUT_GATE` says NULL output is ignored, non-NULL output is a caller-owned slot that must be protected by the wrapper when the real API owner is bypassed, and bad output slots fail with `ERROR_NOACCESS` rather than crashing. |
| Topology | Caller `WriteProcessMemory` flows either into Sandboxie's local fake-success branch for a narrow Firefox/Thunderbird compatibility case or into the real Kernel32 owner. When Sandboxie claims success without calling the real owner, it owns preserving the output-parameter shape. |
| Logic Risk | A compatibility bypass should not convert a malformed output pointer into a local process crash. The old branch bypassed the real API owner and then performed an unguarded caller-output write. |
| Official Shape | `docs/plan/srev-075-file-wpm-output-gate.md` records Microsoft `WriteProcessMemory` references. `docs/plan/srev-075-file-wpm-output-gate.schema.json` records the JSON Schema draft-07 local `FILE_WPM_WORKAROUND_OUTPUT_GATE` contract. |
| Fix | The fake-success branch now writes `lpNumberOfBytesWritten` inside SEH. If the output write faults, the wrapper sets `ERROR_NOACCESS` and returns `FALSE`; NULL output and real fallback behavior remain unchanged. |
| Acceptance Gate | `docs/plan/check-srev-075.py` validates the draft-07 schema, official reference, workaround scope, SEH-gated output write, `ERROR_NOACCESS` failure, stale ungated output write removal, and unchanged real fallback; `docs/plan/check-srev-075.sh` is the matrix wrapper. Windows gate: Firefox/Thunderbird suppressed `ntdll` patch write with NULL output, valid output, invalid output pointer, and non-workaround writes through the real API. |
