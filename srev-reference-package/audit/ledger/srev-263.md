---
kind: srev-ledger-entry
id: SREV-263
title: DNS Filter Final Fence Owner
status: patched-source-topology-after-srev-050-buffer-owner-review-no-layout-change
owner: Sandboxie/core/dll/dns_filter.c
spec: docs/plan/srev-263-dns-filter-final-fence-owner.md
schema: docs/plan/srev-263-dns-filter-final-fence-owner.schema.json
checker: docs/plan/check-srev-263.py
runtime_gate: Inherited from SREV-050
---

### SREV-263: DNS Filter Final Fence Owner

| Field | Content |
|---|---|
| Severity | [minor] |
| Status | patched source/topology after SREV-050 buffer owner review; no layout change |
| Evidence | SREV-050 already owns the release-mode buffer contract for `WSA_FillResponseStructure`: every packed segment write must pass `CHECK_BUFFER_SPACE(currentPtr, size, bufferEnd)` before the write, and `lpdwBufferLength` is the caller-provided byte capacity / required-size owner. The remaining source comment still said the final check was a lightweight failsafe for wrong size calculations, obscuring that the final check is diagnostic only after the segment gates. |
| Data | `WSA_FillResponseStructure`, caller `lpqsResults`, caller `lpdwBufferLength`, `bufferEnd`, `CHECK_BUFFER_SPACE`, packed `WSAQUERYSETW`, `CSADDR_INFO`, `SOCKADDR`, `BLOB`, `HOSTENT`, and SREV-050. |
| Schema | `DNS_FILTER_FINAL_FENCE_OWNER` says SREV-050 owns the response buffer capacity contract; `CHECK_BUFFER_SPACE` gates each release-mode segment write against `bufferEnd`; the final end check is diagnostic only and uses the same `bufferEnd` owner; this SREV does not change response layout, required-size calculation, `WSAEFAULT` behavior, HOSTENT relative-offset encoding, or DNS filter policy. |
| Topology | `lpdwBufferLength input capacity -> bufferEnd -> per-segment CHECK_BUFFER_SPACE before writes -> final diagnostic currentPtr <= bufferEnd fence`. |
| Logic Risk | Calling the final check a failsafe for wrong size calculations can invite the wrong repair: relying on an after-the-fact fence instead of preserving the pre-write segment gates. The correct owner is SREV-050's `bufferEnd` contract; the final check is only a diagnostic consistency fence. |
| Official Shape | Microsoft documents `WSALookupServiceNextW` as receiving `lpdwBufferLength` with the number of bytes in `lpqsResults` on input and the required size on `WSAEFAULT`. Microsoft documents `WSAQUERYSETW` result pointer fields including `lpcsaBuffer` and `lpBlob`, and `BLOB` as Winsock binary block storage. |
| Fix | The source comment now names SREV-050 as the final diagnostic fence owner and states that segment-level `CHECK_BUFFER_SPACE` gates are the release-mode overflow boundary. The final check now compares `currentPtr` to the already computed `bufferEnd`, keeping the capacity owner single-sourced. No layout or runtime policy changed. |
| Acceptance Gate | `docs/plan/check-srev-263.py` validates the draft-07 schema, official references, source comment, final `bufferEnd` fence, unchanged release-mode segment gates, SREV-050 adjacency, and the ledger fragment; `docs/plan/check-srev-263.sh` is the targeted wrapper. Runtime gate is inherited from SREV-050. |
