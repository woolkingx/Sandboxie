---
kind: srev-ledger-entry
id: SREV-223
title: IsHostPath Final Path Length Gate
status: patched-source-level-after-official-getfinalpathnamebyhandlew-length-review-needs-windows-breakout-runtime-proof
owner: Sandboxie/core/svc/main.cpp
spec: docs/plan/srev-223-is-host-path-final-length.md
schema: docs/plan/srev-223-is-host-path-final-length.schema.json
checker: docs/plan/check-srev-223.py
runtime_gate: "Windows service build plus BreakoutProcess host-local, sandbox-root, network-share, and too-small-buffer final-path smokes"
---
### SREV-223: IsHostPath Final Path Length Gate

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source-level after official `GetFinalPathNameByHandleW` length-shape review; needs Windows breakout runtime proof |
| Evidence | `Sandboxie/core/svc/misc.h` was the top unnamed reviewable core file after SREV-222. It declares service-wide helpers whose implementations live in `Sandboxie/core/svc/main.cpp`. `IsHostPath` is used by `ProcessServer.cpp` to decide whether a `BreakoutProcess` target is outside the caller's sandbox root. Before this SREV, `IsHostPath` called `GetFinalPathNameByHandleW` with a fixed `len = 8192` buffer capacity, then tested `if(len > 12 && _wcsnicmp(request_path, L"\\Device\\Mup\\", 12) == 0)` and later computed `request_path_len = wcslen(request_path)`. The MUP/network-share gate therefore used scratch-buffer capacity, not the API-returned path length; the too-small-buffer check also used `dwRet > len` rather than rejecting `dwRet >= len`. |
| Data | `misc.h`, `main.cpp`, `IsHostPath`, `ProcessServer.cpp` breakout process gate, `CreateFileW`, `GetFinalPathNameByHandleW`, `VOLUME_NAME_NT`, `\Device\Mup\`, `SbieApi_QueryProcessPath`, `request_path`, `sandbox_path`, `dwRet`, and `len`. |
| Schema | `IS_HOST_PATH_FINAL_LENGTH_GATE` says `misc.h` declares service-wide helpers while `main.cpp` owns their implementations; `IsHostPath` compares a requested host path against the caller sandbox root before allowing a `BreakoutProcess`; `GetFinalPathNameByHandleW` returns the final path length on success and a required buffer size when the supplied buffer is too small; a successful final-path read requires a nonzero return smaller than the caller-supplied character capacity; prefix tests and later length comparisons use the returned final-path length, not the scratch-buffer capacity; `VOLUME_NAME_NT` paths beginning with `\Device\Mup\` remain network-share paths and are not host paths for this breakout gate. |
| Topology | `ProcessServer` parses a breakout candidate, then calls `IsHostPath(caller pid, lpApplicationName)`. `IsHostPath` opens the candidate path, asks Windows for its final NT path, rejects MUP/network-share paths, queries the caller's sandbox root through `SbieApi_QueryProcessPath`, and allows breakout only when the final path is not under that sandbox root. |
| Logic Risk | The local scratch-buffer capacity is not the semantic length of the returned final path. Using it for the MUP gate hid the actual data owner and could make future prefix changes reason over capacity instead of returned bytes. Accepting `dwRet == len` also treats an exact-capacity return as success even though the documented return shape uses the caller's buffer capacity to distinguish success from required-size responses. |
| Official Shape | `docs/plan/srev-223-is-host-path-final-length.md` records Microsoft `GetFinalPathNameByHandleW` and `CreateFileW` references. `docs/plan/srev-223-is-host-path-final-length.schema.json` records the JSON Schema draft-07 local `IS_HOST_PATH_FINAL_LENGTH_GATE` contract. |
| Fix | `IsHostPath` now rejects `dwRet == 0 || dwRet >= len`, computes `MupPrefixLen` from the local prefix literal, gates the network-share prefix check with `dwRet >= MupPrefixLen`, and uses `dwRet` as `request_path_len`. No breakout allowlist semantics, sandbox-root query semantics, path-open flags, network-share rejection policy, or sandbox-root prefix comparison policy changed. |
| Acceptance Gate | `docs/plan/check-srev-223.py` validates the draft-07 schema, official references, `misc.h` declaration surface, `IsHostPath` source shape, returned-length MUP gate, returned-length request comparison, stale fixed-capacity MUP gate removal, and ledger entry; `docs/plan/check-srev-223.sh` is the targeted wrapper. Runtime/build gate: Windows service build for `main.cpp`; positive `BreakoutProcess` smoke for a host-local executable outside the sandbox root; negative smoke for a candidate inside the sandbox root; negative smoke for a network-share path whose final NT path begins with `\Device\Mup\`; and boundary smoke for a too-small-buffer final-path response. |
