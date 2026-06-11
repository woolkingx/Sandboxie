# Sandboxie Core API Review Reference Fork

This fork is a reference repository for a Sandboxie `core` layer API and
Windows boundary review. It is not an alternate Sandboxie distribution. The
default branch is based on the local `audit-kernel-path` snapshot, so the source
tree includes the reviewed core-layer code changes. The review material is also
kept in one visible directory so maintainers can inspect, split, rewrite, or
ignore it without tracking separate PR branches.

Upstream project:

```text
https://github.com/sandboxie-plus/Sandboxie
```

## Reference Package

The package is here:

```text
srev-reference-package/
```

Start with:

```text
srev-reference-package/README.md
srev-reference-package/CORE-API-REVIEW.md
srev-reference-package/REVIEW-MAP.md
srev-reference-package/RUNTIME-GATES.md
```

## Review Focus

The main review focus is Windows API compatibility and correctness in
`Sandboxie/core`, especially:

- buffer sizes and counted strings;
- handle ownership and object lifetime;
- access rights and token boundaries;
- RPC/IPC wire shape;
- service, driver, and user/kernel crossings;
- WFP classify callback runtime constraints;
- SetupAPI/CfgMgr32 status projection.

This scope was discussed in upstream PR `#5410`. PR `#5405` is the adjacent
SetupAPI/CfgMgr32 status-projection patch. Both PRs are closed; the material is
kept here as a reference package instead of an active upstream blocker.

## Included Material

- The default source tree contains the latest `audit-kernel-path` snapshot,
  including `194` changed files under `Sandboxie/core` relative to the local
  original `46927b56` baseline.
- [`srev-reference-package/CORE-API-REVIEW.md`](srev-reference-package/CORE-API-REVIEW.md)
  explains the core-layer API review boundary.
- [`srev-reference-package/REVIEW-MAP.md`](srev-reference-package/REVIEW-MAP.md)
  maps upstream PRs, SREV items, source files, and patch files.
- [`srev-reference-package/RUNTIME-GATES.md`](srev-reference-package/RUNTIME-GATES.md)
  records the Windows runtime proof still required.
- [`srev-reference-package/patches/`](srev-reference-package/patches/)
  contains two focused closed-PR patch exports. These patch files are not the
  complete fork diff; the complete code state is the default source tree.
- [`srev-reference-package/audit/`](srev-reference-package/audit/)
  contains the source audit archive, ledger, checkers, reports, and local
  validation notes.

Focused patch exports:

```text
srev-reference-package/patches/0001-Preserve-setup-hook-failure-status.patch
srev-reference-package/patches/0002-fix-defer-WFP-traffic-logging-from-classify.patch
```

## Proof Boundary

Most of this material is source-gated reference work, not Windows runtime-proof
closure.

The intended proof chain is:

```text
core source -> SREV/KPATH ledger -> source checker -> Windows runtime gate
```

The package should be read as review material and source evidence, not as a
claim that the code is merge-ready without Windows testing.
