# SREV-098: IE Embedding CLSID Registry Policy

## Data

`Sandboxie/core/drv/key_flt.c` owns the Vista-and-later registry-filter callback
for key create/open events. The comment-admitted shape is:

```text
host Office/Explorer/Svchost process opens IE COM CLSID registry key
BlockIEEmbedding policy is enabled
registry callback denies that CLSID lookup
COM cannot use the embedded IE activation path
caller falls back to a normal IE process launch
Sandboxie ForceProcess can capture that process launch
```

The local IE COM identity is not inferred from the registry filter comment
alone. `Sandboxie/core/svc/comserver9_ie.c` defines
`CLSID_InternetExplorer` as `{0002DF01-0000-0000-C000-000000000046}`, and
`Sandboxie/core/svc/comserver9.c` registers Sandboxie's IE COM server for
objects with `CLSID_InternetExplorer`.

## Official Shape

Microsoft documents registry filtering as a kernel-mode driver surface where a
driver registers a `RegistryCallback` routine with `CmRegisterCallbackEx` on
Windows Vista and later. Microsoft documents pre-notifications for registry
operations and says a registry callback can monitor, block, or modify registry
operations. For blocking, a pre-notification callback can return a non-success
`NTSTATUS`, and the configuration manager immediately returns that status to
the calling thread.

Microsoft documents `REG_NOTIFY_CLASS` values including `RegNtPreCreateKeyEx`
and `RegNtPreOpenKeyEx` as pre-notification calls to `RegistryCallback`.
Microsoft documents `REG_CREATE_KEY_INFORMATION_V1` /
`REG_OPEN_KEY_INFORMATION_V1` as carrying `CompleteName`, `RootObject`, and
`DesiredAccess` for create/open notifications.

Microsoft documents COM class registration as registry data that lets COM
create instances for a CLSID. `InprocServer32` registers an in-process server.
`LocalServer32` registers a local COM server executable, and COM appends
`-Embedding` when launching a local server. Microsoft documents `IWebBrowser2`
as implemented by the WebBrowser ActiveX control or an instance of the
InternetExplorer application.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/registering-for-notifications
https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/handling-notifications
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ne-wdm-_reg_notify_class
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_reg_create_key_information_v1
https://learn.microsoft.com/en-us/windows/win32/com/registering-com-servers
https://learn.microsoft.com/en-us/windows/win32/com/localserver32
https://learn.microsoft.com/en-us/windows/win32/com/inprocserver32
https://learn.microsoft.com/en-us/windows/win32/api/exdisp/nn-exdisp-iwebbrowser2
```

## Schema

Local schema:

```text
docs/plan/srev-098-ie-embedding-clsid-registry-policy.schema.json
```

The IE embedding CLSID policy contract is:

```text
Key_Callback handles only RegNtPreCreateKeyEx and RegNtPreOpenKeyEx for this policy
BlockIEEmbedding is a registry lookup denial policy, not a process launch owner
the denied key is the local InternetExplorer CLSID
the policy applies only to selected host callers where proc is NULL
the selected host callers are winword.exe, powerpnt.exe, excel.exe, explorer.exe, and svchost.exe
the policy returns STATUS_ACCESS_DENIED before ordinary sandbox key redirection
SearchUnicodeString is the CompleteName matcher and remains null-safe
normal sandboxed registry redirection remains owned by Key_MyParseProc_2
```

## Topology

```text
CmRegisterCallbackEx
  -> Key_Callback
  -> RegNtPreCreateKeyEx / RegNtPreOpenKeyEx only
  -> CompleteName contains CLSID\{0002df01-0000-0000-c000-000000000046}
  -> BlockIEEmbedding enabled
  -> current process is host-side (!proc)
  -> process name is selected Office/Explorer/Svchost host caller
  -> return STATUS_ACCESS_DENIED
  -> COM activation cannot resolve the embedded IE CLSID path
```

Normal sandboxed registry create/open continues afterward:

```text
proc exists
  -> build RemainingName from CompleteName or fallback \X
  -> Key_MyParseProc_2 owns sandbox key redirection
```

## Logic Risk

The old `HACK ALERT` comment hid the owner boundary. This block is not a
general ForceProcess implementation and not a COM server implementation. It is
a registry pre-notification policy that intentionally denies a specific COM
CLSID lookup for selected host callers. The acceptance gate is therefore not
"IE starts somehow"; it is "COM cannot resolve the embedded IE CLSID in that
host-caller path, and normal process launch can then be handled by the existing
ForceProcess path."

There is no source-level evidence here for broadening the caller list or
changing COM activation behavior. That needs a Windows runtime matrix because
COM activation and Office link handling can vary by Office/IE/Windows version.

## Fix

Comment-only source clarification. The vague `HACK ALERT` was replaced with a
policy-boundary comment: `BlockIEEmbedding` hides the InternetExplorer COM class
from selected host callers so COM activation cannot start an embedded IE server
path that bypasses Sandboxie's process-launch forcing.

No runtime behavior was changed.

## Acceptance Gate

`docs/plan/check-srev-098.py` validates the draft-07 schema, official
references, registry callback registration, create/open pre-notification scope,
InternetExplorer CLSID local identity, `BlockIEEmbedding` gate, selected host
caller list, `STATUS_ACCESS_DENIED` before ordinary sandbox redirection,
null-safe `SearchUnicodeString`, stale `HACK ALERT` removal, and ledger entry.
`docs/plan/check-srev-098.sh` is the matrix wrapper.

Runtime gate: Windows matrix with Word, PowerPoint, Excel, Explorer, and
Svchost host callers; `BlockIEEmbedding` on/off; Office hyperlink open; COM
activation trace for CLSID `{0002DF01-0000-0000-C000-000000000046}`; and
ForceProcess observation for the resulting normal IE process path.
