# SREV-077: FormatMessage Insert Array Gate

## Data

`Sandboxie/core/dll/support.c` has a right-to-left language compatibility pass
in `SbieDll_FormatMessage_2`. It converts `.2.`, `.3.`, and `.4.` markers in
an already-loaded message string into `FormatMessage` insert markers and runs a
second formatting pass.

The relevant data nodes are:

```text
original LocalAlloc/FormatMessage output text
optional insert array
.2. / .3. / .4. marker scan
temporary rewritten message text
second FormatMessage pass
replacement output buffer
old/new LocalFree ownership
```

## Official Shape

Microsoft documents `FormatMessageW` with `FORMAT_MESSAGE_ARGUMENT_ARRAY` as
receiving an array of values in the `Arguments` parameter. Each insert sequence
must have a corresponding argument element. With `FORMAT_MESSAGE_ALLOCATE_BUFFER`,
the output buffer is allocated for the caller and must be freed with
`LocalFree`.

```text
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-formatmessagew
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-localfree
```

## Schema

Local schema:

```text
docs/plan/srev-077-format-message-insert-gate.schema.json
```

The compatibility contract is:

```text
the second FormatMessage pass may run only when an insert array exists
NULL insert array means there is no legal owner for %2/%3/%4 replacement values
markers inside insert strings are rejected before rewriting the message
successful replacement transfers output ownership and frees the old buffer
failed replacement preserves the original formatted output
```

## Topology

```text
SbieDll_FormatMessage -> first FormatMessage output -> optional .N. rewrite
optional .N. rewrite -> second FormatMessage with insert array -> replacement output
```

`SbieDll_FormatMessage_2` owns only the compatibility rewrite. It may consume
the insert array only after proving that the caller supplied one.

## Logic Risk

Before this patch, `SbieDll_FormatMessage_2` dereferenced `ins[1]` and `ins[2]`
after finding `.2.` in the message text. `SbieDll_FormatMessage0` calls the
same formatter with `ins == NULL`, so a translated message containing `.2.`
could crash in the compatibility workaround before the fallback text could be
returned.

## Fix

`SbieDll_FormatMessage_2` now returns `0` immediately when `ins` is NULL. The
original formatted output remains owned by the caller path, and the second
`FormatMessage` pass runs only when an insert array exists.

Later source-comment clarification: the function comment now names this as
SREV-077's RTL marker compatibility pass instead of a generic workaround. This
does not change behavior; it keeps the source comment aligned with the schema
gate that only permits the second `FormatMessage` pass after the insert-array
boundary is proven.

## Acceptance Gate

`docs/plan/check-srev-077.py` validates the draft-07 schema, official
`FormatMessageW` and `LocalFree` references, NULL insert-array gate before
`ins[1]` / `ins[2]`, unchanged marker-in-insert rejection, unchanged output
ownership transfer, and ledger entry.

Windows gate: localized message with `.2.` and NULL inserts returns the first
formatted string without crashing; localized message with valid inserts still
rewrites `.2.` / `.3.` / `.4.` and frees the replaced output correctly.
