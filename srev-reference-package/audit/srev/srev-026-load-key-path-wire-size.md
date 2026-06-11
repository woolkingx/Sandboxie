# SREV-026: LoadKey Path Wire Size

## Stage Gate

| Field | Content |
|---|---|
| Stage | schema -> topology -> logic -> action |
| Input Artifact | `FILE_LOAD_KEY_REQ` service wire shape |
| Output Artifact | Named and enlarged LoadKey path buffer contract |
| Owner | File service LoadKey request/reply wire contract |
| Acceptance Gate | LoadKey request path capacity is declared once and both sender/receiver enforce that capacity. |

## Official Shape

Microsoft `UNICODE_STRING` documentation defines `Length` and `MaximumLength` as
byte counts for a Unicode buffer:

```text
https://learn.microsoft.com/en-us/windows/win32/api/ntdef/ns-ntdef-_unicode_string
```

Native registry/file object paths are passed as counted Unicode strings at the
OS boundary. The 128-WCHAR limit in `FILE_LOAD_KEY_REQ` was not an OS limit; it
was a Sandboxie service-wire limit.

## Local Shape

`Key_NtLoadKeyImpl` builds a `FILE_LOAD_KEY_REQ` with:

- `KeyPath`: registry key path to mount;
- `FilePath`: hive file path.

The request crosses from the hooked DLL to SbieSvc through `SbieDll_CallServer`.
Both sides include `filewire.h`, so the struct is the owner of the legal wire
shape.

The previous struct used two anonymous `WCHAR[128]` arrays, and the sender had a
source comment saying `req->FilePath` should be much longer.

## Finding

The sender allocated an 8192-WCHAR workspace for the source file path but then
rejected any translated path longer than 127 WCHARs because the service wire
struct was too small. Long Windows install paths or redirected hive paths could
fail before the service's actual allowlist logic.

## Fix

`FILE_LOAD_KEY_PATH_CHARS` now names the wire capacity and sets both `KeyPath`
and `FilePath` to 1024 WCHARs. The sender checks `wcslen(path) <
FILE_LOAD_KEY_PATH_CHARS`; the receiver terminates using
`FILE_LOAD_KEY_PATH_CHARS - 1` instead of hard-coded `127`.

## Runtime Gate

Windows runtime proof:

1. TrustedInstaller COMPONENTS/SCHEMA hive load still succeeds on normal paths;
2. a valid long Windows directory path below 1024 WCHARs reaches the service
   allowlist instead of failing at the sender;
3. paths at or above `FILE_LOAD_KEY_PATH_CHARS` fail closed before `wcscpy`;
4. malformed service messages still fail closed.
