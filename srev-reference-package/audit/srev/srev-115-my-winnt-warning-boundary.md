# SREV-115 My WinNT Warning Boundary

## Data

Owner file:

```text
Sandboxie/core/drv/my_winnt.h
```

Reviewed nodes:

```text
my_winnt.h include guard
#pragma warning
C4267
private NT declarations
OBJECT_TYPE
OBJECT_HEADER
SYSTEM_PROCESS_INFORMATION
SYSTEM_MODULE_INFORMATION
ZwQuerySystemInformation
```

## Schema

`MY_WINNT_WARNING_BOUNDARY` defines these local contracts:

- `my_winnt.h` is a driver-wide NT compatibility shim for declarations not
  supplied by every target WDK/DDK combination.
- Private NT structure declarations in this file are compatibility data shapes,
  not architecture truth by themselves.
- The header may suppress C4267 only for declarations inside the header.
- Any warning-state mutation introduced by the header is restored before the
  include guard closes.
- The C4267 suppression does not cross into includer code.
- This SREV must not change private NT structure layouts, function prototypes,
  access masks, object-manager structures, or system-information structures.

## Topology

```text
driver source
  -> driver.h / util.h
  -> my_winnt.h
      -> include ntifs.h
      -> include alpc.h
      -> push compiler warning state
      -> suppress C4267 for compatibility declarations
      -> private NT declarations
      -> pop compiler warning state
  -> downstream driver code resumes original warning state
```

## Logic Risk

The previous header disabled MSVC warning C4267 without a matching restore. That
made a local compatibility decision leak into every later declaration and source
line in the including translation unit. C4267 is specifically about conversion
from `size_t` to a smaller type, which is exactly the sort of warning that can
catch 64-bit truncation mistakes in NT boundary code.

The rest of this header is mostly private NT shape. Rewriting these declarations
from memory or from average internet snippets would be worse than leaving them
alone. The correct source-level move here is to contain the compiler-warning
mutation and record that private layout validation remains a Windows/WDK/runtime
matrix problem.

## Official Shape

- https://learn.microsoft.com/en-us/cpp/preprocessor/warning?view=msvc-170
- https://learn.microsoft.com/en-us/cpp/error-messages/compiler-warnings/compiler-warning-level-3-c4267?view=msvc-170

## Fix

The header now wraps the C4267 suppression with `#pragma warning(push)` and
`#pragma warning(pop)`. No NT declarations, prototypes, access masks, structure
layouts, include order, or consumers were changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-115.py
bash docs/plan/check-srev-115.sh
```

Runtime/build gate still required:

- Windows WDK build with normal warning level to prove no includer warning state
  is accidentally suppressed after `my_winnt.h`.
- Driver compile matrix for supported x86/x64/ARM64 targets.
- Runtime smoke for code that consumes `SYSTEM_PROCESS_INFORMATION`,
  `SYSTEM_MODULE_INFORMATION`, object-manager structures, and ALPC declarations.
- Driver Verifier / HVCI matrix where supported.
