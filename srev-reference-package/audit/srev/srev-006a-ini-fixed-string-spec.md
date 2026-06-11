# SREV-006A INI Broker Fixed String Shape

Status: source-level spec before patch.

## Official Shape

Microsoft documents CRT string manipulation routines as operating on
null-terminated narrow, wide, or multibyte strings. Character arrays that are not
terminated must be treated as buffers instead.

Sources:

- https://learn.microsoft.com/en-us/cpp/c-runtime-library/string-manipulation-crt?view=msvc-170

## Local Shape

The SbieIni broker accepts fixed inline `WCHAR[66]` fields in several wire
requests:

- `SBIE_INI_SETTING_REQ.password`
- `SBIE_INI_SETTING_REQ.section`
- `SBIE_INI_SETTING_REQ.setting`
- `SBIE_INI_TEMPLATE_REQ.password`
- `SBIE_INI_TEMPLATE_REQ.varname`
- `SBIE_INI_PASSWORD_REQ.old_password`
- `SBIE_INI_PASSWORD_REQ.new_password`

These fields cross from a broker message into C-string APIs and config/password
logic. Before such use, each field that is actually consumed by that request
path must contain a `L'\0'` inside its declared array.

Variable `value` tails must also prove the terminator byte is inside the broker
message before code reads `value[value_len]`.

## Local Risk

Several handlers checked the outer message size but did not prove the fixed
inline strings were terminated before using `wcslen`, `wcscpy`, `wcscmp`,
`_wcsicmp`, `_wcsnicmp`, `wcsrchr`, `wcsstr`, `IsCallerAuthorized`, or INI APIs.

`MSGID_SBIE_INI_GET_SETTING` and `MSGID_SBIE_INI_SET_DAT` did not use the normal
setting request shape gate before touching fixed fields.

## Patch Boundary

This patch covers only SbieIni fixed-string request fields. SCM service-name
requests are tracked separately as SREV-006B.

Keep the existing authorization and config-update behavior. Add local shape
gates before C-string use:

- setting mutations: `password`, `section`, `setting`, and terminated `value`
- get setting: `section` and `setting`
- set dat: `setting`, plus value bytes inside message
- template: `varname`, `password` only when it is used, and terminated `value`
- password: `old_password`; `new_password` only for set-password requests

## Acceptance Gate

- Shared fixed-string gate exists and scans bounded arrays for `L'\0'`.
- `CheckRequest` proves `password`, `section`, and `setting` are terminated
  before authorization or config APIs.
- `GetSetting` proves `section` and `setting` are terminated before
  `m_pSbieIni->GetValue`.
- `SetDatFile` proves `setting` is terminated before path parsing.
- `SetTemplate` proves `varname` and the used password field are terminated.
- `SetOrTestPassword` proves the used password fields are terminated.
- Variable `value` terminator checks prove the terminator lies inside the
  message, not just at `value[value_len]`.
- Runtime gate remains open: malformed broker messages with unterminated fields
  return invalid-parameter replies without entering INI/password/path logic.
