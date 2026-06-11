---
kind: srev-ledger-entry
id: SREV-066
title: Low-Level Hotpatch Scan Window
status: patched-source-level-after-official-readprocessmemory-byte-transfer-shape-and-lo
owner: Sandboxie/core/dll/lowlevel_inject.c
spec: docs/plan/srev-066-lowlevel-hotpatch-scan-window.md
schema: docs/plan/srev-066-lowlevel-hotpatch-scan-window.schema.json
checker: docs/plan/check-srev-066.py
runtime_gate: "normal nearby allocation path unchanged, fallback scan still finds valid 8-byte hotpatch slots, fallback failure returns `NULL`, and repeated fallback attempts do not read beyond the local buffer"
---
### SREV-066: Low-Level Hotpatch Scan Window

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official `ReadProcessMemory` byte-transfer shape and local fallback hotpatch scan analysis; needs Windows x64 injection fallback runtime proof |
| Evidence | `Sandboxie/core/dll/lowlevel_inject.c` `SbieDll_InjectLow_getPage` reads a remote memory range into local `short myBuffer[1024]`, checks that `ReadProcessMemory` transferred `sizeof(myBuffer)` bytes, then scans for an 8-byte `0x90`/`0xcc` hotpatch slot. Microsoft documents `ReadProcessMemory` as copying `nSize` bytes into the caller-provided buffer. Before this patch, the scan loop used `i < sizeof(myBuffer)` while reading an `ULONG_PTR` at `&myBuffer[i]`; because `myBuffer` is a `short[]`, the index was not byte-oriented and the final windows could read beyond the local buffer. Later comment cleanup also found stale generic hack wording in the same fallback scan block. |
| Data | Remote read base address, local `myBuffer` byte capacity, `ReadProcessMemory` byte count, `ULONG_PTR` pattern width, scan start offset, and selected remote hotpatch table address. |
| Schema | `LOWLEVEL_HOTPATCH_SCAN_WINDOW` says an `ULONG_PTR` pattern may be read only when `scan_offset + sizeof(ULONG_PTR) <= sizeof(myBuffer)`, and scan offsets must be byte offsets because the selected remote address is byte-oriented. Fallback comments must name SREV-066 instead of generic hack wording. |
| Topology | Remote process memory flows through `ReadProcessMemory` into a local buffer; the local scanner maps byte offsets to candidate remote patch-table addresses. The scanner owns bounds for every `ULONG_PTR` pattern read. |
| Logic Risk | A fallback hotpatch search should not make process injection depend on undefined local buffer reads. The previous element-indexed loop could search beyond the bytes proven by `ReadProcessMemory`, especially near the end of the buffer. |
| Official Shape | `docs/plan/srev-066-lowlevel-hotpatch-scan-window.md` records Microsoft `ReadProcessMemory` references. `docs/plan/srev-066-lowlevel-hotpatch-scan-window.schema.json` records the JSON Schema draft-07 local `LOWLEVEL_HOTPATCH_SCAN_WINDOW` contract. |
| Fix | The fallback scan now uses a byte `SIZE_T` offset, limits starts to full `ULONG_PTR` windows inside `myBuffer`, reads patterns through `(UCHAR *)myBuffer + i`, and keeps the remote table address byte-oriented. The fallback comments now name SREV-066 instead of generic hack wording. |
| Acceptance Gate | `docs/plan/check-srev-066.py` validates the draft-07 schema, official reference, full-window loop bound, byte-addressed pattern reads, stale element-indexed scan removal, generic hack wording removal from this fallback scan block, and ledger entry; `docs/plan/check-srev-066.sh` is the matrix wrapper. Windows gate: normal nearby allocation path unchanged, fallback scan still finds valid 8-byte hotpatch slots, fallback failure returns `NULL`, and repeated fallback attempts do not read beyond the local buffer. |
