# SREV-199: SFC WRP Query Shim Contract

Stage: schema -> boundary -> action -> verify

Input artifact: `Sandboxie/core/dll/sfc.c`

Output artifact: the Sandboxie SFC/WRP query shim keeps its existing
"not protected" compatibility policy while matching the documented
`SfcIsFileProtected` function shape.

Owner: `Sandboxie/core/dll/sfc.c`

Acceptance gate: `docs/plan/check-srev-199.py` plus
`docs/plan/check-srev-199.sh`.

## Data

`sfc.c` hooks selected `sfc_os.dll` entry points from the DLL loader table where
the local intent is explicitly documented as "disable SFC".

The important data crossings are:

- `SfcIsFileProtected` receives an `RpcHandle` that must be `NULL` and a file
  path pointer.
- `SfcIsKeyProtected` receives a predefined root key handle, an optional subkey
  string, and a registry-view selector.
- `SfcGetNextProtectedFile` receives a protected-file enumeration buffer and
  reports end-of-enumeration through `ERROR_NO_MORE_FILES`.

Local evidence before this entry:

- `sfc.c` intentionally returned `FALSE` for the file/key protection queries and
  `ERROR_NO_MORE_FILES` for enumeration, matching the loader comment that the
  shim disables SFC visibility.
- The local `SfcIsFileProtected` prototype used `LPCWSTR *FileName` even though
  Microsoft documents the second parameter as `LPCWSTR ProtFileName`.
- The source comment in `Sfc_Init` said "SECUR32 entry points", which described
  another hook surface and obscured the SFC/WRP owner.

## Official API Shape

`SfcIsFileProtected` determines whether a file is protected. Its second
parameter is `LPCWSTR ProtFileName`, not a pointer-to-pointer:

https://learn.microsoft.com/en-us/windows/win32/api/sfc/nf-sfc-sfcisfileprotected

`SfcIsKeyProtected` determines whether a registry key is protected. It receives
`HKEY KeyHandle`, optional `LPCWSTR SubKeyName`, and `REGSAM KeySam`:

https://learn.microsoft.com/en-us/windows/win32/api/sfc/nf-sfc-sfciskeyprotected

`SfcGetNextProtectedFile` enumerates protected files. Microsoft documents that
support for this function was removed in Windows Vista / Windows Server 2008 and
that end-of-enumeration is `FALSE` with `GetLastError() == ERROR_NO_MORE_FILES`:

https://learn.microsoft.com/en-us/windows/win32/api/sfc/nf-sfc-sfcgetnextprotectedfile

WRP documentation says the supported resource-query functions are
`SfcIsFileProtected` and `SfcIsKeyProtected`, and they should be used instead of
deprecated enumeration functions when available:

https://learn.microsoft.com/en-us/windows/win32/wfp/wfp-functions

The WRP overview states that WRP prevents replacement of protected files,
folders, and registry keys through DACL/ACL restrictions and that applications
can use the SFC query functions to detect protected resources:

https://learn.microsoft.com/en-us/windows/win32/wfp/detecting-file-replacement

## Boundary

The boundary is:

```text
application or installer SFC/WRP query
  -> sfc_os.dll hook
  -> Sandboxie compatibility shim
  -> fixed not-protected / no-more-files result
```

`sfc.c` owns only the compatibility projection. Windows owns real WRP policy and
TrustedInstaller protection. This SREV does not change the policy decision to
hide protected-resource status inside the sandbox; it fixes the hook's declared
API shape so later review is not built on a wrong parameter model.

## Topology

```text
Sfc_Init
  -> GetProcAddress(sfc_os.dll exports)
  -> hook only exports that exist on the host

Sfc_SfcIsFileProtected
  -> documented HANDLE + LPCWSTR shape
  -> return FALSE with existing ERROR_FILE_NOT_FOUND compatibility status

Sfc_SfcIsKeyProtected
  -> documented HKEY + optional LPCWSTR + REGSAM shape
  -> return FALSE with existing ERROR_FILE_NOT_FOUND compatibility status

Sfc_SfcGetNextProtectedFile
  -> enumeration request
  -> return FALSE with ERROR_NO_MORE_FILES
```

## Logic

The local source should not imply that `SfcIsFileProtected` receives an output or
indirect string pointer. Even if the ABI width is the same for pointer-sized
arguments, the wrong type creates a false schema for future policy work.

The fix is deliberately narrow:

- correct the `SfcIsFileProtected` typedef, declaration, and hook function
  signature to `LPCWSTR ProtFileName`;
- correct the stale `SECUR32` comment to SFC/WRP wording;
- preserve the existing return policy and `SfcGetNextProtectedFile`
  end-of-enumeration behavior.

## Verification

Linux source gates prove:

- `SfcIsFileProtected` no longer uses `LPCWSTR *`;
- the hook has the documented `HANDLE, LPCWSTR` shape;
- the file/key query functions still return `FALSE` with the existing
  compatibility status;
- protected-file enumeration still returns `FALSE` and sets
  `ERROR_NO_MORE_FILES`;
- the SFC/WRP policy-shim intent is recorded in the ledger fragment.

Runtime gate:

- Windows DLL build.
- Installer/application smoke that calls `SfcIsFileProtected`,
  `SfcIsKeyProtected`, and `SfcGetNextProtectedFile` inside a sandbox and
  confirms the expected compatibility results without crashing.
