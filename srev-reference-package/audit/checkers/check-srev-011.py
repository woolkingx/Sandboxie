#!/usr/bin/env python3
import json
import re
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-011 failed: {label} missing {needle!r}")


schema = json.loads((ROOT / "docs/plan/srev-011-named-pipe-lpc-reply-shape.schema.json").read_text())
if schema.get("id") != "NAMED_PIPE_LPC_CONNECT_REPLY_SHAPE":
    raise SystemExit("SREV-011 failed: schema missing NAMED_PIPE_LPC_CONNECT_REPLY_SHAPE")

src = (ROOT / "Sandboxie/core/dll/ipc.c").read_text()
spec = (ROOT / "docs/plan/srev-011-named-pipe-lpc-reply-shape.md").read_text()
ledger = read_combined_ledger(ROOT)

if re.search(r"^\s*info_len\s*=\s*info_len\s*;", src, re.M):
    raise SystemExit("SREV-011 failed: no-op info_len clamp remains")

for term in [
    "FIELD_OFFSET(NAMED_PIPE_LPC_CONNECT_RPL, info_data)",
    "rpl->h.length < rpl_info_offset",
    "rpl_info_len > rpl->h.length - rpl_info_offset",
    "if (copy_len > info_len)",
    "memcpy(ConnectionInfo, rpl->info_data, copy_len)",
]:
    require(src, term, "DLL source")

require(spec, "calling-internal-apis", "spec")

require(ledger, "### SREV-011: Named-Pipe LPC Connect Reply Copies Caller Length Instead Of Reply Length", "ledger")
require(ledger, "Sandboxie/core/dll/ipc.c", "ledger")

print("SREV-011 schema/source gate passed")
