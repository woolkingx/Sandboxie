# SREV-335: IPC COM Server Classifier

| Field | Content |
|---|---|
| Stage | schema -> topology -> verify |
| Input artifact | `Sandboxie/core/drv/ipc.c`, `Sandboxie/core/dll/custom.c`, `Sandboxie/core/svc/comserver9.c`, `Sandboxie/core/svc/ProcessServer.cpp`, SREV-256, Microsoft COM activation and local-server documentation |
| Output artifact | Source comment owner, draft-07 schema, checker, and ledger fragment |
| Owner | `Ipc_IsComServer` driver-side forced COM server classifier |
| Acceptance gate | Targeted checker validates official references, forced-process/outside-box parent predicates, service-broker adjacency, untouchable marker, stale workaround wording removal, and ledger fragment |

## Data

`Ipc_InitPaths` marks a process `untouchable` when `Ipc_IsComServer` returns
true. `Ipc_IsComServer` recognizes a narrow forced COM server shape:

- the process must be forced;
- the image must not come from inside the box;
- the executable name must be one of `iexplore.exe`, `wmplayer.exe`,
  `winamp.exe`, or `kmplayer.exe`;
- the parent process must exist and must not be a sandboxed process;
- the parent must be running as the system account.

The old comment labeled the executable-name predicate as a third-party
workaround. The stronger contract is that this driver predicate is the local
classifier for the SbieSvc brokered COM handoff already described by SREV-256.

## Official Shape

Microsoft documents `CoCreateInstance` as creating and initializing an object
for a specified CLSID. It is a convenience path that obtains a class object,
creates an instance, and releases the class object.

Microsoft documents `CoRegisterClassObject` as the call an EXE object
application uses to register a class object with OLE so other applications can
connect to it. COM local servers launched through `LocalServer32` are executable
servers; COM appends ` -Embedding` to the command line, and the local server
must register its class object within the activation timeout.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-cocreateinstance`
- `https://learn.microsoft.com/en-us/windows/win32/api/combaseapi/nf-combaseapi-coregisterclassobject`
- `https://learn.microsoft.com/en-us/windows/win32/com/localserver32`
- `https://learn.microsoft.com/en-us/windows/win32/com/out-of-process-server-implementation-helpers`

## Boundary

```text
out-of-sandbox COM activation
  -> SbieSvc forced sandboxed local-server launch
  -> driver process flags and parent-context classifier
  -> Ipc_InitPaths marks classified process untouchable
  -> Custom_ComServer/SbieSvc comserver9.c owns the brokered COM conversation
```

The driver owns only the forced-process classifier and the resulting
`untouchable` marker. `Custom_ComServer` and SREV-256 own the brokered COM
handoff topology. `comserver9.c` owns the service-side application-specific COM
conversation.

## Topology

```text
Ipc_InitPaths
  -> Ipc_IsComServer
  -> forced_process
  -> image_from_box == false
  -> iexplore/wmplayer/winamp/kmplayer allowlist
  -> parent exists
  -> parent is not sandboxed
  -> parent runs as system
  -> proc->untouchable = TRUE

Custom_ComServer
  -> SbieDll_RunSandboxed broker request
  -> SbieSvc ProcessServer::RunSandboxedComServer
  -> comserver9.c application-specific COM handling
```

## Logic Risk

The stale workaround wording hid two different owners. The executable-name
predicate is not the COM broker itself; it is a driver-side classifier that
decides whether a forced process should be treated as a broker-launched COM
server for path initialization. If this is treated as a generic compatibility
workaround, a future patch could widen the allowlist, weaken the parent-context
checks, or move broker semantics into the driver without preserving the SbieSvc
owner boundary.

## Fix

Comment-only source clarification. The source now names SREV-335 and states
that the predicate is a driver-side forced COM server classifier for the
brokered SbieSvc handoff owned by `Custom_ComServer` and SREV-256. No process
flags, image allowlist, parent checks, `untouchable` behavior, service broker
request, or COM conversation code changed.

## Acceptance Gate

`docs/plan/check-srev-335.py` validates the draft-07 schema, official
references, `Ipc_IsComServer` predicates, `Ipc_InitPaths` `untouchable` marker,
SREV-256 `Custom_ComServer` broker adjacency, `comserver9.c` matching image
allowlist, `ProcessServer::RunSandboxedComServer` forced/protected flag gate,
stale workaround wording removal from the classifier block, combined ledger
entry, and split ledger fragment.

Runtime gate: Windows COM activation matrix for the four legacy application
targets, parent SYSTEM context, out-of-box parent launch, sandboxed parent
negative case, and non-allowlisted forced-process negative case.
