# SREV-104: Token SID Storage Copy Boundary

## Data

`Sandboxie/core/drv/token.c` owns token restriction and token recreation for
sandboxed processes. The uncovered comment-risk lines were in
`Token_RestrictHelper1`, where Sandboxie temporarily rewrites the user SID in a
filtered token before calling `SeFilterToken` again:

```text
Token_RestrictHelper1
  -> Sbie_SepFilterToken_KernelMode(... LengthIncrease = 128 ...)
  -> locate UserAndGroups through Dyndata_Config.UserAndGroups_offset
  -> rewrite SidAndAttrsInToken->Sid or inline SID bytes
  -> Sbie_SeFilterToken_KernelMode(...)
  -> restore SidAndAttrsInToken->Sid when pointer substitution was used
  -> ObDereferenceObject(TempNewTokenObject)
```

The local storage classifier is `Token_IsSharedSid_W8`. It uses private token
offsets to decide whether the user SID pointer is inline after the token's
`UserAndGroups` array or points elsewhere.

## Official Shape

Microsoft documents `SID` as a variable-length structure and says drivers must
not modify SID structure fields directly; support routines should be used.

Microsoft documents `RtlLengthSid` as returning the byte length only for a valid
SID. If the SID is invalid, the return value is undefined; callers should use
`RtlValidSid` first. Microsoft documents `RtlCopySid` as copying a SID to a
caller-allocated buffer and returning `STATUS_BUFFER_TOO_SMALL` when the
destination is too small.

Microsoft documents `SID_AND_ATTRIBUTES` as a SID pointer plus attributes.
`TOKEN_USER` identifies the token user through `SID_AND_ATTRIBUTES`, while
`TOKEN_GROUPS` contains group `SID_AND_ATTRIBUTES` entries. `TOKEN_USER` itself
is not passed to `SeFilterToken`; the user SID can be supplied as a group SID in
`TOKEN_GROUPS` when a deny-only SID is needed.

Microsoft documents `SeFilterToken` as creating a restricted token and says the
returned token must be released with `ObDereferenceObject`. It also documents
that `SidsToDisable` and `RestrictedSids` are `TOKEN_GROUPS` structures.

Microsoft documents `SeQueryInformationToken` as returning paged-pool buffers
for public token information such as `TokenUser` and `TokenGroups`. It does not
document the private `TOKEN.UserAndGroups` offset storage that Sandboxie uses in
this legacy helper path.

```text
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_sid
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlvalidsid
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtllengthsid
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-rtlcopysid
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_sid_and_attributes
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_token_user
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_token_groups
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-sefiltertoken
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-sequeryinformationtoken
```

## Schema

Local schema:

```text
docs/plan/srev-104-token-sid-storage-copy-boundary.schema.json
```

The token SID storage copy contract is:

```text
SID is variable-length and drivers must not modify SID structure fields directly
RtlValidSid must validate both the token SID and SandboxieLogonSid before RtlLengthSid
RtlLengthSid has undefined return value for invalid SIDs
RtlCopySid copies a SID into a caller-allocated buffer and returns STATUS_BUFFER_TOO_SMALL when the destination is too small
TOKEN_USER identifies the token user through SID_AND_ATTRIBUTES and TOKEN_USER itself is not a SeFilterToken input
TOKEN_GROUPS contains group SID_AND_ATTRIBUTES and can carry a user SID as deny-only input to SeFilterToken
SeFilterToken returns a referenced filtered token object that must later be dereferenced
Token_IsSharedSid_W8 is a private offset-based classifier and only decides whether inline copy is allowed
inline token SID rewrite must use RtlCopySid with the measured destination SID length
shared or too-small token SID storage must use pointer substitution and restore the original pointer before dereferencing the temporary token object
```

## Topology

Source topology after this SREV:

```text
TempNewTokenObject
  -> Dyndata_Config.UserAndGroups_offset
  -> SidAndAttrsInToken->Sid
  -> RtlValidSid(SidInToken)
  -> proc->SandboxieLogonSid defaulted to AnonymousLogonSid when configured
  -> RtlValidSid(proc->SandboxieLogonSid)
  -> RtlLengthSid on both validated SIDs
  -> Token_IsSharedSid_W8 or size comparison
       -> pointer substitution plus later restore
       -> otherwise RtlCopySid(TokenSidLength, SidInToken, SandboxieLogonSid)
```

The temporary token pointer-restore topology remains:

```text
OrigTokenSid = SidAndAttrsInToken->Sid
SidAndAttrsInToken->Sid = proc->SandboxieLogonSid
Sbie_SeFilterToken_KernelMode(...)
SidAndAttrsInToken->Sid = OrigTokenSid
ObDereferenceObject(TempNewTokenObject)
```

## Logic Risk

The old comment correctly identified two distinct data shapes but treated both
as an informal workaround: Windows 8.1 shared SID storage and too-small
system-process SID storage. The implementation also read `SidInToken[1]` and
called `RtlLengthSid` on both SIDs before proving both were valid.

That violates the official SID support-routine boundary. The correct local rule
is not "always copy" and not "always swap pointer"; it is:

```text
valid SID + inline storage + enough destination bytes -> RtlCopySid
valid SID + shared storage or insufficient bytes -> pointer substitution with restore
invalid SID shape -> fail this helper path
```

## Fix

Source-level behavior fix:

```text
Token_RestrictHelper1 now validates SidInToken with RtlValidSid before any length calculation.
It validates proc->SandboxieLogonSid before measuring or using it.
It measures both SID lengths once.
It keeps pointer substitution for Windows 8 shared SID storage and shorter destination storage.
It replaces raw memcpy for inline SID rewrite with RtlCopySid(TokenSidLength, SidInToken, proc->SandboxieLogonSid).
```

Preserved behavior:

```text
AnonymousLogon configuration still defaults proc->SandboxieLogonSid to AnonymousLogonSid.
Token_IsSharedSid_W8 remains the local private storage classifier.
OrigTokenSid restore before ObDereferenceObject is unchanged.
Sbie_SepFilterToken_KernelMode and Sbie_SeFilterToken_KernelMode call ordering is unchanged.
Restricted SID cleanup on NewTokenObject is unchanged.
```

## Acceptance Gate

`docs/plan/check-srev-104.py` validates the draft-07 schema, official reference
URLs, SID validation before length calculation, `RtlCopySid` replacing the old
inline `memcpy`, pointer substitution remaining only for shared or too-small
storage, original pointer restore, stale uncovered workaround wording removal,
and the ledger entry. `docs/plan/check-srev-104.sh` is the matrix wrapper.

Runtime gate: Windows token matrix covering Windows 7, Windows 8.1 before and
after KB2919355, Windows 10, a configured SbieLogin SID longer than the original
token SID, default AnonymousLogon, system-process token application,
`Token_IsSharedSid_W8` true/false observations, Driver Verifier, and token
object dereference/restore stability.
