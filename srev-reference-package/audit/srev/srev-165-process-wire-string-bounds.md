# SREV-165: Process Wire String Bounds

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/svc/ProcessServer.h, Sandboxie/core/svc/ProcessServer.cpp, Sandboxie/core/svc/ProcessWire.h, and Microsoft process/heap API documentation
output artifact: process broker wire string lengths are bounded as WCHAR counts before byte conversion
owner: Sandboxie/core/svc/ProcessServer.cpp
acceptance gate: docs/plan/check-srev-165.py and docs/plan/check-srev-165.sh
```

## Data

`ProcessServer.h` declares the process broker operations and exposes
`RunSandboxedCopyString(MSG_HEADER *msg, ULONG ofs, ULONG len)`. The wire schema
in `ProcessWire.h` carries offsets plus WCHAR-count lengths for process launch
strings:

```c
ULONG cmd_ofs;
ULONG cmd_len;
ULONG dir_ofs;
ULONG dir_len;
ULONG env_ofs;
ULONG env_len;
```

`ProcessServer.cpp` consumes these fields in two places:

- `RunSandboxedHandler` copies command line, current directory, and environment
  strings through `RunSandboxedCopyString`.
- `RunUpdaterHandler` validates and copies a signed updater command line before
  calling `CreateProcessAsUser`.

Before this SREV, the broker multiplied caller-provided `ULONG` WCHAR counts by
`sizeof(WCHAR)` inside validation expressions. A large count could wrap before
the `PIPE_MAX_DATA_LEN` and message-length checks. `RunUpdaterHandler` also
dereferenced the command buffer without checking whether `HeapAlloc` returned
`NULL`.

## Official Shape

- Microsoft documents `CreateProcessAsUserW` `lpCommandLine` as an in/out
  mutable command line, with maximum length 32K characters, and says the Unicode
  function can modify the buffer:
  `https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw`.
- Microsoft documents `HeapAlloc` with no exception flag as returning `NULL` on
  failure and not calling `SetLastError`:
  `https://learn.microsoft.com/en-us/windows/win32/api/heapapi/nf-heapapi-heapalloc`.
- Microsoft documents a user environment block as null-terminated Unicode
  strings ending in two nulls, and requires `CREATE_UNICODE_ENVIRONMENT` when
  passing it to `CreateProcessAsUser`:
  `https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-createenvironmentblock`.

## Schema

`PROCESS_WIRE_STRING_BOUNDS` says:

- `ProcessServer.cpp` owns service-side validation for process broker wire
  strings.
- `ProcessWire.h` lengths are WCHAR counts, not byte counts.
- A WCHAR count must be checked against `PIPE_MAX_DATA_LEN / sizeof(WCHAR)`
  before multiplying by `sizeof(WCHAR)`.
- Offset validation must prove `ofs <= msg->length` first, then compare byte
  length against `available = msg->length - ofs`.
- Validation must not depend on `ofs + byte_len` arithmetic.
- `RunUpdaterHandler` must check `HeapAlloc` before writing to `cmd`.
- The patch does not change process-token ownership, DACL policy, startup flag
  filtering, handle filtering, or `CreateProcessAsUser` call topology.
- Linux source gates are not Windows service runtime proof.

## Topology

Legal process-launch wire flow:

```text
PROCESS_RUN_SANDBOXED_REQ / PROCESS_RUN_UPDATER_REQ
  -> MSG_HEADER.length
  -> offset + WCHAR count
  -> count cap before byte conversion
  -> available bytes from message length
  -> broker-owned mutable WCHAR buffer
  -> CreateProcessAsUserW
```

`ProcessServer.cpp` is the service-side boundary owner. The caller-side packet
builder is useful evidence, but it cannot be trusted as the validation owner
for a service IPC boundary.

## Logic Risk

Multiplying an untrusted `ULONG` count before proving the count fits in bytes can
wrap the byte count used by validation and copying. That can turn an invalid wire
shape into a truncated broker string, or make updater allocation/copy logic
operate on a shape that was never valid. Separately, dereferencing the updater
command allocation without a `NULL` check can crash the service under allocation
failure.

## Fix

`RunSandboxedCopyString` now rejects counts above
`PIPE_MAX_DATA_LEN / sizeof(WCHAR)`, computes `bytes` only after that cap, proves
`ofs <= msg->length`, computes `available = msg->length - ofs`, and compares the
byte length against `available`. It no longer uses `ofs + bytes` validation.

`RunUpdaterHandler` now uses the same pre-multiply count cap, computes
`cmd_bytes`, validates against `available`, uses `cmd_bytes` for `memcpy`, and
returns `ERROR_NOT_ENOUGH_MEMORY` when command-buffer allocation fails.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-165.py
bash docs/plan/check-srev-165.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-165.py &&
bash docs/plan/check-srev-165.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows service build; normal sandboxed process launch;
updater launch by signed caller; malformed service IPC packets with oversized
WCHAR counts, offset past message length, short payload, empty string, and large
valid payload; low-memory or forced-allocation-failure smoke for updater command
buffer.
