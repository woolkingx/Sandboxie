# SREV-013 Relative Symlink Canonicalizer Shape

Status: source-level spec before patch.

## Official Shape

The MS-FSCC symbolic-link reparse data buffer says a symlink substitute name can
be a full path or a path relative to the directory containing the symbolic link.
It also states that either symlink pathname can contain dot directory names.

Implication: Sandboxie must treat a relative symlink substitute name as a
length-bounded buffer supplied by `SubstituteNameLength`, not as a
NUL-terminated string. Dot-segment handling is local Sandboxie logic and must
not read beyond that declared length.

Source:

- https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/b41f1cbf-10df-4a47-98d4-1c52a833d913

## Local Risk

`File_CanonizePath` used unsigned indexes and conditions like `j >= 0`.
It also inspected `relative_path[i + 1]` and `relative_path[i + 2]` while only
checking `i < rel_path_len`. A one-character relative path or excessive `..`
segments can therefore read outside the declared input or underflow the
absolute-path cursor.

## Acceptance Gate

- Dot-segment detection must use explicit `i + n < rel_path_len` bounds.
- Parent traversal must stop at a computed root floor and fail if `..` would
  climb above it.
- `File_SetReparsePoint` must fail closed when relative symlink canonicalization
  cannot produce an absolute path.
