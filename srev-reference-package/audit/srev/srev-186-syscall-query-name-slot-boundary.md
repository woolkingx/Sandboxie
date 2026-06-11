# SREV-186: Syscall Query Name Slot Boundary

## Data

Owner files:

```text
Sandboxie/core/drv/syscall.h
Sandboxie/core/drv/syscall.c
Sandboxie/core/drv/syscall_win32.c
Sandboxie/core/drv/syscall_util.c
```

Reviewed nodes:

```text
SYSCALL_ENTRY.name_len
SYSCALL_ENTRY.name
Syscall_Init_List
Syscall_Init_List32
Syscall_Api_Query
Syscall_Api_Query32
Syscall_HookMapMatch
Syscall_Api_Invoke
SYSCALL_NAME_SLOT_ULONGS
SYSCALL_NAME_SLOT_BYTES
SYSCALL_NAME_MAX_CHARS
```

## Schema

`SYSCALL_QUERY_NAME_SLOT_BOUNDARY` defines these local contracts:

- PE export names are input strings owned by the Windows image export table.
- Microsoft PE/COFF documents export and import names as ASCII strings terminated by a null byte.
- Sandboxie owns the syscall query wire slot that appends an optional syscall name after `{index, offset}`.
- The query name slot is exactly 16 `ULONG` values, or 64 bytes.
- Stored syscall names must be at most 63 bytes so the terminator byte remains inside the 64-byte slot.
- NTDLL `Zw*` and WIN32U `Nt*` enumeration use the same local name-length limit.
- Query buffer size and pointer advancement must use the same named slot contract.
- Hook-map conversion and name-based syscall lookup must use the same maximum name contract.
- This SREV does not change syscall index extraction, hook policy, service-table discovery, syscall dispatch, or the external query slot size.
- Windows build/runtime proof is required.

## Topology

The syscall name path is:

```text
PE export name table
  -> Dll_GetNextProc
  -> strip Zw or Nt prefix
  -> cap stored SYSCALL_ENTRY.name_len at SYSCALL_NAME_MAX_CHARS
  -> store name plus local terminator
  -> optional API_QUERY_SYSCALLS name slot
  -> copy name bytes
  -> write terminator inside the 64-byte slot
  -> advance by SYSCALL_NAME_SLOT_ULONGS
```

The slot remains ABI-compatible with existing consumers because the externally
visible slot size stays 64 bytes.

## Logic Risk

Before this SREV, NTDLL and WIN32U enumeration accepted `name_len == 64`.
`Syscall_Api_Query` and `Syscall_Api_Query32` allocated exactly 64 bytes for the
optional name slot, copied `entry->name_len` bytes, and then wrote a terminator
at `((char*)ptr)[entry->name_len]`.

If an export name after the `Zw` or `Nt` prefix had exactly 64 bytes, the copied
payload filled the slot and the terminator write landed one byte into the next
query field. The same literal `64` also existed in hook-map conversion and the
name-based invoke path, so the local name-size contract was implicit instead of
owned by `syscall.h`.

## Official Shape

Microsoft PE/COFF documents export symbol information through the export
directory and names exported symbols through export name pointer/table data.
The PE format page documents export/import names as ASCII strings terminated by
a null byte; it does not impose Sandboxie's 64-byte query slot.

Therefore the official input shape is variable-length null-terminated ASCII,
while the local output shape is the Sandboxie-owned 16-`ULONG` query slot.

Source:

- https://learn.microsoft.com/en-us/windows/win32/debug/pe-format

## Fix

`syscall.h` now names the syscall query name-slot contract:

```text
SYSCALL_NAME_SLOT_ULONGS = 16
SYSCALL_NAME_SLOT_BYTES = 16 * sizeof(ULONG)
SYSCALL_NAME_MAX_CHARS = SYSCALL_NAME_SLOT_BYTES - 1
```

`syscall.c` and `syscall_win32.c` now cap stored names at
`SYSCALL_NAME_MAX_CHARS`, size optional name slots with
`SYSCALL_NAME_SLOT_BYTES`, and advance output pointers by
`SYSCALL_NAME_SLOT_ULONGS`. The name-based invoke path rejects names longer
than `SYSCALL_NAME_MAX_CHARS`. `syscall_util.c` uses the same maximum while
building hook-map match strings.

No syscall index extraction, hook enable/disable policy, service-table
discovery, dispatch, or external 64-byte slot width changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-186.py
bash docs/plan/check-srev-186.sh
```

Runtime gate still required:

- Windows driver build across x86/x64/ARM64 configurations that include syscall
  query paths.
- `API_QUERY_SYSCALLS` smoke with `add_names=0` and `add_names=1` for native
  NT and win32k tables.
- Compatibility smoke for DLL consumers that read syscall query data.
