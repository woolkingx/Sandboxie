---
kind: srev-ledger-entry
id: SREV-017
title: Breakout Command-Line Argument Copy Can Overflow Fixed Buffer
status: patched-source-level-after-official-command-line-and-local-breakout-parser-analy
owner: "Sandboxie/core/dll/proc.c:1274-1287"
spec: docs/plan/srev-017-breakout-command-line-spec.md
schema: docs/plan/srev-017-breakout-command-line-spec.schema.json
checker: docs/plan/check-srev-017.sh
runtime_gate: overlong quoted drive path is preserved without overflow, while ordinary breakout path remapping still works
---
### SREV-017: Breakout Command-Line Argument Copy Can Overflow Fixed Buffer

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official command-line and local breakout parser analysis; needs Windows runtime proof |
| Evidence | Explorer Ohm reports `Sandboxie/core/dll/proc.c:1274-1287` copies a parsed command-line argument into fixed `temp[8192]` with `wcscpy`. |
| Data | Sandboxed process command line split into breakout candidate arguments. |
| Schema | `CreateProcessW` command lines may be 32,767 Unicode characters including the terminator; argument parsing rules do not bound a single argument to 8192 WCHARs. Parser output length must be bounded before copying into the local scratch buffer. |
| Topology | Sandboxed process command line crosses into breakout request construction before service validation. |
| Logic Risk | Overlong drive-qualified argument can overflow local stack/buffer before broker policy sees it. |
| Official Shape | `docs/plan/srev-017-breakout-command-line-spec.md` records Microsoft `CreateProcessW`, `GetCommandLineW`, `CommandLineToArgvW`, and MSVC CRT argument parsing shape. |
| Fix | `Proc_CreateProcessInternalW` now only remaps drive-qualified arguments whose unquoted payload fits in the 8192-WCHAR scratch buffer. It copies with `wmemcpy(temp, tmp, tmp_len)`, writes the terminator at `tmp_len`, preserves oversized arguments without remapping, and falls back to the original argument tail if scratch allocation fails. |
| Acceptance Gate | `docs/plan/check-srev-017.sh` proves no raw `wcscpy(temp, tmp)` remains, the drive-qualified path check is length-gated, and the terminator uses the copied payload length. Windows gate: overlong quoted drive path is preserved without overflow, while ordinary breakout path remapping still works. |
