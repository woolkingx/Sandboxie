#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-330 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-330 failed: stale {label} remains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-330-conf-import-template-comment-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-330 failed: schema is not draft-07")
if schema.get("id") != "CONF_IMPORT_TEMPLATE_COMMENT_CONTRACT":
    raise SystemExit("SREV-330 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/conf.c":
    raise SystemExit("SREV-330 failed: wrong owner")

contracts = "\n".join(schema["contracts"])
for term in [
    "include import failure rolls back",
    "STATUS_TOO_MANY_SESSIONS is the local additional-section compatibility signal",
    "ImportBox iteration uses map_key_iter",
    "Template merge iteration uses map_key_iter",
    "placeholder comment text must not use Xxx",
    "changes comments and proof only",
]:
    require(contracts, term, "schema contracts")

conf = (ROOT / "Sandboxie/core/drv/conf.c").read_text()
spec = (ROOT / "docs/plan/srev-330-conf-import-template-comment-contract.md").read_text()
srev_073 = (ROOT / "docs/plan/srev-073-conf-publish-rollback.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-330.md").read_text()

include_start = conf.index("_FX NTSTATUS Conf_Import_Include(")
include_end = conf.index("// Conf_Import_AllIncludes", include_start)
include_func = conf[include_start:include_end]

all_includes_start = conf.index("_FX NTSTATUS Conf_Import_AllIncludes(")
all_includes_end = conf.index("// Conf_Merge_AllTemplates", all_includes_start)
all_includes_func = conf[all_includes_start:all_includes_end]

merge_all_start = conf.index("_FX NTSTATUS Conf_Merge_AllTemplates(")
merge_all_end = conf.index("// Conf_Merge_Templates", merge_all_start)
merge_all_func = conf[merge_all_start:merge_all_end]

merge_templates_start = conf.index("_FX NTSTATUS Conf_Merge_Templates(")
merge_templates_end = conf.index("// Conf_Merge_Template", merge_templates_start)
merge_templates_func = conf[merge_templates_start:merge_templates_end]

for term in [
    "SREV-330: roll back the imported section on a single-section import",
    "If additional sections were present, keep the imported",
    "status = STATUS_TOO_MANY_SESSIONS;",
    "if (!NT_SUCCESS(status) && status != STATUS_TOO_MANY_SESSIONS)\n            Conf_Drop_Section(data, section);",
]:
    require(include_func, term, "Conf_Import_Include source")

for stale in [
    "Drop the section if something went wrong",
    "for future extensibility",
]:
    reject(include_func, stale, "include rollback comment")

for term in [
    "SREV-330: iterate only ImportBox settings through the keyed settings map.",
    "map_iter_t iter2 = map_key_iter(&section->settings_map, Conf_ImportBox);",
    "while (map_next(&section->settings_map, &iter2))",
]:
    require(all_includes_func, term, "Conf_Import_AllIncludes source")

reject(all_includes_func, "IncludeBox=Xxx", "ImportBox placeholder")

for term in [
    "SREV-330: scan the section for Template setting entries.",
    "status = Conf_Merge_Templates(data, session_id, sandbox, sandbox, sandbox->name);",
]:
    require(merge_all_func, term, "Conf_Merge_AllTemplates source")

reject(merge_all_func, "Template=Xxx", "Template scan placeholder")

for term in [
    "SREV-330: iterate only Template settings through the keyed settings map.",
    "map_iter_t iter2 = map_key_iter(&section->settings_map, Conf_Template);",
    "while (map_next(&section->settings_map, &iter2))",
]:
    require(merge_templates_func, term, "Conf_Merge_Templates source")

reject(merge_templates_func, "Template=Xxx", "Template iterator placeholder")

for term in [
    "Conf_Add_Sections",
    "Conf_Add_Setting",
    "map-before-list publish order",
]:
    require(srev_073, term, "SREV-073 adjacency")

for term in [
    "CONF_IMPORT_TEMPLATE_COMMENT_CONTRACT",
    "No `Conf_Import_Include` status handling",
    "Windows gate: no Windows runtime gate is required",
    "SREV-073",
]:
    require(spec, term, "spec")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-330",
    "owner: Sandboxie/core/drv/conf.c",
    "spec: docs/plan/srev-330-conf-import-template-comment-contract.md",
    "schema: docs/plan/srev-330-conf-import-template-comment-contract.schema.json",
    "checker: docs/plan/check-srev-330.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-330: Conf Import Template Comment Contract",
    "CONF_IMPORT_TEMPLATE_COMMENT_CONTRACT",
    "Conf_Import_AllIncludes",
    "Conf_Merge_Templates",
    "SREV-073",
]:
    require(ledger, term, "combined ledger")

print("SREV-330 schema/source gate passed")
