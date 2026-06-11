# Core API Review Boundary

This package documents a source-level review of Sandboxie `core` API and
Windows boundary correctness. The reviewed surface is larger than the two closed
PR patches. PR `#5410` carried the main public explanation of that scope: the
work is about Windows API compatibility and correctness, not only one WFP code
path.

## Core Layer Scope

The review focuses on `Sandboxie/core` crossings where API shape, memory
contract, or runtime level matters:

- buffer sizes and counted strings;
- handle ownership, close ownership, and duplicate ownership;
- object lifetime and cleanup on partial failure;
- access rights, tokens, impersonation, and privilege checks;
- RPC/IPC wire shape and sentinel values;
- service to driver crossings;
- user to kernel crossings;
- WFP classify callback constraints and deferred execution;
- SetupAPI/CfgMgr32 status projection.

These categories matter because Sandboxie often sits between a Windows caller
and a Windows API contract. A source path can look locally valid while still
breaking a caller-visible API shape, returning the wrong status, crossing at the
wrong IRQL, or hiding a boundary failure behind a success projection.

## Audit Snapshot

The packaged audit checkpoint records:

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

This means the source coverage pass named every reviewable `Sandboxie/core`
file in the ledger, but it does not mean Windows runtime proof is complete.

## Source Gate vs Runtime Proof

The review boundary is:

```text
core source -> SREV/KPATH ledger -> source checker -> Windows runtime gate
```

The source ledger and checkers are useful because they make the API boundary and
expected invariant explicit. They are not a substitute for Windows runtime
evidence. A source-gated item can still require:

- Windows build proof;
- Driver Verifier proof;
- API status readback from real callers;
- monitor/log readback;
- failure-injection proof;
- unload, cleanup, and lifetime proof.

## Public Review Shape

The fork `master` source tree is based on the latest local `audit-kernel-path`
snapshot. Relative to the local original `46927b56` baseline, it includes `194`
changed files under `Sandboxie/core`. The package gives maintainers three usable
surfaces:

- a short review narrative in this file;
- a mapping from PRs and SREV items to files in [`REVIEW-MAP.md`](REVIEW-MAP.md);
- explicit runtime proof gates in [`RUNTIME-GATES.md`](RUNTIME-GATES.md).

The raw archive remains available under [`audit/`](audit/), but the package
entry points should be read first.
