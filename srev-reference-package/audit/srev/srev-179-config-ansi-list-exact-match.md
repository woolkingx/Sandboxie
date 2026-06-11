# SREV-179: Config ANSI List Exact Match

## Stage Gate

| Field | Value |
|---|---|
| Stage | action |
| Input artifact | `Sandboxie/core/dll/config.c`, `Sandboxie/core/dll/dllhook.c`, Microsoft CRT string-comparison reference |
| Output artifact | `docs/plan/srev-179-config-ansi-list-exact-match.schema.json`, `docs/plan/check-srev-179.py`, `docs/plan/check-srev-179.sh`, ledger row |
| Owner | `SbieDll_CheckStringInListA` config-list membership helper |
| Acceptance gate | source checker plus full SREV/KPATH/core coverage matrix; Windows API trace config smoke remains required |

## Evidence

`Sandboxie/core/dll/config.c` was the highest-ranked unnamed reviewable core
file after SREV-178. It owns DLL-side config query helpers and list membership
helpers over `SbieApi_QueryConfAsIs`.

`SbieDll_CheckStringInList` compares a wide caller string to each wide config
entry with `_wcsicmp(buf, string) == 0`, so the wide helper is exact-list
membership. `SbieDll_CheckStringInListA` is used by `dllhook.c` for
`ApiSkipTrace` API names, but before this SREV it hand-compared a `char*`
caller string against a wide config entry and returned true when only the wide
config entry reached `L'\0'`. That made `ApiSkipTrace=Abc` match API name
`Abcd`, because the helper did not also require the ANSI caller string to reach
`'\0'`.

Microsoft documents CRT string comparison as comparing null-terminated strings
and returning zero only when the strings are identical. The local helper should
therefore preserve exact membership, not prefix membership.

Official references:

- https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/strcmp-wcscmp-mbscmp?view=msvc-170

## Data

`SbieDll_CheckStringInListA`, `SbieDll_CheckStringInList`,
`SbieApi_QueryConfAsIs`, `buf[66]`, `string`, `boxname`, `setting`,
`ApiSkipTrace`, `dllhook.c`, and API trace hook names.

## Schema

`CONFIG_ANSI_LIST_EXACT_MATCH` says:

- `SbieDll_CheckStringInListA` owns ANSI caller-string membership checks against
  wide config-list entries.
- A match is legal only when every compared byte/character is equal and both
  strings reach their terminator at the same position.
- A shorter wide config entry is not a match for a longer ANSI caller string.
- A shorter ANSI caller string is not a match for a longer wide config entry.
- The helper preserves the existing case-sensitive comparison behavior.
- The helper preserves `SbieApi_QueryConfAsIs` iteration and
  `STATUS_BUFFER_TOO_SMALL` skip behavior.
- This SREV does not change wide `SbieDll_CheckStringInList`, config query
  flags, trace hook installation, or the meaning of `ApiSkipTrace` entries.

## Topology

Legal flow:

```text
dllhook API name char*
  -> SbieDll_CheckStringInListA(name, NULL, "ApiSkipTrace")
  -> SbieApi_QueryConfAsIs wide config entry
  -> Config_IsEqualAnsiString(buf, name)
  -> both strings must terminate together
  -> exact membership decision
```

## Logic Risk

The old helper turned a list of exact API names into a prefix list whenever the
configured value was shorter than the API name. For trace policy, that can skip
instrumentation for unintended APIs whose names share a prefix with a configured
entry. The owner-local fix is to make the ANSI helper match the exact membership
shape already used by the wide helper, without changing config query behavior or
case sensitivity.

## Fix

`Config_IsEqualAnsiString` now performs the mixed wide/ANSI comparison and
returns true only when both sides reach their terminator together.
`SbieDll_CheckStringInListA` uses that helper instead of returning true when
only the wide config entry ended.

## Acceptance Gate

`docs/plan/check-srev-179.py` validates the draft-07 schema, official
reference, caller evidence in `dllhook.c`, wide-helper exact-match precedent,
new ANSI exact-match helper, absence of the stale prefix-match loop, and ledger
entry. `docs/plan/check-srev-179.sh` is the matrix wrapper.

Runtime/build gate: Windows DLL build plus `ApiSkipTrace` smoke proving exact
entries still skip the named API, shorter configured prefixes do not skip longer
API names, and ordinary API trace hook installation still works.
