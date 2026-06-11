# Runtime Gates

This package is source-gated reference material. The following gates describe
the Windows runtime evidence still required before the closed PR patches or
related SREV items should be treated as merge-ready.

The proof chain is:

```text
core source -> SREV/KPATH ledger -> source checker -> Windows runtime gate
```

## SREV-027 / PR #5410 / WFP Classify Logging

Source claim:

```text
WFP_classify captures fixed traffic facts only.
Formatting and Session_MonitorPut run from a deferred worker path.
```

Required runtime proof:

- Windows driver build succeeds.
- Driver Verifier runs with IRQL checking and DDI compliance enabled.
- `NetFwTrace` works enabled and disabled.
- IPv4, IPv6, TCP, and UDP traffic are covered.
- blocked, permitted, loopback, and non-loopback paths are covered.
- `BlockInternet`, `BlockLoopback`, and rule-based block/permit cases are
  covered.
- process churn and rule refresh are exercised while traffic is active.
- monitor log readback proves process id, address, port, protocol, direction,
  and action.
- high-rate traffic exercises queue overflow/drop behavior.
- WFP unload and driver unload drain the deferred queue and worker.
- negative control proves `WFP_classify` has no inline
  `Session_MonitorPut*` or `RtlStringCbPrintf*` path.

## SREV-172 / PR #5405 / SetupAPI Status Projection

Source claim:

```text
SetupAPI/CfgMgr32 hook paths preserve failure status instead of projecting
blocked or failed driver-package installs as success.
```

Required runtime proof:

- Windows DLL build succeeds.
- signed and unsigned catalog verification smoke tests run through the hook
  boundary.
- blocked driver-package install smoke proves `CM_Add_Driver_PackageW` and
  `CM_Add_Driver_Package_ExW` return non-success `CONFIGRET` values.
- `SBIE2205` or equivalent diagnostic readback is visible for the blocked path.
- installer compatibility observation confirms callers do not break from an
  unintended status shape.

## SREV-344 / PR #5410 / WFP Transaction Abort Cleanup

Source claim:

```text
WFP transaction abort failure is captured/logged during failed install cleanup
instead of silently ignored.
```

Required runtime proof:

- Windows WFP failure-injection covers transaction abort success and failure.
- BFE/RPC shutdown or equivalent service-boundary failure is exercised.
- dynamic session cleanup is exercised.
- Driver Verifier stays clean.
- repeated enable/disable does not leak WFP objects or leave stale state.

## SREV-345 / PR #5410 / WFP Rule-Load Fail-Closed Logging

Source claim:

```text
WFP_LoadRules owns allocation-failure logging.
WFP_UpdateProcess owns fail-closed state and partial rule cleanup.
```

Required runtime proof:

- allocation failure or low-memory injection reaches the rule-load path.
- exactly one relevant `MSG_1201` style diagnostic is produced for the failure.
- internet access fails closed when the rule list is partial.
- partial rule lists are cleaned up.
- repeated refresh does not accumulate leaked or stale WFP entries.

## Completion Rule

Passing the source checker is not enough. A runtime gate is complete only when
the corresponding Windows command/log/readback shows the expected boundary and
the failure case is observed, not inferred.
