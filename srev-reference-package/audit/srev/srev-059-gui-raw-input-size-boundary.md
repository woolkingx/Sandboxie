# SREV-059: GUI Raw Input Size Boundary

## Data

`Sandboxie/core/dll/guimisc.c` proxies `GetRawInputDeviceInfoA/W` through the
GUI service. The request carries:

```text
hDevice
uiCommand
unicode flag
optional pData bytes
required pcbSize value
```

`Sandboxie/core/svc/GuiServer.cpp` reconstructs the Win32 call and writes the
reply buffer.

## Official Shape

Microsoft documents `GetRawInputDeviceInfoA` as taking optional `pData` and
required `pcbSize`:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getrawinputdeviceinfoa
```

For `RIDI_DEVICENAME`, `pcbSize` is a character count, not a byte count. If
`pData` is `NULL`, the API returns zero and writes the required size through
`pcbSize`.

## Schema

Local schema:

```text
docs/plan/srev-059-gui-raw-input-size-boundary.schema.json
```

The DLL-side hook may omit `pData`, but it must not send a proxy request without
a caller-owned `pcbSize`. The service side must prove the character-to-byte
conversion fits the bounded reply data region before multiplying.

## Topology

```text
caller pcbSize -> DLL request size gate -> GUI wire request -> service max-data gate -> User32 GetRawInputDeviceInfoA/W
```

`pcbSize` is the size owner. The service owns the bounded reply buffer. The
Unicode `RIDI_DEVICENAME` conversion is a topology crossing from character count
to byte count and must happen only after a max-data gate.

## Logic Risk

The older DLL hook treated `pcbSize == NULL` as a dummy zero-sized request so
the helper service would not crash. That shape is not legal per the Win32 API:
`pcbSize` is required, and `pData` is the optional pointer.

The service also multiplied the Unicode `RIDI_DEVICENAME` character count by
`sizeof(WCHAR)` before checking the bounded reply data size. A large forged wire
request could overflow the byte count and then call User32 with a small proxy
buffer plus a huge `pcbSize`.

## Fix

The DLL hook now rejects null `pcbSize` locally with
`ERROR_INVALID_PARAMETER`, validates Unicode byte-count overflow before request
allocation, checks the request-size addition, and handles request allocation
failure.

The GUI service now computes the bounded reply data capacity before converting
Unicode `RIDI_DEVICENAME` characters to bytes, and rejects values larger than
`max_data / sizeof(WCHAR)`.

## Acceptance Gate

`docs/plan/check-srev-059.py` validates the draft-07 schema, official reference,
DLL-side required `pcbSize` gate, local overflow gates, allocation gate, service
pre-multiply max-data gate, and ledger entry.

Windows gate: `GetRawInputDeviceInfoA/W` through the proxy should preserve
normal device-name and device-info behavior, `pData == NULL` size-query behavior,
null `pcbSize` local failure, and oversized Unicode device-name request rejection
without helper-service crash.
