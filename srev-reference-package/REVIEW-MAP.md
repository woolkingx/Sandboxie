# Review Map

This map connects the full `audit-kernel-path` source snapshot, the closed
upstream PRs, the relevant SREV entries, focused patch exports, and runtime
proof owners.

## Full Source Snapshot

The fork default branch is based on local `audit-kernel-path`:

```text
baseline: 46927b56 1.17.7
snapshot: 39e96683 Record local UAC packet readback capture
core changed files: 194 under Sandboxie/core
```

The source tree is therefore not patch-only. The patch files below are focused
exports for the two closed upstream PRs.

## PR And SREV Map

| Upstream item | SREV entries | Source file | Patch/reference |
|---|---|---|---|
| PR `#5410` | SREV-027, SREV-344, SREV-345 | `Sandboxie/core/drv/wfp.c` | [`patches/0002-fix-defer-WFP-traffic-logging-from-classify.patch`](patches/0002-fix-defer-WFP-traffic-logging-from-classify.patch) |
| PR `#5405` | SREV-172 | `Sandboxie/core/dll/setup.c` | [`patches/0001-Preserve-setup-hook-failure-status.patch`](patches/0001-Preserve-setup-hook-failure-status.patch) |
| Core audit checkpoint | 352 ledger entries | `Sandboxie/core/**` | [`audit/reports/core-coverage-audit.md`](audit/reports/core-coverage-audit.md), [`audit/reports/systematic-code-review-ledger.md`](audit/reports/systematic-code-review-ledger.md) |

## Key Ledger Entries

- [`audit/ledger/srev-027.md`](audit/ledger/srev-027.md) - WFP NetFwTrace must
  not write monitor logs inline from `WFP_classify`.
- [`audit/ledger/srev-172.md`](audit/ledger/srev-172.md) -
  SetupAPI/CfgMgr32 status projection must not hide blocked or failed
  driver-install edges as success.
- [`audit/ledger/srev-344.md`](audit/ledger/srev-344.md) - WFP transaction
  abort failure should be captured/logged during install cleanup.
- [`audit/ledger/srev-345.md`](audit/ledger/srev-345.md) - WFP rule-load
  allocation failure logging and fail-closed ownership must be explicit.

## #5410 Core Path

PR `#5410` is the clearest example of the core API boundary problem. The source
patch is small, but the API issue is larger:

```text
WFP classify callback
  -> fixed classify-side capture only
  -> bounded nonpaged queue
  -> deferred worker
  -> formatting and Session_MonitorPut outside classify
```

The boundary exists because WFP classify callbacks can run at runtime levels
where inline string formatting and monitor writeback are unsafe unless every
memory and execution precondition is proven.

## #5405 Core Path

PR `#5405` is the adjacent API-status projection case:

```text
SetupAPI/CfgMgr32 caller
  -> Sandboxie setup hook
  -> driver package install attempt
  -> status returned to caller
```

The bug class is not the install policy itself. The API boundary is whether a
blocked or failed driver-package path is projected back to the caller as
success.

## Raw Archive Layout

The raw audit files were reorganized so the directory is navigable:

| Directory | Contents |
|---|---|
| [`audit/reports/`](audit/reports/) | Human reports and checkpoint summaries. |
| [`audit/ledger/`](audit/ledger/) | Split SREV ledger entries, one per SREV id. |
| [`audit/srev/`](audit/srev/) | Raw SREV docs and schemas copied from the audit worktree. |
| [`audit/checkers/`](audit/checkers/) | Source checker scripts and shell wrappers. |
| [`audit/kpath/`](audit/kpath/) | KPATH raw docs and schemas. |
| [`audit/local/`](audit/local/) | Local validation checkpoints and Windows-test notes. |
| [`audit/tools/`](audit/tools/) | Ledger split/read helper scripts and coordinate notes. |

Use [`RUNTIME-GATES.md`](RUNTIME-GATES.md) before treating a source patch as
runtime-proved.
