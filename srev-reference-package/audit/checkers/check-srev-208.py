#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-208 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-208 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-208-memmem-bounded-search-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-208 failed: schema is not draft-07")
if schema.get("id") != "MEMMEM_BOUNDED_SEARCH_CONTRACT":
    raise SystemExit("SREV-208 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/drv/util.h":
    raise SystemExit("SREV-208 failed: wrong owner")
if schema.get("implementation") != "Sandboxie/core/drv/util.c":
    raise SystemExit("SREV-208 failed: wrong implementation")

contracts = "\n".join(schema["contracts"])
for term in [
    "shared driver memmem helper contract",
    "Search and pattern pointers",
    "Zero-length search or pattern requests",
    "pattern larger than the search buffer",
    "memcmp may only run after the bounded search window",
]:
    require(contracts, term, "schema contract")

header = (ROOT / "Sandboxie/core/drv/util.h").read_text()
src = (ROOT / "Sandboxie/core/drv/util.c").read_text()
spec = (ROOT / "docs/plan/srev-208-memmem-bounded-search-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-208.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

require(header, "void *memmem(const void *pSearchBuf, size_t nBufSize, const void *pPattern, size_t nPatternSize);", "util.h memmem declaration")

fn = between(
    src,
    "void *memmem(const void *pSearchBuf,",
    "//---------------------------------------------------------------------------\n// MyIsTestSigning",
)

for term in [
    "UCHAR *pBuf = (UCHAR *)pSearchBuf;",
    "UCHAR *pEos;",
    "if ((! pBuf) || (! pPattern) || (! nBufSize) || (! nPatternSize))\n        return NULL;",
    "if (nPatternSize > nBufSize)\n        return NULL;",
    "pEos = pBuf + nBufSize - nPatternSize;",
    "while (pBuf <= pEos)",
    "if (*pBuf == *(UCHAR*)pPattern)",
    "if (memcmp(pBuf, pPattern, nPatternSize) == 0)",
]:
    require(fn, term, "memmem bounded search gate")

if not fn.index("if ((! pBuf)") < fn.index("if (nPatternSize > nBufSize)"):
    raise SystemExit("SREV-208 failed: null/zero gate is after size-order gate")
if not fn.index("if (nPatternSize > nBufSize)") < fn.index("pEos = pBuf + nBufSize - nPatternSize;"):
    raise SystemExit("SREV-208 failed: endpoint computed before size-order gate")
if not fn.index("pEos = pBuf + nBufSize - nPatternSize;") < fn.index("while (pBuf <= pEos)"):
    raise SystemExit("SREV-208 failed: loop starts before endpoint calculation")
if not fn.index("while (pBuf <= pEos)") < fn.index("memcmp(pBuf, pPattern, nPatternSize)"):
    raise SystemExit("SREV-208 failed: memcmp runs before bounded loop")

reject(fn, "UCHAR *pEos = pBuf + nBufSize - nPatternSize;", "pre-gate endpoint calculation")
reject(fn, "if (!(pBuf && pEos && nBufSize && nPatternSize))", "stale combined gate")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-208",
    "owner: Sandboxie/core/drv/util.h",
    "implementation: Sandboxie/core/drv/util.c",
    "spec: docs/plan/srev-208-memmem-bounded-search-contract.md",
    "schema: docs/plan/srev-208-memmem-bounded-search-contract.schema.json",
    "checker: docs/plan/check-srev-208.py",
    "patched source-level after official buffer compare shape review",
]:
    require(ledger_fragment, term, "ledger fragment")
    require(ledger, term, "combined ledger")

print("SREV-208 source gate passed")
