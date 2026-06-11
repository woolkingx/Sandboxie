---
kind: srev-ledger-entry
id: SREV-175
title: Driver API Flag Single Source
status: patched-source-level-after-official-duplicate-handle-flag-shape-and-local-driver-api-flag-schema-review-needs-windows-build-runtime-proof
owner: Sandboxie/core/drv/api_flags.h
spec: docs/plan/srev-175-api-flags-single-source.md
schema: docs/plan/srev-175-api-flags-single-source.schema.json
checker: docs/plan/check-srev-175.py
runtime_gate: "Windows driver DLL service and app build plus configuration query and duplicate handle routing smoke"
---

### SREV-175: Driver API Flag Single Source

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official duplicate-handle flag shape and local driver API flag schema review; needs Windows build/runtime proof |
| Evidence | `Sandboxie/core/drv/api_flags.h` was the highest-ranked unnamed reviewable core file after SREV-174. It owns cross-boundary constants for configuration query flags, duplicate-object routing, resource monitor classes, process state, configuration reload, and driver feature reporting. `Sandboxie/core/drv/conf.h` also defined `CONF_GET_NO_GLOBAL`, `CONF_GET_NO_EXPAND`, and `CONF_GET_NO_TEMPLS` with the same numeric values. Those values cross user-mode tools, DLL helpers, service code, and driver configuration code, so they are not private `conf.h` constants. |
| Data | `Sandboxie/core/drv/api_flags.h`, `Sandboxie/core/drv/conf.h`, `Sandboxie/core/drv/conf.c`, `Sandboxie/core/drv/ipc.c`, `Sandboxie/core/dll/secure.c`, `CONF_GET_NO_GLOBAL`, `CONF_GET_NO_EXPAND`, `CONF_GET_NO_TEMPLS`, `DUPLICATE_CLOSE_SOURCE`, `DUPLICATE_SAME_ACCESS`, `DUPLICATE_SAME_ATTRIBUTES`, `DUPLICATE_INHERIT`, `DUPLICATE_INTO_OTHER`, `MONITOR_TYPE_MASK`, `SBIE_FLAG_VALID_PROCESS`, `SBIE_CONF_FLAG_RECONFIGURE`, and `SBIE_FEATURE_FLAG_WFP`. |
| Schema | `DRIVER_API_FLAG_SINGLE_SOURCE` says `api_flags.h` owns Sandboxie driver API flag constants; configuration query flags are cross-boundary wire flags, not private `conf.h` implementation constants; `conf.h` consumes those flags by including `api_flags.h`; Microsoft-owned duplicate options remain named with the documented `DuplicateHandle` / `ZwDuplicateObject` values; Sandboxie-only duplicate routing bits remain above the documented low option bits and are stripped before native `ZwDuplicateObject`; resource monitor, process, reload, and feature flags are unchanged. |
| Topology | Legal flow is `api_flags.h` owning `CONF_GET_*` / duplicate / monitor / process / reload / feature bits, `conf.h` including that owner while declaring configuration APIs, and `conf.c` / `gui.c` / `conf_user.c` / user-mode callers consuming the same flag values across the driver API boundary. |
| Logic Risk | Duplicate macro definitions are quiet until they drift. If a future change updates the driver API owner but misses the consumer copy, the same numeric field can mean different things depending on include path. That is a schema split at a policy boundary, not just a cosmetic duplicate. |
| Official Shape | `docs/plan/srev-175-api-flags-single-source.md` records Microsoft `DuplicateHandle` and `ZwDuplicateObject` option flags as the external shape for the duplicate constants. The configuration, monitor, process, reload, and feature flags are local Sandboxie wire contracts owned by `api_flags.h`. `docs/plan/srev-175-api-flags-single-source.schema.json` records the JSON Schema draft-07 local `DRIVER_API_FLAG_SINGLE_SOURCE` contract. |
| Fix | `conf.h` now includes `api_flags.h` and no longer defines `CONF_GET_NO_GLOBAL`, `CONF_GET_NO_EXPAND`, or `CONF_GET_NO_TEMPLS` locally. The numeric values remain unchanged in `api_flags.h`. No caller behavior, config query expansion semantics, duplicate-object routing, monitor logging, process info reporting, reload behavior, or driver feature reporting changed. |
| Acceptance Gate | `docs/plan/check-srev-175.py` validates the draft-07 schema, official references, key flag values in `api_flags.h`, removal of duplicate `CONF_GET_*` definitions from `conf.h`, `conf.h` inclusion of `api_flags.h`, driver duplicate custom flag stripping, DLL duplicate routing, and ledger fragment; `docs/plan/check-srev-175.sh` is the matrix wrapper. Runtime/build gate: Windows driver, DLL, service, and app build; configuration query smoke for `CONF_GET_NO_GLOBAL`, `CONF_GET_NO_EXPAND`, and `CONF_GET_NO_TEMPLS`; duplicate handle smoke proving Sandboxie-only routing bits are still stripped before native duplication. |
