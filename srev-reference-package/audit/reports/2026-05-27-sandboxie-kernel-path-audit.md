# Sandboxie Kernel Path And LSA Audit Plan

Goal: turn the observed Sandboxie hang, path, kernel data, and LSA policy concerns into independent, reviewable tasks before any code change.

Architecture:
Sandboxie is treated as a Windows object-access mediation layer, not only as a file sandbox. The audit follows the data path from user-mode hooks to driver policy and service brokers, then checks whether each boundary has the correct owner, semantic decision, timeout behavior, and verification gate.

Tech Stack:
C/C++ Windows driver code, Sandboxie user-mode DLL hooks, SbieSvc brokers, Windows NT object namespace, ALPC/LPC/RPC, LSA policy APIs, minifilter file callbacks.

## File Map

| File | Role In This Plan |
|---|---|
| `Sandboxie/core/drv/api.c` | Driver API user-string copy helper; suspected kernel pool overwrite. |
| `Sandboxie/core/drv/conf.c` | Driver config update path that calls `Api_CopyStringFromUser`. |
| `Sandboxie/core/drv/file_xlat.c` | Reparse-point translation cache and global wait path. |
| `Sandboxie/core/drv/process_util.c` | Path-list expansion, reparse translation entry point, pattern construction. |
| `Sandboxie/core/dll/obj.c` | Hooked `NtQueryObject` object-name path; known pipe-handle hang risk. |
| `Sandboxie/core/drv/file.c` | Driver-side `API_GET_FILE_NAME` and file path policy checks. |
| `Sandboxie/core/dll/callsvc.c` | User-mode synchronous calls into `SbieSvc`. |
| `Sandboxie/core/svc/PipeServer.cpp` | SbieSvc LPC request dispatch and synchronous handler execution. |
| `Sandboxie/core/drv/ipc_lsa.c` | LSA endpoint filtering by RPC message ID. |
| `Sandboxie/core/drv/ipc.c` | IPC defaults, `BlockPassword`, `OpenLsaEndpoint`, and LSA path policy. |
| `Sandboxie/core/dll/lsa.c` | Secur32/SspiCli LSA hook surface. |
| `Sandboxie/install/SbieSettings.ini` | User-facing setting definitions such as `OpenLsaEndpoint` and `UseDriverObjLookup`. |
| `CHANGELOG.md` | Historical evidence for LSARPC endpoint filtering as a security fix. |

## Issue Register

### KPATH-001: `Api_CopyStringFromUser` Writes Past The Allocated Buffer

| Field | Content |
|---|---|
| Stage | schema -> boundary -> verify |
| Symptom | Possible kernel pool corruption during driver config update. Could manifest as intermittent hangs or unstable behavior. |
| Evidence | `Sandboxie/core/drv/api.c:1095` allocates `uni->Length + sizeof(WCHAR)` bytes, then `api.c:1102` writes a terminator at index `*len / sizeof(WCHAR)`, one `WCHAR` past the allocation. `Sandboxie/core/drv/conf.c:2198` calls this helper from config update. |
| Current Owner | `api.c` owns copying a user `UNICODE_STRING64` into driver pool memory. |
| Boundary | User-mode `UNICODE_STRING64` crosses into kernel driver memory. |
| Invariant | Kernel buffer length must include copied payload plus exactly one terminator, and the terminator write must be inside the allocated range. |
| Hypothesis | Setting update through driver mode can overwrite adjacent pool memory by two bytes. |
| Risk | Kernel memory corruption; difficult-to-reproduce hang; possible security issue if controlled input shapes adjacent pool state. |
| Strategy | Fix the copy helper first because it is a local, deterministic memory-safety defect with a clear invariant. |
| Proposed Minimal Change | Allocate `uni->Length + sizeof(WCHAR)`, copy only `uni->Length`, write terminator at `uni->Length / sizeof(WCHAR)`, and reject odd `Length` values. |
| Verification Gate | Static readback proves terminator index is inside allocation; driver config update path no longer copies beyond user string length. If Windows build is available, run Special Pool or Driver Verifier against config update. |
| Open Question | Whether `ProbeForRead(buff, *len, ...)` currently depends on reading the caller's terminator; the safer contract is to copy `Length` and synthesize the terminator in driver memory. |

Task plan:

- [x] Step 1: Add `docs/plan/check-kpath-001.sh` as a minimal source-level proof for allocation/copy/terminator invariants.
- [x] Step 2: Patch `Sandboxie/core/drv/api.c` so the copy length is `uni->Length`, allocation length is `uni->Length + sizeof(WCHAR)`, and terminator index is `uni->Length / sizeof(WCHAR)`.
- [x] Step 3: Add explicit rejection for odd byte lengths before allocation.
- [x] Step 4: Run a source grep for all `Api_CopyStringFromUser` callers and verify the new contract still matches `conf.c`.
- [x] Step 5: Checked local build environment; this Linux workspace has no `msbuild`/`devenv`, so Windows driver compilation remains a Windows WDK host verification item.

### KPATH-002: Reparse Translation Uses A Global Busy Wait Around Synchronous File I/O

| Field | Content |
|---|---|
| Stage | topology -> action -> verify |
| Symptom | Sandboxie may appear frozen when path-list initialization or refresh touches a slow, broken, network, cloud, or filter-driver-backed path. |
| Evidence | `Sandboxie/core/drv/file_xlat.c:587` loops while `File_ReparsePointsBusy` is non-zero without a timeout. `file_xlat.c:649` calls `File_TranslateReparsePoints_3`. `file_xlat.c:722` performs synchronous `ZwCreateFile` on the checked path. `Sandboxie/core/drv/process_util.c:787` triggers reparse checking while adding file or pipe path settings. |
| Current Owner | `file_xlat.c` owns reparse-point translation cache; `process_util.c` owns path-list construction. |
| Boundary | Configuration path pattern crosses into kernel file-system namespace probing. |
| Invariant | A path policy refresh must not indefinitely block unrelated sandbox operations. |
| Hypothesis | One slow or stuck reparse probe can keep `File_ReparsePointsBusy` non-zero and cause other path translation callers to wait behind it. |
| Risk | System appears hung while kernel is alive; Task Manager and other processes may stall if they depend on sandboxed process inspection or service calls. |
| Strategy | Do not remove reparse protection. Add bounded waiting, negative-cache behavior, and clear telemetry around slow translation. |
| Proposed Minimal Change | Add an iteration or time budget to the `File_ReparsePointsBusy` wait loop. If the budget expires, return no translation and log a rate-limited diagnostic. |
| Verification Gate | A crafted unavailable path or slow network/reparse target must not block a second path refresh indefinitely. Normal reparse translation still works for local junctions. |
| Open Question | Whether returning no translation on timeout weakens policy. If yes, timeout should fail closed for sensitive settings and fail open only for compatibility-selected paths. |

Task plan:

- [ ] Step 1: Identify all settings that set `CheckReparse = TRUE` through `Process_AddPath`.
- [ ] Step 2: Add timing or bounded-wait instrumentation around `File_TranslateReparsePoints_2` without changing policy decisions.
- [ ] Step 3: Reproduce with a slow/offline path in a controlled Windows VM and record whether the wait loop stalls other calls.
- [ ] Step 4: If reproduced, patch `file_xlat.c` with a bounded wait and rate-limited log.
- [ ] Step 5: Verify local junction translation, offline path behavior, and path refresh latency.

### KPATH-003: Hooked `NtQueryObject(ObjectNameInformation)` Can Still Hit A Known Pipe-Handle Hang

| Field | Content |
|---|---|
| Stage | boundary -> topology -> verify |
| Symptom | Task Manager, Process Explorer, or another handle-inspection tool can appear stuck when querying object names for pipe handles. |
| Evidence | `Sandboxie/core/dll/obj.c:139` states that `NtQueryObject` can lock up forever on synchronous pipe handles with pending reads. `Sandboxie/core/dll/file_dir.c:3083` already avoids calling `SbieDll_GetHandlePath` after identifying `FILE_DEVICE_NAMED_PIPE` with `FileFsDeviceInformation`. Microsoft documents `NtQueryObject` as unstable and only documents `ObjectBasicInformation` / `ObjectTypeInformation` on the Win32 page, while file/pipe identity has dedicated APIs: `GetFileType` returns `FILE_TYPE_PIPE`, `NtQueryVolumeInformationFile(FileFsDeviceInformation)` returns `FILE_FS_DEVICE_INFORMATION`, and `FILE_DEVICE_NAMED_PIPE` is a system device type. |
| Current Owner | `obj.c` owns object-name query mediation for sandboxed user-mode processes. |
| Boundary | Sandboxed process asks Windows for object name; Sandboxie rewrites names for file/key/ipc namespace visibility. |
| Invariant | A name query must not hang forever on object types known to be unsafe for native name query. |
| Hypothesis | `UseDriverObjLookup` does not cover the hooked `Obj_NtQueryObject` path, so a sandboxed handle-inspection flow can still hit the native pipe-name hang. |
| Risk | UI appears frozen; tools that inspect handles amplify the hang; service or RPC calls may queue behind the stuck thread. |
| Strategy | Classify File handles with a file/device-owner API before using object-manager name lookup. Named-pipe File handles must not go through native `NtQueryObject(ObjectNameInformation)` by default; broader driver lookup remains controlled by `UseDriverObjLookup`. |
| Proposed Minimal Change | In `Obj_NtQueryObject`, detect `FILE_DEVICE_NAMED_PIPE` through native `NtQueryVolumeInformationFile(FileFsDeviceInformation)`. Route named-pipe File handles, and all File handles when `UseDriverObjLookup` is enabled, through driver-side `API_GET_FILE_NAME`. Preserve native object-name query for non-pipe File objects and existing key/ipc object flows. |
| Verification Gate | A sandboxed test process holding a synchronous named-pipe handle with pending read must not hang when queried by a sandboxed or injected name-inspection path. |
| Open Question | Whether driver-side `File_Api_GetName` can itself block on all relevant pipe/device objects. It currently uses object names and file-object fields, so this must be stress tested. |

Task plan:

- [x] Step 1: Trace `Obj_NtQueryObject` call flow for file, key, directory, port, event, mutant, section, and semaphore objects with `docs/plan/analyze-kpath-003-workflow.sh`.
- [x] Step 2: Determine whether `Obj_GetObjectType(ObjectHandle)` can identify pipe-backed file handles before native name query. It can only identify the Object Manager type `File`; pipe identity requires file/device-type classification.
- [ ] Step 3: Build a Windows repro program that creates a synchronous named pipe with pending read and calls `NtQueryObject(ObjectNameInformation)` from inside a sandbox.
- [x] Step 4: Patch `obj.c` so pipe-backed file-object name queries avoid native name query by default, while `UseDriverObjLookup` still forces driver lookup for all File objects.
- [ ] Step 5: Verify name rewriting still works for normal file, key, and IPC objects.

Current workflow note:

- `Obj_GetObjectName` has the intended hang-avoidance branch: when `UseDriverObjLookup` is enabled, it calls `SbieApi_GetFileName` instead of native `NtQueryObject(ObjectNameInformation)`.
- Before this mitigation, `Obj_NtQueryObject` did not consult `obj_use_driver_obj_lookup` before its native object-name query path.
- Before this mitigation, `Obj_NtQueryObject` also did not classify named-pipe File handles before native object-name query.
- `Obj_NtQueryObject` still performs native `__sys_NtQueryObject` calls for non-pipe file objects and supported non-file object types, then rewrites file/key/ipc names after a successful query.
- `file_dir.c` already has a named-pipe special case for `NtQueryVolumeInformationFile(FileFsDeviceInformation)`, proving the project already treats pipe-backed handles as a known hang class.
- Static gap now closed by source-level readback: `obj.c` checks `FILE_DEVICE_NAMED_PIPE` before native object-name query for File handles.

Official-source conclusion:

- `NtQueryObject` is not the owner of file/pipe identity. Microsoft's Win32 documentation says it may change or be removed and only documents basic/type object information as available structures.
- `GetFileType` names `FILE_TYPE_PIPE` for sockets, named pipes, or anonymous pipes, proving pipe identity is a file-handle classification, not an object-name query concern.
- `NtQueryVolumeInformationFile(FileFsDeviceInformation)` returns `FILE_FS_DEVICE_INFORMATION`, whose `DeviceType` describes the device object associated with a file object.
- `FILE_DEVICE_NAMED_PIPE` is a Microsoft-defined device type constant.
- Therefore the correct default route is: File object -> file/device classification -> named pipe -> driver lookup or safe failure; native `NtQueryObject(ObjectNameInformation)` remains only for classes not known to be unsafe.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntqueryobject`
- `https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfiletype`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntqueryvolumeinformationfile`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_file_fs_device_information`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/specifying-device-types`

Current implementation note:

- `Obj_NtQueryObject` now computes `use_driver_name_lookup` for File objects when either `UseDriverObjLookup` is enabled or `Obj_IsNamedPipeFileHandle` identifies `FILE_DEVICE_NAMED_PIPE`.
- `Obj_IsNamedPipeFileHandle` uses a native `NtQueryVolumeInformationFile(FileFsDeviceInformation)` pointer captured before the file hooks are installed, avoiding recursion through Sandboxie's own volume-info hook.
- `Obj_GetObjectNameFromDriver` owns the driver lookup packing contract and reports required object-name buffer length, so `Obj_NtQueryObject` can preserve its existing retry-on-small-buffer workflow.
- If driver lookup fails for a driver-routed File object, `Obj_NtQueryObject` now returns that status instead of falling back to native `NtQueryObject(ObjectNameInformation)`.
- This is source-level hardening plus official-route alignment, not full runtime proof. A Windows named-pipe repro is still required to prove the original hang and compatibility behavior.

### KPATH-004: LSA Endpoint Filtering Is Message-ID Denylist, Not Semantic Policy

| Field | Content |
|---|---|
| Stage | schema -> topology -> logic |
| Symptom | Windows logs LSA anonymous policy-handle denial, and Sandboxie may expose compatibility noise or retries around LSA/RPC access. |
| Evidence | `Sandboxie/core/drv/ipc.c:456` opens `\LsaAuthenticationPort`. `Sandboxie/core/drv/ipc_lsa.c:192` filters `\RPC Control\LSARPC_ENDPOINT`. `Sandboxie/core/drv/ipc_lsa.c:246` filters by RPC message ID. `Sandboxie/install/SbieSettings.ini:4049` exposes `OpenLsaEndpoint`. `CHANGELOG.md:3882` records LSARPC endpoint filtering as a security fix. |
| Current Owner | `ipc_lsa.c` owns LSA endpoint filtering; Windows LSA owns actual policy semantics. |
| Boundary | Sandboxed process crosses from application IPC into Windows security-authority control plane. |
| Invariant | LSA mutation and sensitive secret access must not cross the sandbox boundary. Benign identity/query operations should either be brokered, synthesized, or cleanly denied before Windows logs anonymous access. |
| Hypothesis | The current strategy correctly blocks known dangerous LSA operations, but it is too low-level and can still let ambiguous query/open-policy calls reach Windows as anonymous/untrusted attempts. |
| Risk | Compatibility warning noise, retry loops, brittle message-ID mapping across Windows versions, and temptation to enable `OpenLsaEndpoint=y`, which weakens isolation. |
| Strategy | Replace endpoint-level thinking with operation semantics: classify LSA operations as read-self, read-global, mutate-policy, secret/trust/audit, or unknown. Use official MS-LSAD / Win32 LSA shape before changing any policy. |
| Proposed Minimal Change | Deny secret/private-data methods whose opnum alone is sufficient to prove sensitive read/write/create/delete semantics. Do not change `LsarOpenPolicy*` until a payload parser can inspect `DesiredAccess`. |
| Verification Gate | Event ID 6033 must disappear for the target sandboxed app without enabling `OpenLsaEndpoint=y` and without permitting LSA mutation calls. |
| Open Question | Which exact LSA RPC op triggered the event on the user's machine. Event text alone does not identify the sandboxed process or RPC message ID. |

Task plan:

- [ ] Step 1: Capture the exact process and timestamp that triggers Event ID 6033 in Windows Event Viewer.
- [ ] Step 2: Enable Sandboxie IPC tracing for the target box and map the LSA endpoint message ID at the same timestamp.
- [x] Step 3: Add `docs/plan/kpath-004-lsad-spec.md` to preserve the official LSAD shape and separate allowed lookup/query calls from denied mutation/secret/private-data calls.
- [x] Step 4: Deny officially proven secret/private-data opnums in `ipc_lsa.c`: legacy secret create/open/set/query/delete, legacy private-data store/retrieve, and v2 secret/private-data methods.
- [ ] Step 5: Verify that `OpenLsaEndpoint=y` is not required for the target app after the semantic handling change.

Current official-source conclusion:

- MS-LSAD is an object/context-handle protocol. `LsarOpenPolicy*` returns a policy context handle and is semantically governed by `DesiredAccess`; an opnum-only filter cannot distinguish benign lookup access from admin, trust, audit, or secret creation access.
- Secret and private-data methods are different: their method identity alone proves sensitive read/write/open/create/delete semantics. Microsoft documents private data as protected encrypted information including service account passwords, and documents `SECRET_QUERY_VALUE` / `SECRET_SET_VALUE` as query and set access.
- Therefore this task's safe code change is limited to secret/private-data opnums. `LsarOpenPolicy*` remains a parser/instrumentation task gated by KPATH-006 payload-shape proof.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/secmgmt/lsa-policy-objects`
- `https://learn.microsoft.com/en-us/windows/win32/api/ntsecapi/nf-ntsecapi-lsaopenpolicy`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/9456a963-7c21-4710-af77-d0a2f5a72d6b`
- `https://learn.microsoft.com/en-us/windows/win32/secmgmt/policy-object-access-rights`
- `https://learn.microsoft.com/en-us/windows/win32/secmgmt/private-data-object`
- `https://learn.microsoft.com/en-us/windows/win32/secmgmt/private-data-object-access-rights`
- `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lsad/2c6f3cf9-d792-4e8b-9af5-5470f636c20a`

### KPATH-006: RPC Endpoint Filters Need A Spec-Based Opnum Parser

| Field | Content |
|---|---|
| Stage | schema -> boundary -> topology -> verify |
| Symptom | LSA, SAM, spooler, and dynamic endpoint filters treat `ptr[20]` as an RPC message ID/opnum, but the code does not name or validate the IPC/RPC payload shape that makes byte 20 legal. |
| Local Evidence | `Sandboxie/core/drv/ipc_lsa.c:221` reads `msg->u1.s1.DataLength`, `ipc_lsa.c:224` probes exactly that length, then `ipc_lsa.c:226` reads `ptr[20]`. The same pattern appears in `Sandboxie/core/drv/ipc_sam.c:69-74`, `Sandboxie/core/drv/ipc_spl.c:129-158`, and `Sandboxie/core/drv/ipc_port.c:753-758`. |
| Official Spec Evidence | Microsoft RPC supports `NCALRPC` for local same-machine RPC calls, and recommends `ncalrpc` for local communications: `https://learn.microsoft.com/en-us/windows/win32/rpc/selecting-a-protocol-sequence`. MS-RPCE verification-trailer documentation names request-header fields `p_cont_id` and `opnum`, with `opnum` as a `USHORT`: `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-rpce/0a108fbd-c848-4755-9e15-6c4df1c35134`. MS-RPCE security-trailer documentation shows that valid RPC parsing must account for `frag_length`, `auth_length`, data representation, and trailer placement: `https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-rpce/ab45c6a5-951a-4096-b805-7347674dc6ab`. |
| Current Owner | IPC endpoint filter code owns policy decisions for selected RPC endpoints, but it currently has no explicit parser owner for the payload layout. |
| Boundary | Sandboxed user-mode `PORT_MESSAGE` crosses into kernel policy code. `PORT_MESSAGE` is the carrier; RPC/NCALRPC is the payload protocol; endpoint policy must not confuse carrier offset with protocol field identity. |
| Invariant | The code must parse a named message shape before extracting an operation number. `opnum` must be treated as the protocol-defined field width and position for the observed payload shape, not as a magic `UCHAR ptr[20]`. |
| Hypothesis | Sandboxie may be observing either a full MS-RPCE request PDU, a Windows local RPC/LRPC internal frame, or an already-decoded/cut payload. The current code works empirically for some endpoints but has no documented shape contract, so a direct length guard would only hide the deeper parser ambiguity. |
| Risk | A blind `len >= 21` fix prevents one out-of-bounds read class but can preserve an incorrect opnum interpretation. A true fix must avoid both memory unsafety and policy decisions based on the wrong byte. |
| Strategy | Research and instrument first. Capture the first 32-48 bytes of observed LSA/SAM/spooler/dynamic endpoint messages under trace, compare them against MS-RPCE request PDU layout, then introduce a named parser such as `Ipc_TryParseRpcRequestOpnum`. |
| Proposed Minimal Change | Add trace-only payload shape capture without changing valid endpoint policy decisions, centralize the current byte-20 compatibility assumption, then replace it with a shared parser once the observed format is proven. |
| Verification Gate | A captured message must identify whether byte 20 is part of `p_cont_id`, opnum, or a Windows local RPC private field. Only after that can source readback prove every endpoint filter extracts opnum through the named parser and rejects malformed shapes consistently. |
| Open Question | What exact payload shape does `PORT_MESSAGE + sizeof(PORT_MESSAGE)` point to for these local RPC endpoints on supported Windows versions? |

Task plan:

- [ ] Step 1: Preserve the official RPC/NCALRPC and MS-RPCE references in this plan as the legal shape baseline.
- [x] Step 2: Add trace-only capture for the first 32 payload bytes of LSA, SAM, spooler, and dynamic endpoint messages through `Ipc_GetRpcMsgId`.
- [ ] Step 3: Compare captured payloads with MS-RPCE request PDU fields: common header, `frag_length`, `auth_length`, `p_cont_id`, `opnum`, optional object UUID, stub data, and security trailer.
- [ ] Step 4: Decide whether the observed payload is full MS-RPCE, Windows local RPC private framing, or already-decoded endpoint payload.
- [ ] Step 5: Only after Step 4, implement a named parser and remove raw `ptr[20]` reads.
- [ ] Step 6: Verify with normal endpoint traffic and malformed short-message traffic.

Current implementation note:

- `Sandboxie/core/drv/ipc_port.c` now owns `Ipc_GetRpcMsgId`, which centralizes the existing byte-20 assumption and logs `RPC0` / `RPC1` payload-shape records when IPC tracing is enabled.
- `Sandboxie/core/drv/ipc_lsa.c`, `ipc_sam.c`, `ipc_spl.c`, and dynamic port filtering now call the helper instead of directly reading `ptr[20]`.
- This is still research instrumentation, not a final parser. The next gate is captured Windows payload evidence.

Upstream handling note:

- Prefer issue-first disclosure for KPATH-006. This is a protocol-shape and compatibility question, not a ready behavioral fix.
- The issue should present local source evidence, official RPC/MS-RPCE references, and captured payload traces once available.
- A PR should wait until the payload shape is proven and the maintainer agrees on the expected compatibility contract.
- If a PR is later opened, keep it narrow: one shared parser/helper, no broad endpoint policy changes, and include malformed short-message regression proof.

### KPATH-005: Synchronous User-Mode Service Calls Have No Universal Timeout

| Field | Content |
|---|---|
| Stage | topology -> action -> verify |
| Symptom | A sandboxed process may block while waiting for `SbieSvc`, and multiple stuck requests can make the system feel frozen. |
| Evidence | `Sandboxie/core/dll/callsvc.c:277` sends request chunks with `NtRequestWaitReplyPort`. `callsvc.c:356` waits for response chunks the same way. `Sandboxie/core/svc/PipeServer.cpp:349` receives requests with `NtReplyWaitReceivePort`. `PipeServer.cpp:958` calls the target handler synchronously. Microsoft documents ALPC ETW events for send, receive, wait-for-reply, wait-for-new-message, and stop-wait, and the WinDbg LPC page states LPC is now emulated in ALPC and `!alpc` should be used instead of `!lpc`. |
| Current Owner | `callsvc.c` owns client-side service calls; `PipeServer.cpp` owns dispatch. |
| Boundary | Sandboxed user-mode process crosses into SbieSvc broker for privileged or host-visible work. |
| Invariant | A compatibility broker must not let one handler block unrelated clients indefinitely. |
| Hypothesis | Some service handlers have local timeouts, but the base request/reply path has no universal watchdog. A stuck handler can starve caller threads and possibly service capacity. |
| Risk | System appears hung without a kernel crash; Task Manager may also wait if it touches the affected process or handles. |
| Strategy | Follow the OS owner first: capture ALPC wait states with ETW or WinDbg before changing Sandboxie control flow. Sandboxie source instrumentation is only a semantic correlation layer from ALPC wait to Sandboxie `msgid` / handler, not the primary proof. |
| Proposed Minimal Change | Do not add a universal timeout yet. First document an ALPC ETW / `!alpc` repro workflow. Then, if correlation is still missing, add `SbieTrace`-gated begin/end records around `SbieDll_CallServer` and `PipeServer::CallTarget` to map OS waits to Sandboxie handlers. |
| Verification Gate | During a reproduced hang, ETW must show whether the client is in ALPC wait-for-reply and whether the service has a matching receive/wait/new-message/stop-wait transition. Sandboxie trace must identify the `msgid` / handler only after the OS wait state is proven. |
| Open Question | Which service message IDs are involved in the user's hang. Current evidence is architectural, not a reproduced cause. |

Task plan:

- [x] Step 1: Research official Windows posture for LPC/ALPC waits before changing Sandboxie IPC code.
- [x] Step 2: Write an ALPC ETW / WinDbg capture note for the Windows VM repro: enable ALPC kernel events, reproduce hang, inspect wait-for-reply and service receive/wait events.
- [ ] Step 3: Only if OS-level correlation is insufficient, add `SbieTrace`-gated begin/end correlation around `SbieDll_CallServer` and `PipeServer::CallTarget`.
- [ ] Step 4: Reproduce hang and map blocked caller to service handler.
- [ ] Step 5: If one handler is responsible, add targeted timeout or move that handler to an isolated worker path.
- [ ] Step 6: Verify normal broker calls still succeed and long legitimate operations are not cut off.

Official-source conclusion:

- The ALPC ETW provider is the correct first observation surface for this class of wait. It exposes send, receive, wait-for-reply, wait-for-new-message, and stop-wait event types.
- Microsoft's WinDbg `!lpc` page says LPC is now emulated in ALPC and points the investigator to `!alpc`; therefore a Sandboxie-local timeout is not the first diagnostic move.
- `NtRequestWaitReplyPort` / `NtReplyWaitReceivePort` are the local carrier in this codebase, but the wait truth belongs to the OS ALPC/LPC subsystem. Sandboxie app-level traces can only map the OS wait to a `msgid`, target server, and handler.

Official references:

- `https://learn.microsoft.com/en-us/windows/win32/etw/alpc`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-lpc`

### PLAT-001: Secure Boot CA/KEK Update Is Not Applied To Firmware

| Field | Content |
|---|---|
| Stage | perceive -> schema -> verify |
| Symptom | Windows reports that Secure Boot CA/key material still needs updating for this device class. |
| Evidence | User-provided TPM-WMI Secure Boot event data: `BaseBoardManufacturer=ASUSTeK COMPUTER INC.`, `FirmwareManufacturer=American Megatrends Inc.`, `FirmwareVersion=2902`, `OEMModelBaseBoard=Z97-K`, `OSArchitecture=amd64`, `UpdateType=0`, `HResult=0`. Microsoft documents Event ID 1801 as updated certificates not yet applied to device firmware; Event ID 1808 is the completion signal. |
| Current Owner | Platform firmware and Windows Secure Boot update flow own DB, DBX, and KEK state. Sandboxie does not own this boundary. |
| Boundary | Firmware Secure Boot trust store controls what bootloaders and pre-OS code can be trusted before Windows and Sandboxie start. |
| Invariant | The boot trust chain must reject revoked or obsolete boot components and must contain the required newer Microsoft Secure Boot certificate material before Windows considers the device fully updated. |
| Hypothesis | This old ASUS Z97-K / AMI firmware bucket is not yet high-confidence or has not completed the firmware variable update path, so Windows logs the event even though the event write itself reports `HResult=0`. |
| Risk | Platform remains exposed to boot-chain trust debt. This is not a Sandboxie escape by itself, but any pre-OS compromise bypasses Sandboxie's runtime boundary because it happens before Sandboxie exists. |
| Strategy | Treat this as a separate platform hardening task. Do not weaken Secure Boot, do not manually clear firmware keys casually, and do not mix this with Sandboxie LSA/kernel path fixes. |
| Proposed Minimal Change | Inventory Secure Boot variables and TPM-WMI events first. Apply Microsoft/OEM-guided Secure Boot certificate update only after backup and BitLocker/recovery-key precautions. |
| Verification Gate | `Confirm-SecureBootUEFI` succeeds, DB/KEK contain the expected 2023 Microsoft certificates, and TPM-WMI Event ID 1808 appears. Event ID 1801 alone means incomplete. |
| Open Question | Whether ASUS Z97-K firmware 2902 can safely receive the new Secure Boot DB/KEK update automatically, or requires OEM/manual handling. |

Task plan:

- [ ] Step 1: Record exact Event ID and timestamp from Windows Event Viewer.
- [ ] Step 2: Run Secure Boot state readback with `Confirm-SecureBootUEFI` and `Get-SecureBootUEFI db,kek,dbx`.
- [ ] Step 3: Query TPM-WMI Secure Boot events for IDs `1801`, `1802`, `1803`, and `1808`.
- [ ] Step 4: Check whether BitLocker/device encryption is active before any firmware or Secure Boot key change.
- [ ] Step 5: If no Event ID 1808 exists, follow Microsoft/OEM Secure Boot certificate update guidance for this firmware bucket and verify again.

## Execution Order

1. Fix or prove `KPATH-001` first because it is deterministic memory safety.
2. Fix or prove `KPATH-006` because it is another local kernel boundary parser defect with clear source evidence.
3. Instrument `KPATH-005` before changing timeout behavior because the current hang source is not yet reproduced.
4. Test `KPATH-003` with a named-pipe repro because it directly matches the Task Manager style symptom.
5. Investigate `KPATH-004` with event timestamp and IPC trace because the LSA event alone is not enough.
6. Treat `KPATH-002` as a path-setting stress test and hardening task after the deterministic bug is handled.
7. Track `PLAT-001` separately as platform trust-chain hardening, not as a Sandboxie defect.

## Verification Commands

These commands are local source readback only:

```bash
git -C /home/claude/projects/sandboxie/audit-kernel-path status --short --branch
rg -n "Api_CopyStringFromUser|File_ReparsePointsBusy|Obj_NtQueryObject|Ipc_CheckPortRequest_LsaEP|NtRequestWaitReplyPort" /home/claude/projects/sandboxie/audit-kernel-path/Sandboxie
```

Windows-only verification, to run later in a VM or Windows build host:

```text
Build Sandboxie driver and user-mode DLLs.
Enable Driver Verifier or Special Pool for SbieDrv.
Reproduce config update through SbieIni.exe with --drv mode.
Reproduce named-pipe NtQueryObject hang inside a sandbox.
Reproduce Event ID 6033 with IPC tracing enabled.
```

## Review Checklist

- [ ] Every issue has a local evidence path.
- [ ] Every issue has an owner, boundary, invariant, hypothesis, risk, strategy, and verification gate.
- [ ] No code patch is performed before plan review.
- [ ] No registry workaround weakens Windows LSA security.
- [ ] Any future change keeps `OpenLsaEndpoint=y` as a diagnostic escape hatch, not a recommended fix.
- [ ] Every RPC endpoint filter validates message length before reading opnum byte offset 20.
- [ ] Secure Boot CA/KEK update work is verified by firmware variable readback and Event ID 1808, not by `HResult=0` alone.
