---
kind: srev-ledger-entry
id: SREV-319
title: Winsock Socket WFP Prompt Boundary
status: comment-classified-after-official-wsasocketw-wfp-topology-review-no-behavior-change
owner: Sandboxie/core/dll/net.c
spec: docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.md
schema: docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.schema.json
checker: docs/plan/check-srev-319.py
runtime_gate: Windows WFP-enabled socket creation, denied traffic block, prompt/manual-bypass path-list refresh, and no repeated prompt after allowed bypass
---
### SREV-319: Winsock Socket WFP Prompt Boundary

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | comment classified after official `WSASocketW` and WFP topology review; no source behavior change |
| Evidence | `Sandboxie/core/dll/net.c` hooks `WSASocketW`. When `WSA_WFPisBlocking` is true, it queries `PromptForInternetAccess`, calls `SbieApi_CheckInternetAccess(0, NULL, !prompt)`, optionally calls `File_InternetBlockade_ManualBypass()`, and then still calls `__sys_WSASocketW(...)`. The old comment explained this as always allowing socket creation to avoid process crashes or unexpected behavior. |
| Data | `WSASocketW` input tuple, `WSA_WFPisEnabled`, `WSA_WFPisBlocking`, `AllowNetworkAccess`, `PromptForInternetAccess`, `SbieApi_CheckInternetAccess`, `File_InternetBlockade_ManualBypass`, driver path-list / WFP internet-access state, and provider-owned `SOCKET` result. |
| Schema | `WINSOCK_SOCKET_WFP_PROMPT_BOUNDARY` says `WSASocketW` creation result remains provider-owned; the prompt/manual-bypass path may refresh driver internet-access state before socket creation; `SbieApi_CheckInternetAccess` owns the driver state query; `File_InternetBlockade_ManualBypass` owns the interactive box-manager request; WFP driver filtering owns blocked-traffic enforcement after socket creation; this SREV changes comments and proof only. |
| Topology | Application `WSASocketW` call -> Sandboxie DLL prompt/manual-bypass policy refresh -> original provider `WSASocketW` -> driver WFP classify/filter enforcement on later traffic. SREV-190 owns the ABI shape; SREV-239 owns the driver WFP module topology; SREV-319 owns only this DLL-side socket-creation / WFP-enforcement boundary comment. |
| Logic Risk | The old compatibility wording mixed motivation with ownership. The relevant boundary is not "allow to avoid crash"; it is "provider owns socket creation, driver WFP owns later traffic enforcement." Keeping that topology explicit prevents future changes from returning local `WSASocketW` failures for a policy state that belongs to the driver traffic path. |
| Official Shape | `docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.md` records Microsoft `WSASocketW` and WFP references. `docs/plan/srev-319-winsock-socket-wfp-prompt-boundary.schema.json` records the JSON Schema draft-07 local `WINSOCK_SOCKET_WFP_PROMPT_BOUNDARY` contract. |
| Fix | The source comment now states that socket creation remains provider-owned, prompt/manual-bypass only updates driver internet-access state, and the WFP driver enforces blocked traffic after the socket exists. No socket creation, prompt, bypass, provider-call, or driver enforcement behavior changed. |
| Acceptance Gate | `docs/plan/check-srev-319.py` validates the draft-07 schema, official references, `WSA_WSASocketW` prompt/manual-bypass topology, provider call preservation, stale compatibility wording removal, local `SbieApi`/manual-bypass evidence, SREV-190 ABI adjacency, SREV-239 WFP topology adjacency, and split ledger fragment; `docs/plan/check-srev-319.sh` is the targeted wrapper. Windows gate: WFP-enabled socket creation, denied traffic block, prompt/manual-bypass path-list refresh, and no repeated prompt after allowed bypass. |
