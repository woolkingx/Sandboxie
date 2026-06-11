# SREV-017 Breakout Command-Line Argument Shape

Status: source-level spec before patch.

## Official Shape

Microsoft documents `CreateProcessW` as accepting a mutable Unicode command-line
buffer. The command line may be as long as 32,767 characters, including the
terminating null character. If `lpApplicationName` is present, `lpCommandLine`
is still the full command line that the new process can later retrieve with
`GetCommandLineW`.

Microsoft's `CommandLineToArgvW` and MSVC CRT argument rules define argument
splitting around whitespace, double quotes, and backslashes, but they do not
bound an individual argument to 8192 characters.

Sources:

- https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw
- https://learn.microsoft.com/en-us/windows/win32/api/processenv/nf-processenv-getcommandlinew
- https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-commandlinetoargvw
- https://learn.microsoft.com/en-us/cpp/c-language/parsing-c-command-line-arguments?view=msvc-170

## Local Shape

`Proc_CreateProcessInternalW` builds a clean breakout command line for configured
`BreakoutProcess` / `BreakoutFolder` launches. It preserves the original
argument delimiters, but for drive-qualified arguments it may open the path and
replace a sandbox-copy path with its host path before sending the request to
`SbieDll_RunSandboxed`.

The temporary path buffer is also the output buffer for `SbieDll_GetHandlePath`,
whose contract is an 8192-WCHAR path buffer.

## Local Risk

The previous implementation copied a parsed argument into the fixed 8192-WCHAR
temporary buffer with `wcscpy(temp, tmp)`. A legal command line can carry a
single drive-qualified argument longer than that buffer, so breakout command-line
construction can overflow before the service-side validation boundary sees the
request.

The quoted-argument branch also wrote `temp[len - 2] = L'\0'`, which ties the
terminator index to the original token length rather than the copied payload
length.

## Patch Boundary

Keep the existing local parser and service validation boundary. Do not broaden
breakout policy and do not rewrite argument quoting semantics.

Only drive-qualified arguments whose unquoted payload fits in the 8192-WCHAR
scratch buffer are eligible for path remapping. Oversized or malformed parsed
arguments are preserved in the rebuilt command line without remapping.

If scratch allocation fails, preserve the original argument tail.

## Acceptance Gate

- No raw `wcscpy(temp, tmp)` remains in the breakout argument adaptation path.
- The drive-qualified check proves the candidate payload has at least two WCHARs.
- The copy into `temp` is bounded by the 8192-WCHAR scratch capacity.
- The terminator is written at the copied payload length, not at `len - 2`.
- Runtime gate remains open: overlong quoted drive-path argument should be
  preserved without overflow, and ordinary breakout path remapping should still
  work on Windows.
