# SREV-073: Config Section/Setting Publish Rollback

## Data

`Sandboxie/core/drv/conf.c` stores parsed configuration data in paired list and
hash-map indexes:

```text
CONF_DATA.sections list
CONF_DATA.sections_map
CONF_SECTION.settings list
CONF_SECTION.settings_map
CONF_SECTION / CONF_SETTING node storage
node name/value strings
```

The local data owner is the config parser and updater. `Conf_Add_Sections` and
`Conf_Add_Setting` create nodes that later readers enumerate by list order and
look up through the corresponding map.

## Local Shape

This is an internal Sandboxie data-structure contract, not an external
Microsoft API. The relevant local definitions are:

```text
Sandboxie/core/drv/conf.c
Sandboxie/common/list.h
Sandboxie/common/list.c
Sandboxie/common/map.h
Sandboxie/common/map.c
```

`List_Insert_*` mutates the list immediately and has no failure return. `map_add`
can fail when node allocation or bucket growth fails and returns `NULL`.

## Schema

Local schema:

```text
docs/plan/srev-073-conf-publish-rollback.schema.json
```

The publish contract is:

```text
allocated node owns its name/value strings until successfully published
map insertion must succeed before the node is inserted into the list
failed map insertion releases the node-owned strings and node
failed string allocation releases already-owned local allocations
caller receives NULL only when no list/map-visible node was published
```

## Topology

```text
parse/update input -> private node allocation -> map publish -> list publish
```

The map/list pair is one logical index. The creator owns rollback until the
node is visible in both indexes.

## Logic Risk

Before this patch, `Conf_Add_Sections` and `Conf_Add_Setting` inserted nodes
into their lists before checking whether the map insertion succeeded. If map
allocation failed, the helper returned `NULL` while leaving an unindexed list
node behind. Callers then treated the add as failed, which could leave stale
configuration nodes reachable by list enumeration but invisible to map lookup.

Earlier allocation failures also leaked partially-created nodes or strings
inside the current parse pool until the pool was eventually deleted.

## Fix

`Conf_Add_Sections` now releases the section node if name allocation fails, and
inserts the section into `sections_map` before publishing it to the ordered
section list. If map insertion fails, it releases the local section name and
node.

`Conf_Add_Setting` now releases the setting node if name allocation fails,
releases name and node if value allocation fails, and inserts the setting into
`settings_map` before publishing it to the ordered settings list. If map append
fails, it releases value, name, and node.

## Acceptance Gate

`docs/plan/check-srev-073.py` validates the draft-07 schema, local list/map
references, cleanup on allocation failure, map-before-list publish order, stale
list-before-map patterns removal, and ledger entry.

Windows gate: low-memory config reload/import/update paths do not leave a
section or setting visible in list enumeration after the helper reports failure,
and normal config order remains stable when map insertion succeeds.
