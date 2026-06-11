# Audit Archive Layout

This directory contains the raw SREV/core audit evidence copied into the fork
reference package. It is intentionally preserved as evidence, but no longer kept
as a flat dump.

Read the package entry points first:

```text
../README.md
../CORE-API-REVIEW.md
../REVIEW-MAP.md
../RUNTIME-GATES.md
```

## Directories

| Directory | Contents |
|---|---|
| [`reports/`](reports/) | Human reports and checkpoint summaries. |
| [`ledger/`](ledger/) | Split SREV ledger entries, one per SREV id. |
| [`srev/`](srev/) | Raw SREV docs and JSON schemas copied from the audit worktree. |
| [`checkers/`](checkers/) | Source checker scripts and shell wrappers. |
| [`kpath/`](kpath/) | KPATH raw docs and schemas. |
| [`local/`](local/) | Local validation checkpoints and Windows-test notes. |
| [`tools/`](tools/) | Ledger split/read helper scripts and coordinate notes. |

## Primary Files

- [`reports/core-coverage-audit.md`](reports/core-coverage-audit.md)
- [`reports/systematic-code-review-ledger.md`](reports/systematic-code-review-ledger.md)
- [`ledger/srev-027.md`](ledger/srev-027.md)
- [`ledger/srev-172.md`](ledger/srev-172.md)
- [`ledger/srev-344.md`](ledger/srev-344.md)
- [`ledger/srev-345.md`](ledger/srev-345.md)
- [`srev/srev-022-027-kernel-runtime-capture-playbook.md`](srev/srev-022-027-kernel-runtime-capture-playbook.md)

## Preservation Note

Raw files may still mention their original audit-worktree paths or local plan
locations. This package preserves those files as evidence. The cleaned entry
points above are the maintained navigation layer for the fork.
