# SREV-022 / SREV-027: Kernel Runtime Capture Playbook

## Stage Gate

| Field | Value |
|---|---|
| Stage | schema |
| Input artifact | SREV-022, SREV-027, `Sandboxie/core/drv/file.c`, `Sandboxie/core/drv/wfp.c`, Microsoft ACCESS_STATE / SECURITY_SUBJECT_CONTEXT / WFP classify / IRQL DDI documentation |
| Output artifact | `docs/plan/srev-022-027-kernel-runtime-capture.schema.json`, `docs/plan/check-srev-022-027-kernel-runtime-capture.py`, runtime capture checklist |
| Owner | kernel runtime evidence contract for unsupported font subject-context rewrite and deferred WFP classify logging |
| Acceptance gate | targeted checker validates source/spec adjacency and the evidence schema; Windows capture remains the runtime gate |

## Official Surface

SREV-022 and SREV-027 share one kernel rule: the code path that happens to make
compatibility work is not automatically the legal owner of the Windows runtime
state it touches.

For font opens, Microsoft documents `ACCESS_STATE` as the state of an access in
progress, but says drivers must not modify it directly. Microsoft also documents
`SECURITY_SUBJECT_CONTEXT` as a captured subject context for access validation
and auditing, with its members reserved for system use. Object/token references
still have normal reference ownership, but the local code is substituting a
token into a system-owned subject context, so release ownership must be proven
before any dereference/restore change.

For WFP logging, Microsoft documents `classifyFn` as callable at
`IRQL <= DISPATCH_LEVEL`. Safe string formatting is only arbitrary-IRQL when all
manipulated strings are resident. `ExAcquireResourceExclusiveLite` is limited to
`IRQL <= APC_LEVEL`, and pool allocations touched at `DISPATCH_LEVEL` must be
nonpaged. Therefore the classify callback may capture bounded nonpaged facts,
but monitor formatting and `Session_MonitorPutEx` belong to a later
`PASSIVE_LEVEL` executor unless the whole monitor path is made DISPATCH-safe.

Official references:

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_access_state
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ns-wdm-_security_subject_context
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-obreferenceobject
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-psreferenceprimarytoken
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/fwpsk/nc-fwpsk-fwps_callout_classify_fn0
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntstrsafe/nf-ntstrsafe-rtlstringcbprintfa
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exacquireresourceexclusivelite
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exallocatepool2
```

Legal route:

```text
official kernel DDI shape -> Windows runtime capture -> local owner decision
```

Illegal route:

```text
local compatibility path works once -> kernel ownership and IRQL contracts are satisfied
```

## Data

Each capture record must identify shared runtime coordinates:

- Windows build, architecture, Sandboxie commit, driver build, box name,
  process image, capture tool, and timestamp.
- Feature path: `font-token-subject-context` for SREV-022 or
  `wfp-deferred-logger` for SREV-027.
- Machine key: `feature path: `font-token-subject-context``.
- Machine key: `feature path: `wfp-deferred-logger``.
- Route result: `font-token-substituted`, `font-token-not-applicable`,
  `wfp-classify-captured`, `wfp-deferred-written`, `wfp-logging-disabled`,
  `negative-control-passed`, `verifier-failure`, or `combined`.
- Evidence coordinates: ETW trace path, debugger transcript, Driver Verifier
  result, poolmon or pool-tracking result, monitor-log readback path, and
  operator notes.

SREV-022 font-token records must include:

- Path topology: minifilter `IRP_MJ_CREATE`, legacy XP parse-proc, or negative
  control.
- Requestor shape: kernel-mode win32k delayed font open, user-mode open,
  active impersonation, or non-sandboxed process.
- Path class: real Fonts path, sandbox-boxed font path, non-font path, missing
  file, or reparse/symlinked font path.
- Access mask class: exact font read/execute mask, denied write/delete mask, or
  unrelated read path.
- Token state: `proc->primary_token`, `ClientToken`, `PrimaryToken`,
  impersonation level, reference delta before/after create, downstream release
  observation, restore observation, and driver unload readback.
- Failure controls: `Process_Find` miss, missing `proc->primary_token`,
  `Obj_GetParseName` failure, boxed-path allocation failure, create failure,
  and Digital Guardian or equivalent callback-sensitive endpoint regression.

SREV-027 WFP logger records must include:

- Classify coordinates: IRQL, layer id, direction, protocol, remote address,
  remote port, action, rule match, trace-enabled bit, and logging-disabled
  decision readback.
- Memory owner: nonpaged fixed-size record, pool tag, bounded queue or ring
  capacity, allocation-failure policy, overflow/drop counter, and pool tracking.
- Synchronization owner: DISPATCH-safe producer synchronization, absence of
  ERESOURCE/pageable buffer/blocking wait/pageable function in `WFP_classify`,
  and negative proof that `Session_MonitorPut*` and `RtlStringCbPrintf*` are not
  called inline.
- Deferred executor: PASSIVE_LEVEL worker, monitor formatting outside classify,
  `Session_MonitorPutEx` outside classify, process/sandbox/WFP/rule/monitor
  lifecycle handling, unload drain/cancel behavior, and monitor-log readback.
- Verifier and traffic stress: Driver Verifier IRQL/DDI checking, Special Pool
  for the logger tag, forced allocation failure, IPv4/IPv6 TCP/UDP,
  loopback/non-loopback, blocked/permitted traffic, process churn, and rule
  refresh.

## Schema

Machine-readable capture records use:

```text
docs/plan/srev-022-027-kernel-runtime-capture.schema.json
```

The schema accepts one record per runtime observation. A record can carry a
font-token payload, a WFP logger payload, or both when one Windows run captures
both paths.

## Topology

SREV-022:

```text
win32k delayed font open
  -> Sandboxie minifilter or XP parse-proc path
  -> File_ReplaceTokenIfFontRequest
  -> unsupported SECURITY_SUBJECT_CONTEXT token substitution
  -> filesystem/security path consumes access state
  -> reference release / no-release observation
```

SREV-027:

```text
WFP classify callback at <= DISPATCH_LEVEL
  -> policy map + block/permit decision
  -> bounded nonpaged capture
  -> PASSIVE_LEVEL executor
  -> Session_MonitorPutEx monitor write
```

Forbidden edge:

```text
WFP_classify at DISPATCH_LEVEL
  -x-> Session_MonitorPutEx / RtlStringCbPrintf / pageable monitor ring
```

## Required Captures

SREV-022 positive and negative controls:

| Capture | Expected Proof |
|---|---|
| Kernel-mode win32k delayed font open on real Fonts path | Token substitution happens and font load succeeds |
| Boxed font path from the GDI helper | Boxed-path compatibility route is covered |
| User-mode file open | Subject-context substitution does not run |
| Active impersonation | Existing client token blocks substitution |
| Denied write/delete access | Access-mask gate blocks substitution |
| Missing token / missing process / parse failure | Failure controls do not substitute a token |
| Repeated font opens | Token references, paged pool, and nonpaged pool do not grow |
| Digital Guardian or equivalent endpoint | Callback-sensitive regression does not BSOD |

SREV-027 positive and negative controls:

| Capture | Expected Proof |
|---|---|
| `NetFwTrace=y` with blocked traffic | Nonpaged capture records block decision and deferred monitor output |
| `NetFwTrace=y` with permitted traffic | Nonpaged capture records permit decision and deferred monitor output |
| `NetFwTrace` disabled | Block/permit decision is unchanged and no trace write occurs |
| IPv4/IPv6 TCP/UDP loopback/non-loopback stress | No verifier violation, dropped decision, or corrupt monitor record |
| Rule refresh and process churn | Queue lifecycle does not write stale process/rule state |
| Forced allocation failure / queue overflow | Drop counter increments and traffic decision remains correct |
| Inline logging negative control | No `Session_MonitorPut*`, `RtlStringCbPrintf*`, ERESOURCE, pageable allocation, or `session->monitor_log` touch from `WFP_classify` |

## Logic Risk

SREV-022 can fail in two directions: a leak if the substituted reference is
never consumed, or a use-after-free/BSOD if the code rebalances a reference that
the downstream security path already owns. SREV-027 also has a two-sided risk:
inline logging can crash at high IRQL, while a deferred logger can silently drift
traffic decisions or lose monitor records if owner, capacity, and lifecycle are
not explicit.

The correct posture is evidence first. Source readback can prove that unsafe
paths are guarded today. It cannot prove Windows token-reference ownership or a
future logger's IRQL/lifecycle behavior.

## Acceptance Gate

Linux/source gate:

```bash
bash docs/plan/check-srev-022-027-kernel-runtime-capture.sh
bash docs/plan/check-srev-022.sh
bash docs/plan/check-srev-027.sh
```

Windows gate:

1. Build the Sandboxie driver for each target architecture.
2. Capture SREV-022 font-token observations across minifilter and XP parse-proc
   topologies where supported.
3. Capture SREV-027 deferred logger observations under Driver Verifier IRQL/DDI
   checking and traffic stress.
4. Store one JSON record per build/architecture/process/control.
5. Validate records against
   `docs/plan/srev-022-027-kernel-runtime-capture.schema.json`.
6. Only after records validate may SREV-022 release/restore behavior or
   SREV-027 NetFwTrace logger behavior change.
