# SREV-288: GDI GetStockObject SEH Failure Result

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Input artifact | `Sandboxie/core/dll/gdi.c`, Microsoft `GetStockObject` and SEH references |
| Output artifact | Source comment owner, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Gdi_GetStockObject` full-GDI stock-object failure guard |
| Acceptance gate | Targeted checker validates official references, hook topology, narrow SEH guard, documented NULL failure result, stale wording removal, and ledger fragment |

## Data

`Gdi_GetStockObject` wraps the native `GetStockObject` only when
`Gdi_Full_Init_impl(..., full=TRUE)` resolves and hooks the export from
`gdi32full.dll`.

The data nodes are:

```text
full GDI init
GetProcAddress("GetStockObject")
SBIEDLL_HOOK(Gdi_, GetStockObject)
fnObject
__sys_GetStockObject(fnObject)
SEH exception filter
HGDIOBJ rc
NULL failure result
```

The source comment previously described a rare Chrome crash and broader
environmental theory. The code behavior is narrower: if the native call raises
inside this wrapper, the hook returns `0`, which is the documented failure
result for `GetStockObject`.

## Official Shape

Microsoft documents `GetStockObject` as retrieving a handle to a stock pen,
brush, font, or palette. If it succeeds, it returns a handle to the requested
logical object; if it fails, it returns `NULL`. `SYSTEM_FONT` is one of the
documented stock object selectors.

Microsoft documents `__try` / `__except` as frame-based structured exception
handling. If the filter evaluates to `EXCEPTION_EXECUTE_HANDLER`, the system
transfers control to the handler and execution continues in that stack frame.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-getstockobject`
- `https://learn.microsoft.com/en-us/windows/win32/debug/exception-handler-syntax`

## Schema

Local schema:

```text
docs/plan/srev-288-gdi-getstockobject-seh-failure-result.schema.json
```

Contract id:

```text
GDI_GETSTOCKOBJECT_SEH_FAILURE_RESULT
```

## Boundary

```text
caller stock object selector
  -> Gdi_GetStockObject hook
  -> __sys_GetStockObject(fnObject)
  -> success: native HGDIOBJ
  -> handled exception: NULL failure result
```

The hook owns only the exception-to-failure-result boundary around the native
call. It does not own stock-object selection, Chrome process classification,
GDI shared-state initialization, or general GDI recovery.

## Topology

```text
gdi32full.dll load
  -> Gdi_Full_Init(module)
  -> Gdi_Full_Init_impl(module, TRUE)
  -> GetProcAddress("GetStockObject")
  -> SBIEDLL_HOOK(Gdi_, GetStockObject)
  -> Gdi_GetStockObject
  -> __sys_GetStockObject
```

## Logic Risk

The old comment made this look like an open-ended Chrome crash workaround.
That can misroute future changes toward broad browser-specific GDI policy. The
local contract is smaller: keep a narrow SEH guard around one native
`GetStockObject` call and return the documented failure value if that call
raises during GDI initialization.

## Fix

Comment-only source clarification. The source now names SREV-288, the full-GDI
hook owner, the Chrome sandbox initialization context, the documented
`GetStockObject` `NULL` failure result, and the narrow native-call SEH guard.
No hook registration, exception filter, return value, or stock-object selector
behavior changed.

## Acceptance Gate

`docs/plan/check-srev-288.py` validates the draft-07 schema, official
references, full-GDI hook topology, source comment, narrow `__try` /
`__except (EXCEPTION_EXECUTE_HANDLER)` shape, `rc = 0` failure result, stale
workaround/crash wording removal from the function, combined ledger entry, and
split ledger fragment.

Runtime gate: Windows Chrome/Chromium sandbox launch matrix on builds where
`gdi32full.dll` owns `GetStockObject`, including `SYSTEM_FONT` access during
early GDI initialization and negative smoke for normal non-exception stock
object queries.
