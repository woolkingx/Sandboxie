# SREV-105: Verify Legacy Certificate Level Compatibility

## Data

`Sandboxie/core/drv/verify.c` owns parsing and validation of the local
`Certificate.dat` entitlement file. The file is a signed text contract: tags are
hashed, the signature is verified, then the parsed `TYPE`, `LEVEL`, `DATE`,
`DAYS`, `OPTIONS`, and lock fields are mapped into `Verify_CertInfo`.

The uncovered comment-risk lines were attached to the legacy `LARGE`, `MEDIUM`,
and `SMALL` level branches in the `eCertPersonal` / `eCertPatreon` scheme 1.1
parser. Those branches do not independently activate expired certificates. They
only map signed legacy level text to local type/level/expiration state before
the common expiration gate runs.

## Official Shape

Microsoft documents certificate validity as a time-window decision around
certificate `NotBefore` and `NotAfter` fields. `CertVerifyTimeValidity` returns
whether a reference time is before, inside, or after that certificate validity
window.

Microsoft documents kernel system time as a UTC value counted in 100-nanosecond
intervals and documents `RtlTimeFieldsToTime` / `RtlTimeToTimeFields` as the
conversion boundary between `TIME_FIELDS` and that time value.

Sandboxie does not parse an X.509 certificate chain in this path. It parses a
local signed text file, so the official certificate model is used only for the
validity-window shape. The local owner of the actual policy is
`KphValidateCertificate`.

```text
https://learn.microsoft.com/en-us/windows/win32/api/wincrypt/nf-wincrypt-certverifytimevalidity
https://learn.microsoft.com/en-us/windows/win32/api/wincrypt/ns-wincrypt-cert_info
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-kequerysystemtimeprecise
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtltimefieldstotime
https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-rtltimetotimefields
```

## Schema

Local schema:

```text
docs/plan/srev-105-verify-legacy-cert-level-compatibility.schema.json
```

The legacy level compatibility contract is:

```text
Certificate.dat is local signed text, not an X.509 chain
legacy LARGE/MEDIUM/SMALL levels are accepted for signed-text compatibility
LARGE gets an explicit two-year expiration, except the pre-2022 sentinel batch
MEDIUM falls through to the default one-year expiration gate
SMALL maps to Home subscription before the common expiration gate
expiration_date drives expired/expirers_in_sec for non-eternal certificates
non-subscription certificates are gated by outdated against BuildDate
subscription certificates are gated by expired against UtcTime
inactive certificates become STATUS_ACCOUNT_EXPIRED outside grace period
```

## Topology

Source topology after this SREV:

```text
Certificate.dat signed tags
  -> type / level / cert_date / days / options
  -> scheme 1.1 personal / patreon level aliases
       -> HUGE maps to eternal max level
       -> pre-2022 LARGE maps to Advanced1 with -2 sentinel
       -> LARGE maps to level plus explicit 2-year expiration
       -> MEDIUM maps to Standard2 and uses default 1-year expiration
       -> SMALL maps to Standard2 + Home and uses default subscription expiration
  -> option defaults from level
  -> common expiration_date fallback
  -> isSubscription
  -> expired / outdated / grace_period / active / STATUS_ACCOUNT_EXPIRED
```

## Logic Risk

The old TODO comments named calendar dates and suggested removing the legacy
branches after those dates. That would be a behavior change: previously signed
`Certificate.dat` text containing `LARGE`, `MEDIUM`, or `SMALL` would no longer
map through the same local type/level state before diagnostics and expiry logic.

The correct boundary is data-shaped: keep the signed text aliases, and let the
common expiration gate decide whether the resulting certificate is active. The
source comments now name that contract instead of presenting stale removal dates.

## Fix

Comment-only source clarification. The three stale TODO comments were replaced
with comments that describe the legacy compatibility alias and point to the
common expiration enforcement below.

No certificate parser branch, type/level mapping, option defaulting, expiration
calculation, grace-period handling, lock-refresh handling, or return status
behavior changed.

## Acceptance Gate

`docs/plan/check-srev-105.py` validates the draft-07 schema, official
references, legacy level branches, pre-2022 sentinel behavior, explicit LARGE
two-year interval, MEDIUM and SMALL default-expiration topology, subscription vs
non-subscription gate, stale TODO removal, and ledger entry.
`docs/plan/check-srev-105.sh` is the matrix wrapper.

Runtime gate: Windows build matrix with signed `Certificate.dat` samples for
`LARGE`, `MEDIUM`, `SMALL`, pre-2022 `LARGE`, `HUGE`, `STANDARD`,
subscription and non-subscription types, expired/non-expired dates,
grace-period boundaries, `BuildDate` outdated checks, and lock-refresh enabled
and disabled.
