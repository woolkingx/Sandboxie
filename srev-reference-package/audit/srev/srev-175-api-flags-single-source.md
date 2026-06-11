# SREV-175: Driver API Flag Single Source

## Stage Gate

```text
stage: schema -> boundary -> topology -> logic -> action -> verify
input artifact: Sandboxie/core/drv/api_flags.h, Sandboxie/core/drv/conf.h, configuration query callers, Microsoft DuplicateHandle and ZwDuplicateObject flag documentation
output artifact: driver API flag constants have one local owner and configuration helpers consume that owner instead of duplicating wire flag definitions
owner: Sandboxie/core/drv/api_flags.h
acceptance gate: docs/plan/check-srev-175.py and docs/plan/check-srev-175.sh
```

## Data

`api_flags.h` is the shared flag vocabulary for several Sandboxie boundaries:

- configuration query index flags such as `CONF_GET_NO_GLOBAL`,
  `CONF_GET_NO_EXPAND`, and `CONF_GET_NO_TEMPLS`;
- native handle duplication flags and Sandboxie-only duplicate routing flags;
- resource monitor type/disposition/result bits;
- process state flags returned by `API_QUERY_PROCESS_INFO`;
- configuration reload flags;
- driver feature flags returned by `API_QUERY_DRIVER_INFO`.

`conf.h` also defined `CONF_GET_NO_GLOBAL`, `CONF_GET_NO_EXPAND`, and
`CONF_GET_NO_TEMPLS` locally with the same numeric values as `api_flags.h`.
Those values cross user-mode tools, DLL helpers, service code, and driver
configuration code. They are not private implementation details of `conf.h`.

## Official Shape

- Microsoft documents `DuplicateHandle` options as `DUPLICATE_CLOSE_SOURCE` and
  `DUPLICATE_SAME_ACCESS`:
  `https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle`.
- Microsoft documents `ZwDuplicateObject` options as
  `DUPLICATE_SAME_ATTRIBUTES`, `DUPLICATE_SAME_ACCESS`, and
  `DUPLICATE_CLOSE_SOURCE`:
  `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-zwduplicateobject`.

The configuration, monitor, process, reload, and feature flags are local
Sandboxie wire contracts. Their legal source is the project-owned
`api_flags.h`, not duplicated consumer headers.

## Schema

`DRIVER_API_FLAG_SINGLE_SOURCE` says:

- `api_flags.h` owns Sandboxie driver API flag constants.
- Configuration query flags are cross-boundary wire flags, not private
  `conf.h` implementation constants.
- `conf.h` may consume `CONF_GET_*` constants by including `api_flags.h`, but it
  must not duplicate their numeric definitions.
- Microsoft-owned duplicate options remain named in `api_flags.h` with the
  documented `DuplicateHandle`/`ZwDuplicateObject` values.
- Sandboxie-only duplicate routing bits (`DUPLICATE_INHERIT` and
  `DUPLICATE_INTO_OTHER`) remain above the documented low option bits and are
  stripped before native `ZwDuplicateObject` calls.
- Resource monitor, process, reload, and feature flags are unchanged.
- SREV-175 does not change any numeric flag value, caller behavior, config query
  expansion semantics, handle duplication routing, monitor logging, process info
  reporting, reload behavior, or driver feature reporting.
- Linux source gates are not Windows build/runtime proof.

## Topology

Legal ownership after this SREV:

```text
api_flags.h
  -> owns CONF_GET_* / duplicate / monitor / process / reload / feature bits

conf.h
  -> includes api_flags.h
  -> declares configuration APIs that consume CONF_GET_* bits

conf.c / gui.c / conf_user.c / user-mode callers
  -> consume the same api_flags.h values across the driver API boundary
```

The key rule is simple: one cross-boundary bit value gets one owner.

## Logic Risk

Duplicate macro definitions are quiet until they drift. If a future change
updates the driver API owner but misses the consumer copy, the same numeric
field can mean different things depending on include path. That is exactly the
kind of schema split that turns a small configuration flag into a policy
boundary bug.

The correct repair is not to add another abstraction. It is to remove the
duplicate consumer definitions and make `conf.h` depend on the shared owner.

## Action

`conf.h` now includes `api_flags.h` and no longer defines
`CONF_GET_NO_GLOBAL`, `CONF_GET_NO_EXPAND`, or `CONF_GET_NO_TEMPLS` locally.
The numeric values remain unchanged in `api_flags.h`.

## Verification

Source-level gates:

```bash
python3 docs/plan/check-srev-175.py
bash docs/plan/check-srev-175.sh
python3 docs/plan/check-core-coverage.py
```

Full closure matrix:

```bash
python3 docs/plan/check-srev-175.py &&
bash docs/plan/check-srev-175.sh &&
python3 docs/plan/check-core-coverage.py &&
for s in docs/plan/check-srev-0*.sh docs/plan/check-srev-1*.sh docs/plan/check-kpath-0*.sh; do bash "$s"; done &&
git diff --check
```

Runtime/build gate: Windows driver, DLL, service, and app build proving the
include topology still compiles; configuration query smoke for
`CONF_GET_NO_GLOBAL`, `CONF_GET_NO_EXPAND`, and `CONF_GET_NO_TEMPLS`; duplicate
handle smoke proving Sandboxie-only routing bits are still stripped before the
native duplication call.
