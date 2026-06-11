# SREV-188: Conf Expand Early Exit Pool Lifetime

## Data

Owner file:

```text
Sandboxie/core/drv/conf_expand.c
```

Reviewed nodes:

```text
Conf_Expand_2
Conf_Expand_Helper
Conf_Expand_Buffer
ExAllocatePoolWithTag
ExFreePoolWithTag
Mem_AllocString
Mem_FreeString
TooLong
Recursion
```

## Schema

`CONF_EXPAND_EARLY_EXIT_POOL_LIFETIME` defines these local contracts:

- `Conf_Expand_2` owns the per-expansion page buffer `Conf_Expand_Buffer`.
- `Conf_Expand_Buffer` is allocated with `ExAllocatePoolWithTag(PagedPool, PAGE_SIZE, tzuk)`.
- Every successful allocation of `Conf_Expand_Buffer` must reach `ExFreePoolWithTag(Conf_Expand_Buffer, tzuk)` before returning.
- Expansion strings allocated after `model_value` must be released with `Mem_FreeString` when the expansion fails.
- The too-long gate must fail closed without leaking `Conf_Expand_Buffer` or an allocated current expansion string.
- The recursion gate must fail closed without leaking `Conf_Expand_Buffer` or the newly allocated recursive expansion string.
- This SREV does not change expansion variable lookup, registry lookup, recursion limit, string length limit, or logging.
- Windows Driver Verifier or pool-tag runtime proof is required.

## Topology

The expansion lifetime route is:

```text
Conf_Expand_2
  -> ExAllocatePoolWithTag(PagedPool, PAGE_SIZE, tzuk)
  -> loop over Conf_Expand_Helper results
  -> on normal success: return allocated expanded string
  -> on too-long or recursion failure: free current allocated string if needed
  -> ExFreePoolWithTag(Conf_Expand_Buffer, tzuk)
  -> return final result or NULL
```

## Logic Risk

Before this SREV, the `TooLong` branch returned `NULL` directly after
`Conf_Expand_Buffer` had been allocated. The recursion-limit branch also
returned `NULL` directly after `Conf_Expand_Helper` had produced a new expansion
string and after `Conf_Expand_Buffer` had been allocated.

Both branches bypassed the common `ExFreePoolWithTag` release at the end of the
function. The recursion branch also leaked the newly allocated `new_value`
string because the old value had already been freed before the branch.

## Official Shape

Microsoft documents `ExAllocatePoolWithTag` as returning a pointer to allocated
pool memory and says the allocated buffer can be freed with `ExFreePool` or
`ExFreePoolWithTag`. Microsoft documents `ExFreePoolWithTag` as deallocating a
block allocated with the specified tag.

Sources:

- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exallocatepoolwithtag
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/nf-wdm-exfreepoolwithtag

## Fix

The `TooLong` and `Recursion` branches now release any current allocated
expansion string when it is not the caller-owned `model_value`, set `new_value`
to `NULL`, and break to the common `ExFreePoolWithTag` release path.

No expansion lookup order, recursion limit, string length limit, registry query
shape, or log message changed.

## Acceptance Gate

Source gate:

```bash
python3 docs/plan/check-srev-188.py
bash docs/plan/check-srev-188.sh
```

Runtime gate still required:

- Windows driver build for `conf_expand.c`.
- Driver Verifier or pool-tag observation for a too-long expansion string.
- Recursion-limit expansion smoke proving both the page buffer and current
  expansion string are released.
