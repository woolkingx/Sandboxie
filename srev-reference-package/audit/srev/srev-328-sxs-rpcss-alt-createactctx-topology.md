# SREV-328: SXS RpcSs Alt CreateActCtx Topology

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/sxs.c`, `Sandboxie/apps/com/RpcSs/sxs.c`, Microsoft activation-context references |
| Output artifact | `docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.schema.json`, `docs/plan/check-srev-328.py`, `docs/plan/check-srev-328.sh`, ledger fragment, comment-only source clarification |
| Owner | `Sandboxie/core/dll/sxs.c` SXS alternate CreateActCtx route |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Data

`Sandboxie/core/dll/sxs.c` routes activation-context creation through the
in-sandbox `RPCSS_SXS` queue for normal sandboxed callers. The same file also
has an alternate path for `SandboxieRpcSs` and other cases where the service
route must not be used.

The relevant data nodes are:

```text
Sxs_UseAltCreateActCtx
Dll_ImageType == DLL_IMAGE_SANDBOXIE_RPCSS
Dll_AppContainerToken
DisableBoxedWinSxS
RPCSS_SXS queue request/reply
UseAltCreateActCtx out parameter
*UseAltCreateActCtx* reply sentinel
Sxs_CreateActCtxW_Alt
ACTCTXW lpSource
optional boxed-path translation
__sys_CreateActCtxW
```

## Official Shape

Microsoft documents `CreateActCtxW` as the API that creates an activation
context from an `ACTCTXW` pointer and returns either an activation-context
handle or `INVALID_HANDLE_VALUE`.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createactctxw
```

Microsoft documents activation contexts as system-managed data structures used
to redirect DLL, COM, window-class, type-library, and interface bindings.

```text
https://learn.microsoft.com/en-us/windows/win32/sbscs/activation-contexts
```

Microsoft documents `ACTCTXW.lpSource` as the null-terminated manifest or PE
path used to create the activation context.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-actctxw
```

## Schema

Local schema:

```text
docs/plan/srev-328-sxs-rpcss-alt-createactctx-topology.schema.json
```

`SXS_RPCSS_ALT_CREATEACTCTX_TOPOLOGY` says:

- `CreateActCtxW` owns the final activation-context handle;
- Sandboxie owns only the optional SXS service projection and boxed-path
  translation around the official `ACTCTXW` input;
- `SandboxieRpcSs` must not synchronously re-enter the in-sandbox `RPCSS_SXS`
  service that it implements;
- `Sxs_UseAltCreateActCtx` and the `*UseAltCreateActCtx*` sentinel are local
  topology gates to fall back to the native `CreateActCtxW` owner;
- this SREV changes comments and proof only.

## Topology

```text
normal sandboxed caller
  -> Sxs_CreateActCtxW
  -> Sxs_CallService
  -> RPCSS_SXS queue
  -> SandboxieRpcSs Sxs_Thread / Sxs_Request / Sxs_Generate
  -> RtlCreateActivationContext on returned section

SandboxieRpcSs or sentinel fallback
  -> Sxs_CreateActCtxW
  -> Sxs_CreateActCtxW_Alt
  -> optional boxed lpSource translation
  -> __sys_CreateActCtxW
```

The alternate path is not a general SXS policy bypass. It is the local route
that prevents the service process from depending on its own queue/thread while
still handing the final activation-context creation to the native API owner.

## Logic Risk

The old source comment described this as a generic workaround and said to use
the "real SXS from CSRSS." That wording hides the actual local topology. The
risk is not merely which process owns SXS internally; it is recursive service
dependency: the process implementing the `RPCSS_SXS` queue cannot safely block
on that same queue, especially during startup or loader-lock-sensitive work.

## Fix

Comment-only source clarification. The source now names SREV-328 and states
that `SandboxieRpcSs` avoids re-entering the in-sandbox SXS service. It also
states that the alternate path calls the native `CreateActCtxW` owner after
optional boxed-path translation, preserving the recursion gate.

No `Sxs_UseAltCreateActCtx` predicate, `RPCSS_SXS` queue behavior, fallback
sentinel, boxed-path translation, TLS process-create flag, `__sys_CreateActCtxW`
call, or activation-context result handling changed.

## Acceptance Gate

`docs/plan/check-srev-328.py` validates the draft-07 schema, official
references, source comment, `Sxs_UseAltCreateActCtx` routing, native
`__sys_CreateActCtxW` fallback, `RPCSS_SXS` service topology, fallback sentinel,
stale generic workaround wording removal, combined ledger entry, and split
ledger fragment.

Windows gate: SandboxieRpcSs startup and SXS activation-context creation should
be captured to prove that the service process uses the alternate path without
blocking on its own `RPCSS_SXS` queue, while normal sandboxed callers still use
the queue path when available.
