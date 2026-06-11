---
kind: srev-ledger-entry
id: SREV-073
title: Config Section/Setting Publish Rollback
status: patched-source-level-after-local-config-list-map-schema-analysis-needs-windows-l
owner: Sandboxie/core/drv/conf.c
spec: docs/plan/srev-073-conf-publish-rollback.md
schema: docs/plan/srev-073-conf-publish-rollback.schema.json
checker: docs/plan/check-srev-073.py
runtime_gate: "low-memory `Conf_Read`, `ImportBox`, template merge, and `API_UPDATE_CONF` add paths do not leave list-visible/map-invisible config nodes, while normal ordered enumeration remains unchanged"
---
### SREV-073: Config Section/Setting Publish Rollback

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after local config/list/map schema analysis; needs Windows low-memory config reload/import/update runtime proof |
| Evidence | `Sandboxie/core/drv/conf.c` stores config sections and settings in paired ordered lists and hash maps. `Sandboxie/common/list.c` `List_Insert_Before` / `List_Insert_After` mutate the list without returning failure, while `Sandboxie/common/map.c` `map_add` can return `NULL` when node allocation or bucket growth fails. Before this patch, `Conf_Add_Sections` and `Conf_Add_Setting` inserted into lists before checking map insertion, so a failed map insert could return `NULL` while leaving a list-visible, map-invisible node. Earlier string allocation failures also leaked partially-created local nodes/strings. |
| Data | `CONF_DATA.sections`, `CONF_DATA.sections_map`, `CONF_SECTION.settings`, `CONF_SECTION.settings_map`, allocated `CONF_SECTION` / `CONF_SETTING` nodes, and owned name/value strings. |
| Schema | `CONF_PUBLISH_ROLLBACK` says the config owner may publish a new section or setting to the ordered list only after the corresponding map insertion succeeds. Until both indexes are updated, the helper owns rollback; returning `NULL` means no list-visible node was published. |
| Topology | Config parse/update input creates a private node, publishes it to the map index, then publishes it to the ordered list. The list/map pair is one logical index boundary for later enumeration and lookup. |
| Logic Risk | A half-published config node breaks the parser's topology: list enumeration can see data that map lookup cannot find, while callers believe the add failed. In import/update failure paths, that can leave stale config state or leak parse-pool allocations until later pool teardown. |
| Official Shape | This is an internal Sandboxie config/list/map contract, so `docs/plan/srev-073-conf-publish-rollback.md` records local source references rather than a Microsoft API. `docs/plan/srev-073-conf-publish-rollback.schema.json` records the JSON Schema draft-07 local `CONF_PUBLISH_ROLLBACK` contract. |
| Fix | `Conf_Add_Sections` now frees the section node when name allocation fails, inserts into `sections_map` before list publication, and frees the section name/node if map insertion fails. `Conf_Add_Setting` now frees the setting node/name/value along allocation-failure paths, inserts into `settings_map` before list publication, and frees value/name/node if map append fails. |
| Acceptance Gate | `docs/plan/check-srev-073.py` validates the draft-07 schema, local list/map failure shape, allocation cleanup, map-before-list publish order, stale list-before-map patterns removal, and ledger entry; `docs/plan/check-srev-073.sh` is the matrix wrapper. Windows gate: low-memory `Conf_Read`, `ImportBox`, template merge, and `API_UPDATE_CONF` add paths do not leave list-visible/map-invisible config nodes, while normal ordered enumeration remains unchanged. |
