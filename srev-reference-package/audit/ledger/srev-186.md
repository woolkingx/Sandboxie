---
kind: srev-ledger-entry
id: SREV-186
title: Syscall Query Name Slot Boundary
status: patched-source-level-after-official-pe-export-name-shape-review-needs-windows-syscall-query-runtime-proof
owner: Sandboxie/core/drv/syscall.h
spec: docs/plan/srev-186-syscall-query-name-slot-boundary.md
schema: docs/plan/srev-186-syscall-query-name-slot-boundary.schema.json
checker: docs/plan/check-srev-186.py
runtime_gate: Windows driver build, API_QUERY_SYSCALLS add_names=0/add_names=1 smoke for native NT and win32k tables, and DLL consumer compatibility smoke
---
### SREV-186: Syscall Query Name Slot Boundary

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official PE export-name shape review; needs Windows syscall query runtime proof |
| Evidence | `Sandboxie/core/drv/syscall.h` was the highest-ranked unnamed reviewable core file after SREV-185. `syscall.c` and `syscall_win32.c` enumerate PE export names, cap names with a literal `64`, allocate an optional query name slot of exactly 64 bytes, copy `entry->name_len` bytes, then write a terminator at `((char*)ptr)[entry->name_len]`. If an export name after the `Zw` or `Nt` prefix is exactly 64 bytes, the terminator write lands one byte past the name slot. Microsoft PE/COFF documents export/import names as ASCII strings terminated by a null byte; the fixed 64-byte query slot is a Sandboxie ABI, not a Microsoft guarantee. |
| Data | `Sandboxie/core/drv/syscall.h`, `Sandboxie/core/drv/syscall.c`, `Sandboxie/core/drv/syscall_win32.c`, `Sandboxie/core/drv/syscall_util.c`, `SYSCALL_ENTRY.name_len`, `SYSCALL_ENTRY.name`, `Syscall_Init_List`, `Syscall_Init_List32`, `Syscall_Api_Query`, `Syscall_Api_Query32`, `Syscall_HookMapMatch`, `Syscall_Api_Invoke`, `SYSCALL_NAME_SLOT_ULONGS`, `SYSCALL_NAME_SLOT_BYTES`, and `SYSCALL_NAME_MAX_CHARS`. |
| Schema | `SYSCALL_QUERY_NAME_SLOT_BOUNDARY` says PE export names are input strings owned by the Windows image export table; Microsoft PE/COFF documents export and import names as ASCII strings terminated by a null byte; Sandboxie owns the syscall query wire slot that appends an optional syscall name after `{index, offset}`; the query name slot is exactly 16 `ULONG` values, or 64 bytes; stored syscall names must be at most 63 bytes so the terminator byte remains inside the 64-byte slot; NTDLL `Zw*` and WIN32U `Nt*` enumeration use the same local name-length limit; query buffer size and pointer advancement use the same named slot contract; hook-map conversion and name-based syscall lookup use the same maximum name contract; syscall index extraction, hook policy, service-table discovery, dispatch, and the external query slot size must not change. |
| Topology | Legal syscall name flow is `PE export name table` -> `Dll_GetNextProc` -> strip `Zw` or `Nt` prefix -> cap stored `SYSCALL_ENTRY.name_len` at `SYSCALL_NAME_MAX_CHARS` -> store name plus local terminator -> optional `API_QUERY_SYSCALLS` name slot -> copy name bytes -> write terminator inside the 64-byte slot -> advance by `SYSCALL_NAME_SLOT_ULONGS`. |
| Logic Risk | The old code treated a 64-byte payload slot as both payload capacity and payload-plus-terminator capacity. That is only safe when the stored name length is less than 64. A 64-byte post-prefix export name could corrupt the next query field by one byte, and the literal size repeated across enumeration, query packing, hook-map conversion, and name-based lookup made the ABI contract easy to drift again. |
| Official Shape | `docs/plan/srev-186-syscall-query-name-slot-boundary.md` records the Microsoft PE/COFF reference for null-terminated ASCII export/import names. `docs/plan/srev-186-syscall-query-name-slot-boundary.schema.json` records the JSON Schema draft-07 local `SYSCALL_QUERY_NAME_SLOT_BOUNDARY` contract. |
| Fix | `syscall.h` now defines `SYSCALL_NAME_SLOT_ULONGS`, `SYSCALL_NAME_SLOT_BYTES`, `SYSCALL_NAME_MAX_CHARS`, and `SYSCALL_NAME_LOG_CHARS`. `syscall.c` and `syscall_win32.c` now cap enumerated names at `SYSCALL_NAME_MAX_CHARS`, pack optional query names into `SYSCALL_NAME_SLOT_BYTES`, and advance output pointers by `SYSCALL_NAME_SLOT_ULONGS`. The name-based invoke path rejects names longer than `SYSCALL_NAME_MAX_CHARS`, and `syscall_util.c` uses the same maximum for hook-map matching. |
| Acceptance Gate | `docs/plan/check-srev-186.py` validates the draft-07 schema, official reference, shared name-slot constants, native and win32k enumeration limits, query slot sizing and advancement, in-slot terminator write, name-based lookup limit, hook-map conversion limit, and ledger fragment; `docs/plan/check-srev-186.sh` is the matrix wrapper. Runtime gate: Windows driver build, `API_QUERY_SYSCALLS` smoke with `add_names=0` and `add_names=1` for native NT and win32k tables, and DLL consumer compatibility smoke. |
