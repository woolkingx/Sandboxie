# SREV-003 UAC App Name Shape

Status: source-level spec before patch.

## Official Shape

Microsoft documents `ShellExecuteW` as separate fields: `lpFile` names the file
or object being executed, while `lpParameters` carries parameters when `lpFile`
is an executable. The `runas` verb is the UAC/elevation shell verb.

Microsoft documents `CommandLineToArgvW` as the parser for a full Unicode
command line into argv-style arguments, and `PathFindFileNameW` as a helper for
extracting a filename from a path.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutew
- https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-commandlinetoargvw
- https://learn.microsoft.com/en-us/windows/win32/api/shlwapi/nf-shlwapi-pathfindfilenamew

## Local Shape

Sandboxie's UAC packet carries three independent WCHAR arrays:

- `app`: application identity, or the special `*MSI*` token
- `cmd`: full command line
- `dir`: working directory, or the special `*MSI*` token

`RunUacSlave4(..., OutAppName)` is used by `RunUacSlave2` only to get display
text for the Sandboxie elevation prompt before actual elevated execution.

## Local Risk

The previous display path returned `cmd` through `OutAppName`. The UI code then
tried to classify `*MSI*` from that value, but the code comment already notes
that the `*MSI*` token belongs to `app`, not to the returned command line.

The execution path also compared five WCHARs against `app`, `cmd`, and `dir`
without first proving each field length is exactly the five-WCHAR token shape.

## Patch Boundary

Keep execution behavior unchanged. Only fix the display/classification data
shape:

- `RunUacSlave4(..., OutAppName)` returns the `app` token only when `app` is
  exactly `*MSI*`; otherwise it preserves the previous command-line return.
- `RunUacSlave2` maps a returned `*MSI*` display token to `Windows Installer`.
- The execution MSI branch uses a length-aware token helper for `app`, `cmd`,
  and `dir` before treating the request as an MSI elevation token.

## Acceptance Gate

- No inline `bug bug` comment remains in the UAC display path.
- MSI token checks require exact five-WCHAR shape before comparison.
- The command-line display path remains the default for non-MSI UAC requests.
- Runtime gate remains open: MSI elevation prompt displays `Windows Installer`;
  normal executable elevation still displays the executable/command identity.
