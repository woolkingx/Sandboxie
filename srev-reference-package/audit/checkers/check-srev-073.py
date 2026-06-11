#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-073 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-073-conf-publish-rollback.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-073 failed: schema is not draft-07")
if schema.get("id") != "CONF_PUBLISH_ROLLBACK":
    raise SystemExit("SREV-073 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "List_Insert_Before and List_Insert_After mutate the ordered list without a failure return",
    "map_insert and map_append can fail and return NULL",
    "map insertion must succeed before the section or setting is inserted into the ordered list",
    "failed string allocation releases already-owned local allocations",
    "failed map insertion releases node-owned strings and node",
    "may return NULL only when no list-visible node was published",
]:
    require(contracts, term, "schema")

conf = (ROOT / "Sandboxie/core/drv/conf.c").read_text()
map_c = (ROOT / "Sandboxie/common/map.c").read_text()
list_c = (ROOT / "Sandboxie/common/list.c").read_text()
spec = (ROOT / "docs/plan/srev-073-conf-publish-rollback.md").read_text()
ledger = read_combined_ledger(ROOT)

section_start = conf.index("_FX CONF_SECTION* Conf_Add_Sections(")
section_end = conf.index("// Conf_Read_Header", section_start)
section_func = conf[section_start:section_end]

setting_start = conf.index("_FX CONF_SETTING* Conf_Add_Setting(")
setting_end = conf.index("// Conf_Read_Settings", setting_start)
setting_func = conf[setting_start:setting_end]

for term in [
    "if (! section->name) {\n        Mem_Free(section, sizeof(CONF_SECTION));\n        return NULL;\n    }",
    "if(map_insert(&data->sections_map, section->name, section, 0) == NULL) {\n        Mem_FreeString(section->name);\n        Mem_Free(section, sizeof(CONF_SECTION));\n        return NULL;\n    }",
    "List_Insert_Before(&data->sections, NULL, section);",
    "List_Insert_After(&data->sections, NULL, section);",
]:
    require(section_func, term, "Conf_Add_Sections source")

if section_func.index("map_insert(&data->sections_map") > section_func.index("List_Insert_Before(&data->sections"):
    raise SystemExit("SREV-073 failed: section list publish appears before map publish")
if "List_Insert_After(&data->sections, NULL, section);\n    if(map_insert(&data->sections_map" in section_func:
    raise SystemExit("SREV-073 failed: stale section list-before-map pattern remains")

for term in [
    "if (! setting->name) {\n        Mem_Free(setting, sizeof(CONF_SETTING));\n        return NULL;\n    }",
    "if (! setting->value) {\n        Mem_FreeString(setting->name);\n        Mem_Free(setting, sizeof(CONF_SETTING));\n        return NULL;\n    }",
    "if(map_append(&section->settings_map, setting->name, setting, 0) == NULL) {\n        Mem_FreeString(setting->value);\n        Mem_FreeString(setting->name);\n        Mem_Free(setting, sizeof(CONF_SETTING));\n        return NULL;\n    }",
    "List_Insert_Before(&section->settings, NULL, setting);",
    "List_Insert_After(&section->settings, NULL, setting);",
]:
    require(setting_func, term, "Conf_Add_Setting source")

if setting_func.index("map_append(&section->settings_map") > setting_func.index("List_Insert_Before(&section->settings"):
    raise SystemExit("SREV-073 failed: setting list publish appears before map publish")
if "List_Insert_After(&section->settings, NULL, setting);\n    if(map_append(&section->settings_map" in setting_func:
    raise SystemExit("SREV-073 failed: stale setting list-before-map pattern remains")

for term in [
    "if(!node)  goto fail;",
    "if (!map_resize(m, nbuckets)) goto fail;",
    "return NULL;",
]:
    require(map_c, term, "map failure contract")

for term in [
    "void List_Insert_Before(LIST *list, void *oldelem, void *newelem)",
    "void List_Insert_After(LIST *list, void *elem, void *newelem)",
]:
    require(list_c, term, "list mutation contract")

for term in [
    "srev-073-conf-publish-rollback.schema.json",
    "Sandboxie/common/map.c",
    "Sandboxie/common/list.c",
]:
    require(spec, term, "spec")

for term in [
    "### SREV-073: Config Section/Setting Publish Rollback",
    "CONF_PUBLISH_ROLLBACK",
    "srev-073-conf-publish-rollback.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-073 schema/source gate passed")
