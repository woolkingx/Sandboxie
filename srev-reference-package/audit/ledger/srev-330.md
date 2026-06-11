---
kind: srev-ledger-entry
id: SREV-330
title: Conf Import Template Comment Contract
status: source-comment-classified-after-local-conf-data-shape-review-no-behavior-change
owner: Sandboxie/core/drv/conf.c
spec: docs/plan/srev-330-conf-import-template-comment-contract.md
schema: docs/plan/srev-330-conf-import-template-comment-contract.schema.json
checker: docs/plan/check-srev-330.py
runtime_gate: No Windows runtime gate is required for this comment-only classification; future include/template behavior changes inherit SREV-073 low-memory config reload proof
---
### SREV-330: Conf Import Template Comment Contract

| Field | Content |
|---|---|
| Severity | [low] |
| Status | source comment classified after local `CONF_DATA` / list-map shape review; no source behavior change |
| Evidence | `Sandboxie/core/drv/conf.c` owns in-kernel configuration sections/settings as ordered lists plus hash maps. `Conf_Import_Include` treats `STATUS_TOO_MANY_SESSIONS` as the local additional-section compatibility signal and skips `Conf_Drop_Section` in that case. `Conf_Import_AllIncludes` iterates `Conf_ImportBox` entries with `map_key_iter`; `Conf_Merge_Templates` iterates `Conf_Template` entries with `map_key_iter`. The old comments used vague failure wording and `Xxx` placeholders that the audit checker reported as `XXX` risk hits. |
| Data | `Conf_Import_Include`, `STATUS_TOO_MANY_SESSIONS`, `Conf_Drop_Section`, `Conf_Import_AllIncludes`, `Conf_ImportBox`, `Conf_Merge_AllTemplates`, `Conf_Merge_Templates`, `Conf_Template`, `map_key_iter`, `map_next`, and SREV-073. |
| Schema | `CONF_IMPORT_TEMPLATE_COMMENT_CONTRACT` says include import failure rolls back a newly imported section unless additional sections were observed; `STATUS_TOO_MANY_SESSIONS` is the local additional-section compatibility signal; `ImportBox` iteration uses `map_key_iter` over settings named by `Conf_ImportBox`; template merge iteration uses `map_key_iter` over settings named by `Conf_Template`; placeholder comment text must not use `Xxx` because `XXX` is an audit risk token; this SREV changes comments and proof only. |
| Topology | `Conf_Read -> Conf_Import_AllIncludes -> GlobalSettings ImportBox keyed settings -> Conf_Import_Include / Conf_Import_Includes -> optional Conf_Drop_Section rollback`; `Conf_Read -> Conf_Merge_AllTemplates -> Conf_Merge_Templates -> keyed Template settings -> Conf_Merge_Template`. |
| Logic Risk | The old comments mixed a vague failure phrase with placeholder text. Future review could miss that `STATUS_TOO_MANY_SESSIONS` is the explicit additional-section compatibility signal, and the audit checker kept reporting the `Xxx` placeholders as `XXX` risk hits. |
| Official Shape | This SREV does not cross a Microsoft API boundary. The legal shape is local: `CONF_DATA` owns sections/settings, SREV-073 owns config node publication rollback, and `map_key_iter` owns keyed setting iteration. |
| Fix | Comment-only source clarification. The source now names SREV-330, states the single-section rollback / additional-section preserve rule, and replaces `IncludeBox=Xxx` / `Template=Xxx` placeholders with keyed-map ownership language. No `Conf_Import_Include` status handling, `Conf_Drop_Section` call, `Conf_ImportBox` key, `Conf_Template` key, `map_key_iter`, `map_next`, template merge ordering, section publication, or settings publication behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-330.py` validates the draft-07 schema, source comments, unchanged rollback condition, unchanged keyed ImportBox and Template iterators, SREV-073 adjacency, stale `went wrong` and `Xxx` comment removal from the target blocks, combined ledger entry, and split ledger fragment; `docs/plan/check-srev-330.sh` is the targeted wrapper. Windows gate: no Windows runtime gate is required for this comment-only classification. Future behavior changes to include import rollback or template merge ordering inherit SREV-073's low-memory/config reload runtime gate. |
