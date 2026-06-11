# SREV-223 IsHostPath Final Path Length Gate

## Data

Owner files:

```text
Sandboxie/core/svc/misc.h
Sandboxie/core/svc/main.cpp
```

Reviewed nodes:

```text
IsHostPath
ProcessServer breakout process gate
CreateFileW
GetFinalPathNameByHandleW
VOLUME_NAME_NT
\Device\Mup\
SbieApi_QueryProcessPath
```

## Schema

`IS_HOST_PATH_FINAL_LENGTH_GATE` defines these local contracts:

- `misc.h` declares service-wide helpers; `main.cpp` owns the implementations.
- `IsHostPath` compares a requested host path against the caller's sandbox root
  before allowing a `BreakoutProcess` request.
- `GetFinalPathNameByHandleW` returns the final path length on success and a
  required buffer size when the supplied buffer is too small.
- A successful final-path read requires a nonzero return smaller than the buffer
  capacity passed in characters.
- Prefix tests and later length comparisons must use the returned final-path
  length, not the fixed scratch-buffer capacity.
- A `VOLUME_NAME_NT` path beginning with `\Device\Mup\` is a network-share path
  and remains not-a-host-path for this breakout gate.
- This SREV does not change breakout allowlist semantics, sandbox-root query
  semantics, `CreateFileW` access/share flags, or the prefix-based sandbox-root
  comparison policy.

## Topology

```text
ProcessServer breakout candidate
  -> IsHostPath(caller pid, lpApplicationName)
  -> CreateFileW(candidate)
  -> GetFinalPathNameByHandleW(..., VOLUME_NAME_NT)
  -> returned final-path length
  -> reject \Device\Mup\ network-share paths
  -> SbieApi_QueryProcessPath(caller sandbox root)
  -> host-path decision
```

The Windows API owns the final-path length. The local scratch buffer owns
capacity only; it is not a valid substitute for the length of the returned NT
path string.

## Logic Risk

Before this SREV, `IsHostPath` initialized `len = 8192`, passed that as the
`GetFinalPathNameByHandleW` buffer capacity, then checked `len > 12` before the
`\Device\Mup\` prefix test and used `wcslen(request_path)` for the request
length. The MUP gate therefore depended on the scratch-buffer capacity, not on
the API's returned path length. The too-small-buffer check also accepted
`dwRet == len`, even though a successful NUL-terminated write cannot occupy the
entire caller-supplied character capacity.

The legal local repair is to keep the same host/sandbox policy but use
`dwRet` as the final-path length for the MUP prefix gate and later comparison.

## Official Shape

- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfinalpathnamebyhandlew
- https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew

## Fix

`IsHostPath` now rejects `GetFinalPathNameByHandleW` results where
`dwRet == 0` or `dwRet >= len`, computes the MUP prefix length from the local
literal, gates the prefix test with `dwRet >= MupPrefixLen`, and uses `dwRet`
as `request_path_len`.

No breakout allowlist, path-open flags, network-share rejection policy,
sandbox-root query, or sandbox-root prefix comparison policy changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-223.py
bash docs/plan/check-srev-223.sh
```

Runtime/build gate still required:

- Windows service build for `main.cpp`.
- Positive `BreakoutProcess` smoke for a host-local executable outside the
  sandbox root.
- Negative smoke for a candidate inside the sandbox root.
- Negative smoke for a network-share path whose final NT path begins with
  `\Device\Mup\`.
- Boundary smoke where `GetFinalPathNameByHandleW` returns a too-small-buffer
  length, proving the path is rejected before comparison.
