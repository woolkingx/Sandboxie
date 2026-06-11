---
kind: srev-ledger-entry
id: SREV-179
title: Config ANSI List Exact Match
status: patched-source-level-after-official-crt-string-comparison-review-needs-windows-api-trace-runtime-proof
owner: SbieDll_CheckStringInListA config-list membership helper
spec: docs/plan/srev-179-config-ansi-list-exact-match.md
schema: docs/plan/srev-179-config-ansi-list-exact-match.schema.json
checker: docs/plan/check-srev-179.py
runtime_gate: "Windows DLL build plus ApiSkipTrace exact match and prefix false-positive smoke"
---

### SREV-179: Config ANSI List Exact Match

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official CRT string-comparison review; needs Windows API trace runtime proof |
| Evidence | `Sandboxie/core/dll/config.c` was the highest-ranked unnamed reviewable core file after SREV-178. It owns DLL-side config query helpers and list membership helpers over `SbieApi_QueryConfAsIs`. `SbieDll_CheckStringInList` compares wide caller strings with `_wcsicmp(buf, string) == 0`, but `SbieDll_CheckStringInListA`, used by `Sandboxie/core/dll/dllhook.c` for `ApiSkipTrace`, returned true when only the wide config entry reached `L'\0'`. That made `ApiSkipTrace=Abc` match API name `Abcd`. |
| Data | `SbieDll_CheckStringInListA`, `SbieDll_CheckStringInList`, `SbieApi_QueryConfAsIs`, `buf[66]`, ANSI caller `string`, wide config entry, `ApiSkipTrace`, `dllhook.c`, and API trace hook names. |
| Schema | `CONFIG_ANSI_LIST_EXACT_MATCH` says `SbieDll_CheckStringInListA` owns ANSI caller-string membership checks against wide config-list entries; a match is legal only when every compared byte/character is equal and both strings reach their terminator at the same position; shorter wide entries and shorter ANSI caller strings are both non-matches; case-sensitive comparison and `STATUS_BUFFER_TOO_SMALL` skip behavior remain unchanged. |
| Topology | Legal flow is `dllhook API name char* -> SbieDll_CheckStringInListA(name, NULL, "ApiSkipTrace") -> SbieApi_QueryConfAsIs wide config entry -> Config_IsEqualAnsiString(buf, name) -> both strings must terminate together -> exact membership decision`. |
| Logic Risk | The old helper turned an exact API-name list into a prefix list whenever the configured value was shorter than the API name. For trace policy, this can skip instrumentation for unintended APIs that share a prefix with a configured entry. |
| Official Shape | `docs/plan/srev-179-config-ansi-list-exact-match.md` records Microsoft CRT string comparison semantics. `docs/plan/srev-179-config-ansi-list-exact-match.schema.json` records the JSON Schema draft-07 local `CONFIG_ANSI_LIST_EXACT_MATCH` contract. |
| Fix | `Config_IsEqualAnsiString` now performs the mixed wide/ANSI comparison and returns true only when both sides reach their terminator together. `SbieDll_CheckStringInListA` uses that helper instead of returning true when only the wide config entry ended. No wide `SbieDll_CheckStringInList`, config query flags, trace hook installation, or `ApiSkipTrace` entry meaning changed. |
| Acceptance Gate | `docs/plan/check-srev-179.py` validates the draft-07 schema, official reference, caller evidence in `dllhook.c`, wide-helper exact-match precedent, new ANSI exact-match helper, absence of the stale prefix-match loop, and ledger fragment; `docs/plan/check-srev-179.sh` is the matrix wrapper. Runtime/build gate: Windows DLL build plus `ApiSkipTrace` smoke proving exact entries still skip the named API, shorter configured prefixes do not skip longer API names, and ordinary API trace hook installation still works. |
