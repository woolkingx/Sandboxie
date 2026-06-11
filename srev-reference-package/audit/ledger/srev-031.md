---
kind: srev-ledger-entry
id: SREV-031
title: Process Low Inject SID Validation
status: patched-source-level-after-official-sid-rtlvalidsid-rtllengthsid-rtlcopysid-anal
owner: "Sandboxie/core/drv/process_low.c:277-281"
spec: docs/plan/srev-031-process-low-sid.md
schema: docs/plan/srev-031-process-low-sid.schema.json
checker: docs/plan/check-srev-031.py
runtime_gate: valid per-box SID copies and token rewrite works; NULL SID keeps fallback; malformed SID fails before length/copy
---
### SREV-031: Process Low Inject SID Validation

| Field | Content |
|---|---|
| Severity | [major] |
| Status | patched source-level after official SID/RtlValidSid/RtlLengthSid/RtlCopySid analysis; needs Windows per-box SID runtime proof |
| Evidence | `Sandboxie/core/drv/process_low.c:277-281` probed `SECURITY_MAX_SID_SIZE`, then called `RtlLengthSid(pSID)` and copied that length into `proc->SandboxieLogonSid` with `memcpy` without first proving the SID was valid. |
| Data | Optional SbieSvc-provided per-box SID pointer passed through `API_INJECT_COMPLETE` and stored in persistent `PROCESS.SandboxieLogonSid`. |
| Schema | SID is variable-length; `RtlLengthSid` is defined only for valid SIDs; valid copied size must be `<= SECURITY_MAX_SID_SIZE`; destination storage is process-pool-owned `PSID`. |
| Topology | SbieSvc low-level injection completion crosses into driver process state; later token rewrite reads `proc->SandboxieLogonSid`. |
| Logic Risk | A malformed SID can make `RtlLengthSid` return an undefined length, driving incorrect allocation/copy and later token SID rewrite behavior. |
| Official Shape | `docs/plan/srev-031-process-low-sid.md` records Microsoft `RtlValidSid`, `RtlLengthSid`, `RtlCopySid`, and SID structure contracts. `docs/plan/srev-031-process-low-sid.schema.json` records the small local API/SID schema. |
| Fix | `Process_Low_Api_InjectComplete` now initializes status, validates `RtlValidSid` before `RtlLengthSid`, rejects `sid_length > SECURITY_MAX_SID_SIZE`, checks allocation, copies with `RtlCopySid`, frees/clears on copy failure, and types `PROCESS.SandboxieLogonSid` as `PSID`. |
| Acceptance Gate | `docs/plan/check-srev-031.py` validates the SID schema and source guard/copy order; `docs/plan/check-srev-031.sh` is the matrix wrapper. Windows gate: valid per-box SID copies and token rewrite works; NULL SID keeps fallback; malformed SID fails before length/copy. |
