# Sandboxie Isolation Coordinate

## Stage Gate

```text
stage: schema -> topology
input artifact: user product intent, Sandboxie path policy review, SREV/KPATH audit findings
output artifact: compact policy coordinate for later schema and issue work
owner: docs/plan/sandboxie-isolation-coordinate.md
acceptance gate: later SREV/KPATH entries must preserve or explicitly reject this coordinate when changing path policy semantics
```

## Coordinate

```text
domain: per-box OS view and object access mediation
origin: a sandboxed process sees a clean machine unless policy grants more
axes:
  host-readable: host state may be observed when the policy allows reads
  sandbox-writable: writes land in the box copy, not in host state
  fresh-machine: default user-facing profile hides unrelated installed residue
  custom-exception: explicit app/workflow exceptions punch narrow holes
metric: smallest policy surface that preserves compatibility and isolation
boundary: host mutation, host-private data, and unrelated installed-app residue are outside the default legal view
legal_transition: read host -> write sandbox copy -> expose through approved exchange/sync path
invariant: write authority and durable state stay owned by the sandbox unless a named policy explicitly crosses the boundary
invalid_state: many unrelated per-app toggles become the real policy model
```

## Product Rule

The simple model is not "more controls everywhere". It is a small number of
semantic levels:

| Level | Meaning |
|---|---|
| Host read | The sandbox may read selected host state. |
| Sandbox write | Any mutation goes to the sandbox copy. |
| Fresh machine | The default view looks like a new Windows install plus the target app. |
| Custom exception | Narrow, named exceptions exist only when required for compatibility. |

This is a topology rule, not a UI feature list. Future code review should ask
whether a path, registry, IPC, service, or credential edge preserves this shape.
When compatibility needs a hole, the hole should have an owner, a boundary, and
a verification gate.
