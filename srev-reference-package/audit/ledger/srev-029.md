---
kind: srev-ledger-entry
id: SREV-029
title: Crypt DPAPI Broker Wire Schema
status: patched-source-level-after-official-dpapi-data-blob-and-local-com-wire-analysis-
owner: Sandboxie/core/dll/crypt.c
spec: docs/plan/srev-029-crypt-wire-schema.md
schema: docs/plan/srev-029-crypt-wire.schema.json
checker: docs/plan/check-srev-029.py
runtime_gate: force DPAPI fallback and test normal, empty, entropy, empty-description, non-empty-description, and oversized boundary inputs
---
### SREV-029: Crypt DPAPI Broker Wire Schema

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official DPAPI/DATA_BLOB and local COM wire analysis; needs Windows DPAPI fallback runtime proof |
| Evidence | `Sandboxie/core/dll/crypt.c` built `COM_CRYPT_PROTECT_DATA_REQ` with unchecked `ULONG` arithmetic over `DATA_BLOB.cbData`, entropy, and description length, then trusted `COM_CRYPT_PROTECT_DATA_RPL` `data_len` / `descr_len` before copying. `Sandboxie/core/svc/comserver2.cpp` parsed request segments with `offset + length` checks and built reply lengths with unchecked addition. |
| Data | DPAPI `DATA_BLOB` bytes, optional entropy bytes, optional description WCHAR string, and `COM_CRYPT_PROTECT_DATA_REQ/RPL` flexible payloads. |
| Schema | `DATA_BLOB.cbData` is a byte count. The local COM request/reply payload starts at `FIELD_OFFSET(..., data)`, segment lengths must fit inside `h.length`, WCHAR descriptions include a NUL terminator on the wire, and `LocalAlloc` output ownership must match DPAPI's `LocalFree` contract. |
| Topology | Hooked DLL falls back from Crypt32 DPAPI into SbieSvc COM proxy; SbieSvc calls host `CryptProtectData` / `CryptUnprotectData`, then returns protected/unprotected bytes and optional description to the DLL. |
| Logic Risk | Large or malformed caller lengths can wrap temp-buffer allocation before copy; malformed service replies can make the DLL read past returned payload; service-side `offset + length` checks can wrap before rejecting malformed map-buffer data. |
| Official Shape | `docs/plan/srev-029-crypt-wire-schema.md` records Microsoft `CryptProtectData`, `CryptUnprotectData`, `DATA_BLOB`, and `LocalAlloc` contracts. `docs/plan/srev-029-crypt-wire.schema.json` records the small machine-readable wire schema for `COM_CRYPT_PROTECT_DATA`. |
| Fix | DLL request construction now uses `Crypt_AddUlong`, `Crypt_WcharsToBytesWithNull`, and `Crypt_GetBlobLength`; reply handling validates `h.length` through `Crypt_ValidateReply` before `LocalAlloc`/copy. Service parsing uses remaining-length checks and builds replies with `CryptAddUlong` / `CryptWcharsToBytesWithNull` before writing into the COM map buffer. |
| Acceptance Gate | `docs/plan/check-srev-029.py` validates the small schema and source patterns; `docs/plan/check-srev-029.sh` is only a compatibility wrapper for the existing shell matrix. Windows gate: force DPAPI fallback and test normal, empty, entropy, empty-description, non-empty-description, and oversized boundary inputs. |
