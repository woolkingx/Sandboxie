# SREV-193: IE COM Navigation Input Contract

## Scope

Owner:

```text
Sandboxie/core/svc/comserver9_ie.c
```

Supporting build shape:

```text
Sandboxie/core/svc/comserver9.c
Sandboxie/core/svc/SboxSvc.vcxproj
```

This entry covers the local Internet Explorer COM server shim that receives
navigation calls and restarts the requested browser process with the supplied
URL/path argument.

## Official Shape

Microsoft documents `IWebBrowser2::Navigate` as taking a required `BSTR` URL,
full path, or UNC location. Invalid parameters can return `E_INVALIDARG`.

Microsoft documents `IWebBrowser2::Navigate2` as taking a `VARIANT *URL` that
evaluates to the resource URL/path or Shell PIDL. The Sandboxie local broker
currently only consumes the `VT_BSTR` member of that variant, so the legal local
shape is narrower than the full API: the broker must prove `URL != NULL`,
`URL->vt == VT_BSTR`, and `URL->bstrVal != NULL` before reading `bstrVal`.

Microsoft documents VARIANT manipulation rules: callers must respect the
variant type and `VT_BSTR` has one string owner.

Microsoft documents `IUri::GetRawUri` as returning a `BSTR` through an out
parameter and states that the caller is responsible for freeing it with
`SysFreeString`.

Microsoft documents `SysFreeString` as the deallocator for previously allocated
BSTR values and as accepting NULL.

References:

- https://learn.microsoft.com/en-us/previous-versions/aa752133(v=vs.85)
- https://learn.microsoft.com/en-us/previous-versions/aa752134(v=vs.85)
- https://learn.microsoft.com/en-us/previous-versions/windows/desktop/automat/variant-manipulation-functions
- https://learn.microsoft.com/en-us/previous-versions/windows/internet-explorer/ie-developer/platform-apis/ms775030(v=vs.85)
- https://learn.microsoft.com/en-us/windows/win32/api/oleauto/nf-oleauto-sysfreestring

## Local Data

The local navigation inputs are:

- `IOleCommandTarget::Exec` with `pvaIn->vt == VT_BSTR`
- `ITargetFramePriv::NavigateHack` with `pszUrl`
- `ITargetFramePriv2::AggregatedNavigation2` with `IUri *pUri`
- `IWebBrowser2::Navigate` with `BSTR url`
- `IWebBrowser2::Navigate2` with `VARIANT *URL`
- `ITargetFrame2::SetFrameSrc` with `pszFrameSrc`
- `IEServer_RestartProgram` and `IEServer_ResolveUrl`

`IEServer_ResolveUrl` uses string scanning APIs and therefore needs a non-NULL
string. The correct boundary gate is before a COM input is forwarded into
`IEServer_RestartProgram`.

## Topology

Legal local flow:

```text
COM caller navigation input
-> method-specific shape gate
-> non-NULL URL/path string
-> optional .url resolution
-> ComServer_RestartProgram
```

For `IUri::GetRawUri`:

```text
IUri pointer
-> IUri_GetRawUri out BSTR
-> NavigateHack consumes BSTR as read-only URL string
-> SysFreeString releases the BSTR owner allocation
```

For `Navigate2`, full Shell PIDL support is an unimplemented compatibility
shape. This SREV does not add PIDL support; it makes the existing BSTR-only
projection explicit and rejects unsupported variants before reading the wrong
union member.

## Risk

Before this fix, several COM entry points could pass NULL or unsupported
variant data into `IEServer_RestartProgram`, and `IEServer_ResolveUrl` would
then call string functions on that pointer. `IWebBrowser2::Navigate2` read
`URL->bstrVal` without proving that `URL` was non-NULL or that `bstrVal` was
the active VARIANT member. `ITargetFramePriv2::AggregatedNavigation2` also did
not release the BSTR returned by `IUri::GetRawUri`.

## Fix

- Reject NULL BSTR/string inputs at COM navigation entry points.
- Reject `IWebBrowser2::Navigate2` unless the local supported shape is
  `VT_BSTR` with a non-NULL `bstrVal`.
- Reject a NULL `IUri *` before calling `IUri_GetRawUri`.
- Release the `IUri::GetRawUri` output with `SysFreeString`.
- Include `oleauto.h` and link `OleAut32.lib` for the service binary.
- Keep a final NULL guard in `IEServer_RestartProgram`.

## Acceptance Gate

Source-level gate:

```bash
python3 docs/plan/check-srev-193.py
bash docs/plan/check-srev-193.sh
python3 docs/plan/check-core-coverage.py
```

Runtime gate:

```text
Windows SbieSvc build for Win32/x64/ARM64/ARM64EC plus IE COM server smoke
for Navigate, Navigate2 VT_BSTR, NULL/unsupported Navigate2 inputs,
AggregatedNavigation2 IUri input, and .url resolution behavior.
```
