# SREV-178: MountManager Wire String Shape

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/svc/MountManager.h`, `Sandboxie/core/svc/MountManagerWire.h`, `Sandboxie/core/svc/MountManager.cpp`, `Sandboxie/core/dll/support.c`, Microsoft CRT string references |
| Output artifact | `docs/plan/srev-178-mountmanager-wire-string-shape.schema.json`, `docs/plan/check-srev-178.py`, `docs/plan/check-srev-178.sh`, ledger row |
| Owner | MountManager broker wire request boundary |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows malformed broker-message runtime proof remains required |

## Evidence

`Sandboxie/core/svc/MountManager.h` was the highest-ranked unnamed reviewable
core file after SREV-177. The header declares the MountManager owner for box-root
mount lifecycle, ImDisk mount/unmount, junction creation/removal, and broker
handlers. Its wire surface is defined in `MountManagerWire.h`.

Before this SREV, `CreateHandler`, `MountHandler`, `UnmountHandler`, and
`QueryHandler` checked only the minimum request structure size before using
fixed inline `WCHAR` arrays and flexible `file_root[1]` tails as C strings.
`CreateHandler` also called `wcsrchr(req->file_root, L'\\')` and immediately
used the result as the end iterator for a `std::wstring` range. A malformed
broker message with an unterminated `password`, `reg_root`, or `file_root`, or a
terminated create path without a backslash, could move service logic past the
message boundary before the mount policy decision.

On the DLL caller side, `SbieDll_Mount` copied `BoxKey` into
`IMBOX_MOUNT_REQ.password[129]` with `wcscpy`, and did not initialize the full
request before sending it. That left `admin_only` dependent on allocator
contents when `protect_root` was true.

Microsoft documents `wcscpy` as copying a null-terminated source string and
warns that it does not check destination capacity. Microsoft also documents a
wide-character length routine as operating on a null-terminated Unicode string.
Therefore the legal MountManager broker route must prove termination and local
capacity before calling string/path/mount logic.

Official references:

- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcpy-wcscpy-mbscpy?view=msvc-170
- https://learn.microsoft.com/en-us/windows/win32/api/stralign/nf-stralign-uaw_wcslen

## Data

`IMBOX_CREATE_REQ.password`, `IMBOX_CREATE_REQ.file_root`,
`IMBOX_MOUNT_REQ.password`, `IMBOX_MOUNT_REQ.reg_root`,
`IMBOX_MOUNT_REQ.file_root`, `IMBOX_UNMOUNT_REQ.reg_root`,
`IMBOX_QUERY_REQ.reg_root`, `MSG_HEADER.length`, `MAX_REG_ROOT_LEN`,
`SbieDll_Mount`, `BoxKey`, `admin_only`, `MountManager::CreateHandler`,
`MountManager::MountHandler`, `MountManager::UnmountHandler`,
`MountManager::QueryHandler`, `GetImageFileName`, `OpenOrCreateNtFolder`,
`MountImDisk`, `GetBoxRootLocked`, and `SbieApi_Call(API_PROTECT_ROOT)`.

## Schema

`MOUNTMANAGER_WIRE_STRING_SHAPE` says:

- MountManager owns the ImBox broker request string-shape gate before mount,
  unmount, enum, query, or create logic consumes request fields.
- Fixed `password[129]` fields must contain `L'\0'` inside the declared array
  before they are passed to C-string or password-handoff logic.
- Fixed `reg_root[MAX_REG_ROOT_LEN]` fields must contain `L'\0'` inside the
  declared array before map lookup, lock, release, protect, or unprotect logic.
- Flexible `file_root[1]` tails must contain `L'\0'` inside `MSG_HEADER.length`
  before `GetImageFileName`, `wcsrchr`, `OpenOrCreateNtFolder`, or
  `CreateJunction`.
- `CreateHandler` must reject a terminated create `file_root` with no backslash
  before using the `wcsrchr` result as a range boundary.
- `SbieDll_Mount` initializes the full outbound `IMBOX_MOUNT_REQ`, rejects
  `BoxKey` values that do not fit `password[129]`, and copies `BoxKey` only
  after that bound is proven.
- This SREV does not change ImDisk device discovery, encryption policy, reparse
  point creation/removal, box-root ownership, `UseFileImage`, `UseRamDisk`, or
  `API_PROTECT_ROOT` semantics.

## Topology

Legal MountManager broker flow:

```text
sandboxed caller / DLL request
  -> MSGID_IMBOX_* broker message
  -> minimum struct-size gate
  -> fixed-array terminator gates
  -> flexible tail terminator gate inside MSG_HEADER.length
  -> path separator gate for create-only root-parent derivation
  -> existing mount / query / unmount / junction / protect logic
```

Legal DLL mount request flow:

```text
SbieDll_Mount(BoxName, BoxKey, Protect)
  -> allocate request
  -> zero full IMBOX_MOUNT_REQ including admin_only
  -> prove BoxKey fits password[129]
  -> copy password
  -> query reg/file roots
  -> SbieDll_CallServer
```

## Logic Risk

The mount broker is a service boundary. The local payload schema is not proven
by the outer LPC/ALPC carrier and is not proven by `sizeof(IMBOX_*_REQ)` alone,
because several consumed fields are fixed inline arrays or flexible tails.
Calling `wcslen`, `wcscpy`, `wcsrchr`, `std::wstring(const WCHAR*)`, path
translation, or mount helpers before proving terminators lets untrusted request
bytes choose how far the service reads.

The smallest legal repair is a MountManager-local string-shape gate before the
existing logic. The fix should not alter mount policy, ImDisk command shape,
driver protection calls, or image/root naming.

## Fix

`MountManager.cpp` now has local bounded string gates:

- `MountManager_HasTerminator`
- `MountManager_HasMessageTerminator`
- `MountManager_IsValidRegRoot`
- `MountManager_IsValidPassword`
- `MountManager_IsValidFileRoot`

`CreateHandler` validates password and flexible `file_root`, then rejects a
create path with no backslash before deriving the parent root path with a
bounded `RootEnd - req->file_root` character count.
`MountHandler` validates password, `reg_root`, and flexible `file_root`.
`UnmountHandler` and `QueryHandler` validate `reg_root`.

`SbieDll_Mount` now zeroes the full request, rejects oversized `BoxKey` values
before `wcscpy`, copies the password only when `BoxKey` is non-null, and leaves
`admin_only` deterministically false unless a future caller sets it explicitly.

## Acceptance Gate

`docs/plan/check-srev-178.py` validates the draft-07 schema, official
references, wire-field evidence, MountManager service-side string gates,
ordering before C-string/path/mount use, create-path backslash rejection,
DLL-side request zeroing and password length gate, and ledger entry.
`docs/plan/check-srev-178.sh` is the matrix wrapper.

Runtime/build gate: Windows service/DLL build; malformed broker messages for
unterminated `password`, `reg_root`, and `file_root` return
`ERROR_INVALID_PARAMETER` without entering mount/query/unmount/protect logic;
oversized `BoxKey` passed to `SbieDll_Mount` returns false without overflowing
the request; ordinary mount/unmount/query and protected-root mount smoke still
work.
