# SREV-069: SXS ActCtx Temp Buffer Gate

## Data

`Sandboxie/core/dll/sxs.c` intercepts activation-context creation and query
paths. The local SXS layer derives directory strings from `ACTCTXW.lpSource`,
rewrites boxed `lpSource` paths for the alternate `CreateActCtxW` path, and
post-processes queried activation-context paths.

The relevant data nodes are:

```text
ACTCTXW lpSource
ACTCTXW lpAssemblyDirectory
args.SourcePath
args.Directory temp buffer
Sxs_CreateActCtxW_Alt MySource temp buffer
Sxs_QueryActCtxW_2 TruePath2 temp buffer
wmemcpy writes into temp buffers
underlying CreateActCtxW fallback
```

## Official Shape

Microsoft documents `CreateActCtxW` as receiving a pointer to an `ACTCTXW`
structure:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createactctxw
```

Microsoft documents `ACTCTXW.lpSource` as a null-terminated manifest or PE path:

```text
https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-actctxw
```

Microsoft documents `wmemcpy` as copying wide characters from source to
destination buffers:

```text
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/memcpy-wmemcpy?view=msvc-170
```

The local SXS wrapper may derive and copy strings around those official inputs,
but every destination buffer must be proven non-null before the copy.

## Schema

Local schema:

```text
docs/plan/srev-069-sxs-actctx-temp-buffer-gate.schema.json
```

Temporary SXS path buffers are legal destinations only when allocation succeeds:

```text
args.Directory != NULL before copying args.SourcePath
MySource != NULL before SbieDll_GetHandlePath writes into it
TruePath2 != NULL before appending a trailing slash copy
```

If the alternate path-translation temp buffer cannot be allocated, the local
translation is skipped and the original `ACTCTXW` is passed to the underlying
`CreateActCtxW` owner.

## Topology

```text
ACTCTXW input -> Sandboxie SXS path translation -> temp path buffer -> CreateActCtxW / QueryActCtxW projection
```

`CreateActCtxW` owns the official activation-context result. Sandboxie owns only
the temporary path buffers it allocates before calling or post-processing that
API.

## Logic Risk

Before this patch, low-memory allocation failure could make the SXS wrapper pass
a null destination into `wmemcpy` or `SbieDll_GetHandlePath`. That turns an
activation-context compatibility path into a local crash before the official
API owner can handle the original request.

## Fix

`Sxs_CreateActCtxW` now checks `args.Directory` before copying `args.SourcePath`.
`Sxs_CreateActCtxW_Alt` now checks `MySource` before passing it to
`SbieDll_GetHandlePath`; allocation failure skips only the local path
translation and falls through to `__sys_CreateActCtxW(ActCtx)`. `Sxs_QueryActCtxW_2`
now checks `TruePath2` before copying and appending a trailing slash.

## Acceptance Gate

`docs/plan/check-srev-069.py` validates the draft-07 schema, official
references, temp-buffer allocation gates before writes, alternate-path
translation skip behavior, and ledger entry.

Windows gate: alternate `CreateActCtxW` path still translates boxed manifest
paths when allocation succeeds; low-memory temp-buffer failures do not crash in
local SXS path copying; queried activation-context paths still preserve trailing
slash behavior when allocation succeeds.
