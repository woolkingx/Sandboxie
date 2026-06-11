# SREV-330: Conf Import Template Comment Contract

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> action -> verify |
| Input artifact | `Sandboxie/core/drv/conf.c`, SREV-073 config list/map publication contract |
| Output artifact | `docs/plan/srev-330-conf-import-template-comment-contract.schema.json`, `docs/plan/check-srev-330.py`, `docs/plan/check-srev-330.sh`, ledger fragment, comment-only source clarification |
| Owner | `Sandboxie/core/drv/conf.c` include import and template merge comments |
| Acceptance gate | targeted source checker, core coverage, and diff checkpoint |

## Data

`Sandboxie/core/drv/conf.c` owns the in-kernel configuration model. Sections
and settings are stored in both ordered lists and hash maps, with list order
preserved for enumeration and maps used for keyed lookup. SREV-073 already owns
the publication rollback contract for `Conf_Add_Sections` and
`Conf_Add_Setting`.

The relevant comment-risk nodes in this SREV are:

```text
Conf_Import_Include
STATUS_TOO_MANY_SESSIONS
Conf_Drop_Section
Conf_Import_AllIncludes
Conf_ImportBox / ImportBox
Conf_Merge_AllTemplates
Conf_Merge_Templates
Conf_Template / Template
map_key_iter
map_next
```

## Official Shape

This SREV does not cross a Microsoft API boundary. The legal shape is local:
`CONF_DATA` owns sections/settings, `Conf_Add_Sections` and `Conf_Add_Setting`
publish list/map nodes under the SREV-073 contract, and `map_key_iter` owns
keyed iteration over matching setting names.

## Schema

Local schema:

```text
docs/plan/srev-330-conf-import-template-comment-contract.schema.json
```

`CONF_IMPORT_TEMPLATE_COMMENT_CONTRACT` says:

- include import failure rolls back a newly imported section unless the parser
  already observed additional sections;
- `STATUS_TOO_MANY_SESSIONS` is the local signal for the forward-compatible
  additional-section case;
- `ImportBox` iteration is a keyed lookup over settings named by
  `Conf_ImportBox`;
- template merge iteration is a keyed lookup over settings named by
  `Conf_Template`;
- placeholder comment text must not use `Xxx`, because the audit coverage
  checker treats `XXX` as a risk token;
- this SREV changes comments and proof only.

## Topology

```text
Conf_Read
  -> Conf_Import_AllIncludes
  -> GlobalSettings ImportBox keyed settings
  -> Conf_Import_Include / Conf_Import_Includes
  -> optional Conf_Drop_Section rollback

Conf_Read
  -> Conf_Merge_AllTemplates
  -> Conf_Merge_Templates
  -> keyed Template settings
  -> Conf_Merge_Template
```

The include import path owns imported-section rollback. The template merge path
owns keyed iteration over template settings. Neither comment changes the
SREV-073 list/map publication owner.

## Logic Risk

The old comments mixed a vague "something went wrong" phrase with placeholder
`Xxx` text. That is weak topology: future review could miss that
`STATUS_TOO_MANY_SESSIONS` is the explicit additional-section compatibility
signal, and the audit checker kept reporting the `Xxx` placeholders as `XXX`
risk hits.

## Fix

Comment-only source clarification. The source now names SREV-330, states the
single-section rollback / additional-section preserve rule, and replaces
`IncludeBox=Xxx` / `Template=Xxx` placeholders with keyed-map ownership
language.

No `Conf_Import_Include` status handling, `Conf_Drop_Section` call,
`Conf_ImportBox` key, `Conf_Template` key, `map_key_iter`, `map_next`, template
merge ordering, section publication, or settings publication behavior changed.

## Acceptance Gate

`docs/plan/check-srev-330.py` validates the draft-07 schema, source comments,
unchanged rollback condition, unchanged keyed ImportBox and Template iterators,
SREV-073 adjacency, stale `went wrong` and `Xxx` comment removal from the
target blocks, combined ledger entry, and split ledger fragment.

Windows gate: no Windows runtime gate is required for this comment-only
classification. Future behavior changes to include import rollback or template
merge ordering inherit SREV-073's low-memory/config reload runtime gate.
