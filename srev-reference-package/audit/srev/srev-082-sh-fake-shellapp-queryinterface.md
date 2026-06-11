# SREV-082: Shell FakeApp QueryInterface Vtable Boundary

## Data

`Sandboxie/core/dll/sh.c` synthesizes a shell automation object used by the
fake desktop / folder-view chain. The `FakeShellApp` object exposes an
`IShellDispatch2`-sized vtable and routes `ShellExecute`, `Open`, `Explore`,
`Windows`, and several dispatch stubs through that table.

The relevant data nodes are:

```text
FakeShellApp object
QueryInterface requested IID
supported IID set
39-entry IShellDispatch2 vtable
unsupported IShellDispatch3/4/5/6 requests
ppv output pointer
reference count
```

## Official Shape

Microsoft documents `IUnknown::QueryInterface` as returning `S_OK` plus an
AddRef'd interface pointer when the object supports an IID, `E_NOINTERFACE`
with `*ppvObject = nullptr` when it does not, and `E_POINTER` when the output
pointer itself is null. Microsoft's QueryInterface rules also require a static
interface set for a COM object instance.

Microsoft documents `IShellDispatch2` as an extension of `IShellDispatch`. The
fake object implements an `IShellDispatch2`-sized table; later dispatch
interfaces add members beyond that table and therefore are not legal contracts
for this object.

```text
https://learn.microsoft.com/en-us/windows/win32/api/unknwn/nf-unknwn-iunknown-queryinterface%28refiid_void%29
https://learn.microsoft.com/en-us/windows/win32/com/rules-for-implementing-queryinterface
https://learn.microsoft.com/en-us/windows/win32/shell/ishelldispatch2-object
```

## Schema

Local schema:

```text
docs/plan/srev-082-sh-fake-shellapp-queryinterface.schema.json
```

The fake-shell COM contract is:

```text
FakeShellApp may return self for IUnknown, IDispatch, IShellDispatch, and IShellDispatch2
successful QueryInterface increments the object refcount
unsupported interfaces must set *ppv to NULL and return E_NOINTERFACE
IShellDispatch3/4/5/6 must not be accepted by a 39-entry IShellDispatch2 vtable
null ppv returns E_POINTER
the supported interface set is static for the object
```

## Topology

```text
FakeFolderView / FakeDesktop
  -> FakeShellApp
  -> QueryInterface
  -> supported IID set
  -> vtable slot contract
```

`SH32_FakeApp_QI` owns the boundary between the public COM interface request
and the local synthetic vtable. The vtable itself is a code-owned executable
projection of the supported IID set.

## Logic Risk

The source comment names the interface contract directly: `SH32_FakeApp_QI`
must not accept `IShellDispatch3`, `IShellDispatch4`, `IShellDispatch5`, or
`IShellDispatch6` because those interfaces add vtable slots beyond the
39-entry `IShellDispatch2` table.

The current source already follows the correct shape: it accepts only the
interfaces backed by the table and rejects unsupported interfaces with
`*ppv = NULL` and `E_NOINTERFACE`.

## Fix

The current source-level shape is recorded and gated as the SREV-082 contract
so the comment-admitted risk is classified instead of remaining in the uncovered
queue. A later comment-only clarification replaced the stale risk wording with
explicit SREV-082 contract language; behavior stayed unchanged.

## Acceptance Gate

`docs/plan/check-srev-082.py` validates the draft-07 schema, official
references, accepted IID set, explicit unsupported-interface rejection,
`IShellDispatch2` 39-entry table, null-output handling, refcount increment on
success, and ledger entry.

Windows gate: scripting clients querying `IUnknown`, `IDispatch`,
`IShellDispatch`, or `IShellDispatch2` succeed; clients querying
`IShellDispatch3/4/5/6` receive `E_NOINTERFACE` with a null output pointer and
do not call beyond the fake vtable.
