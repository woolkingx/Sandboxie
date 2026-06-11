# SREV Core API Review Package

This directory is the public reference package for the fork. Its purpose is to
make the Sandboxie `core` layer API review readable from the default branch,
without asking maintainers to follow closed PR branches or unpack a flat audit
dump.

The central issue is not only the two closed code patches. The larger review is
about Windows API compatibility and correctness in `Sandboxie/core`: buffer
sizes, counted strings, handle ownership, object lifetime, access rights,
RPC/IPC wire shape, service/driver boundaries, user/kernel crossings, WFP
classify runtime constraints, and SetupAPI/CfgMgr32 status projection.

Related upstream PRs:

- `#5410` - WFP NetFwTrace deferred logging from classify. This is the main
  public review thread for the broader core API / runtime-boundary discussion.
- `#5405` - SetupAPI/CfgMgr32 failure status projection.

The fork's default `master` branch is based on the latest local
`audit-kernel-path` snapshot, so the reviewed source changes are applied in the
default source tree. Relative to the local original `46927b56` baseline, that
snapshot changes `194` files under `Sandboxie/core`.

The patch files in this package are only focused exports for the two closed PRs.
They are not the full fork diff.

## Reading Order

1. [`CORE-API-REVIEW.md`](CORE-API-REVIEW.md) - what the review is actually
   about.
2. [`REVIEW-MAP.md`](REVIEW-MAP.md) - how PRs, SREV items, source files,
   focused patch exports, and the full source snapshot connect.
3. [`RUNTIME-GATES.md`](RUNTIME-GATES.md) - what still needs Windows runtime
   proof.
4. [`audit/README.md`](audit/README.md) - where the raw audit evidence lives
   after cleanup.

## Code References

Focused patch exports:

- [`patches/0001-Preserve-setup-hook-failure-status.patch`](patches/0001-Preserve-setup-hook-failure-status.patch)
- [`patches/0002-fix-defer-WFP-traffic-logging-from-classify.patch`](patches/0002-fix-defer-WFP-traffic-logging-from-classify.patch)

Source files affected by those patches:

| PR | File | Scope |
|---|---|---|
| #5405 | `Sandboxie/core/dll/setup.c` | Preserve SetupAPI/CfgMgr32 failure status instead of projecting blocked or failed driver-install edges as success. |
| #5410 | `Sandboxie/core/drv/wfp.c` | Move NetFwTrace logging out of WFP classify into a deferred logger path and keep classify-side capture fixed/resident. |

## Audit Entry Points

Primary reports:

- [`audit/reports/core-coverage-audit.md`](audit/reports/core-coverage-audit.md)
- [`audit/reports/systematic-code-review-ledger.md`](audit/reports/systematic-code-review-ledger.md)

Relevant ledger entries:

- [`audit/ledger/srev-027.md`](audit/ledger/srev-027.md)
- [`audit/ledger/srev-172.md`](audit/ledger/srev-172.md)
- [`audit/ledger/srev-344.md`](audit/ledger/srev-344.md)
- [`audit/ledger/srev-345.md`](audit/ledger/srev-345.md)

Related runtime-capture playbook:

- [`audit/srev/srev-022-027-kernel-runtime-capture-playbook.md`](audit/srev/srev-022-027-kernel-runtime-capture-playbook.md)

Coverage snapshot from the audit checkpoint:

```text
core_files=287
reviewable_core_files=276
ledger_entries=352
reviewable_files_named_in_ledger=276
reviewable_files_not_named_in_ledger=0
patched_source_needs_windows=231
runtime_design_open=0
named_runtime_capture=0
```

## Proof Boundary

Most of the audit material is source-gated, not runtime-proved. The important
boundary is:

```text
core source -> SREV/KPATH ledger -> source checker -> Windows runtime gate
```

Use this package as reference material:

- inspect the core API and Windows boundary review;
- inspect, split, or rewrite the source tree changes;
- split the material into smaller future work;
- run the Windows proof gates before treating the source state as merge-ready.
