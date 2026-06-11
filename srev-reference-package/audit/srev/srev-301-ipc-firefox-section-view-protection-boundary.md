# SREV-301: IPC Firefox Section View Protection Boundary

## Stage Gate

| Field | Value |
|---|---|
| Stage | data -> schema -> topology -> logic -> verify |
| Input artifact | `Sandboxie/core/dll/ipc.c`, Microsoft `ZwMapViewOfSection` and `ZwQuerySection` documentation, SREV-283 |
| Output artifact | Firefox non-image section view protection contract, draft-07 schema, targeted checker, ledger fragment |
| Owner | `Ipc_NtMapViewOfSection` |
| Acceptance gate | Targeted checker validates source comment ownership, non-image section predicate, unchanged protection rewrite, official references, SREV-283 adjacency, stale symptom wording removal, and ledger fragment |

## Data

`Ipc_NtMapViewOfSection` wraps `NtMapViewOfSection`. For Firefox 146+ it has a
child-process branch:

```text
Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX
  -> ProcessHandle is not the current-process pseudo handle
  -> Protect == PAGE_EXECUTE_READ
  -> NtQuerySection(SectionBasicInformation)
  -> non-image section
  -> map with PAGE_EXECUTE_READWRITE
```

The old source comment said this was a thunk allocation and that a later
`NtProtectVirtualMemory` call would produce `STATUS_SECTION_PROTECTION`. It did
not name the section-protection owner, the Firefox version/runtime matrix, or
the adjacent write-suppression owner recorded by SREV-283.

## Official Shape

Microsoft documents `ZwMapViewOfSection` as mapping a section view into the
subject process. For non-image sections, the `Win32Protect` value controls the
initial protection for committed pages and must be compatible with the section's
page protection. An incompatible protection returns `STATUS_SECTION_PROTECTION`.

Microsoft documents `ZwQuerySection` as returning information about a section
object. The local source uses `SectionBasicInformation` and reads
`AllocationAttributes & SEC_IMAGE` to distinguish image sections from non-image
sections before changing the requested view protection.

Official references:

- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwmapviewofsection`
- `https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-zwquerysection`
- `https://learn.microsoft.com/en-us/windows/win32/memory/memory-protection-constants`

## Schema

Local schema:

```text
docs/plan/srev-301-ipc-firefox-section-view-protection-boundary.schema.json
```

Contract id:

```text
IPC_FIREFOX_SECTION_VIEW_PROTECTION_BOUNDARY
```

## Topology

```text
Firefox remote map request
  -> Ipc_NtMapViewOfSection
  -> NtQuerySection SectionBasicInformation
  -> SEC_IMAGE exclusion
  -> non-image execute view protection policy
  -> __sys_NtMapViewOfSection
```

SREV-301 owns only the comment-level source classification for this local
policy branch. SREV-283 owns the adjacent Firefox/Thunderbird
`WriteProcessMemory` suppression for `NtMapViewOfSection` and
`NtSetInformationThread` export-address targets. SREV-119 owns checked
`NtProtectVirtualMemory` write gates in low-level bootstrap patching.

## Logic Risk

The previous wording described the symptom but not the legal boundary. Without
the API shape, a future patch could treat the branch as a generic Firefox
permission escalation, or remove it as a stale local trick, instead of testing
the real section-protection matrix:

```text
section creation protection
  -> requested view protection
  -> later child-side local patch write
  -> STATUS_SECTION_PROTECTION behavior
```

Because `Ipc_NtMapViewOfSection` does not own the section creation call or the
Firefox child-side writer, this SREV does not narrow the predicate or change the
protection value. That requires Windows runtime evidence naming the Firefox
version, section creation protection, and child-side write path.

## Fix

The source comment now names SREV-301, the Firefox 146+ remote non-image section
boundary, the child-side local patch-byte intent, and the Windows
section-protection runtime matrix. It removes symptom-only `bug out` wording and
the disabled `BAM` monitor line.

No behavior changed: the Firefox image-type check, remote-process check,
`PAGE_EXECUTE_READ` predicate, `NtQuerySection` call, `SEC_IMAGE` exclusion,
`PAGE_EXECUTE_READWRITE` rewrite, and real `__sys_NtMapViewOfSection` call are
unchanged. This is a comment-only source clarification, no behavior change.

## Acceptance Gate

`docs/plan/check-srev-301.py` validates the draft-07 schema, official
references, source comment owner, unchanged Firefox/non-image predicate,
unchanged `PAGE_EXECUTE_READWRITE` rewrite, SREV-283 adjacency, stale wording
removal, combined ledger entry, and split ledger fragment.

Runtime gate: Windows Firefox 146+ smoke that captures the section creation
protection, `NtMapViewOfSection` requested protection before/after the wrapper,
child-side local patch-byte write, later `NtProtectVirtualMemory` behavior, and
negative proof that image sections and non-Firefox callers still use the native
protection unchanged.
