# SREV-256: Custom COM Server Broker Comment

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/dll/custom.c`, SREV-098, SREV-193, Microsoft COM registration references |
| Output artifact | `docs/plan/srev-256-custom-comserver-broker-comment.schema.json`, `docs/plan/check-srev-256.py`, `docs/plan/check-srev-256.sh`, ledger fragment, comment-only source clarification |
| Owner | `Custom_ComServer` forced COM server broker topology comment |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Evidence

`Custom_ComServer` contains the local comment that explains the forced COM
server transition. A forced COM server is a sandboxed program launched by COM
outside the sandbox in response to a `CoCreateInstance` request. The historical
comment used generic workaround language for both the pre-v4 direct COM IPC
access shape and the v4 SbieSvc broker shape.

Adjacent SREV coverage:

- SREV-098 owns the IE embedding CLSID registry policy and COM local-server
  registration boundary.
- SREV-193 owns IE COM navigation input validation in `comserver9_ie.c`.

Official references:

- https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-cocreateinstance
- https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-coregisterclassobject
- https://learn.microsoft.com/en-us/windows/win32/com/localserver32

## Data

`Custom_ComServer`, `CoCreateInstance`, `CoRegisterClassObject`,
`SbieDll_RunSandboxed`, SbieSvc `comserver9.c`, COM IPC objects, and the target
URL/file handoff.

## Schema

`CUSTOM_COMSERVER_BROKER_COMMENT` says:

- the current v4 forced-COM-server path is a brokered SbieSvc handoff, not a
  sandboxed process with broad COM IPC access;
- the pre-v4 direct COM IPC access shape is historical context only;
- `Custom_ComServer` comments should name the broker topology rather than a
  generic workaround;
- this SREV does not change process launch, COM IPC policy, SbieSvc request
  shape, `comserver9.c`, or IE navigation input handling.

## Topology

```text
out-of-sandbox COM CoCreateInstance
  -> forced sandboxed COM server program
  -> Custom_ComServer broker request
  -> SbieSvc comserver9.c outside-sandbox COM conversation
  -> target URL/file handoff back into sandboxed server program
```

## Logic Risk

Generic workaround language hides the owner transition. A future patch could
mistake the pre-v4 direct COM IPC access shape for the current owner, or change
`Custom_ComServer` even though the active COM conversation is broker-owned by
SbieSvc.

## Fix

Comment-only source clarification. The source now describes the current path as
a brokered COM handoff and the pre-v4 path as historical direct COM IPC access.
No behavior changed.

## Acceptance Gate

`docs/plan/check-srev-256.py` validates the draft-07 schema, official reference
links, source comments, removal of the generic workaround wording from the
`Custom_ComServer` block, SREV-098/SREV-193 adjacency, and the ledger fragment.

Runtime gate: none added. Existing COM server runtime gates remain owned by
SREV-098 and SREV-193.
