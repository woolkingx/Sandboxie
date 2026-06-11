#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-186 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-186 failed: {label} still contains {needle!r}")


def assert_before(text: str, label: str, earlier: str, later: str) -> None:
    e = text.find(earlier)
    l = text.find(later)
    if e < 0 or l < 0 or e > l:
        raise SystemExit(f"SREV-186 failed: {label}")


schema = json.loads(
    (ROOT / "docs/plan/srev-186-syscall-query-name-slot-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-186 failed: schema is not draft-07")
if schema.get("id") != "SYSCALL_QUERY_NAME_SLOT_BOUNDARY":
    raise SystemExit("SREV-186 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "PE export names are input strings",
    "ASCII strings terminated by a null byte",
    "Sandboxie owns the syscall query wire slot",
    "exactly 16 ULONG values or 64 bytes",
    "stored syscall names must be at most 63 bytes",
    "NTDLL Zw and WIN32U Nt enumeration",
    "query buffer size and pointer advancement",
    "hook-map conversion and name-based syscall lookup",
    "does not change syscall index extraction",
    "runtime proof is required",
]:
    require(contracts, term, "schema contracts")

syscall_h = (ROOT / "Sandboxie/core/drv/syscall.h").read_text()
syscall_c = (ROOT / "Sandboxie/core/drv/syscall.c").read_text()
syscall_win32_c = (ROOT / "Sandboxie/core/drv/syscall_win32.c").read_text()
syscall_util_c = (ROOT / "Sandboxie/core/drv/syscall_util.c").read_text()
spec = (ROOT / "docs/plan/srev-186-syscall-query-name-slot-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-186.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "#define SYSCALL_NAME_SLOT_ULONGS   16",
    "#define SYSCALL_NAME_SLOT_BYTES    (SYSCALL_NAME_SLOT_ULONGS * sizeof(ULONG))",
    "#define SYSCALL_NAME_MAX_CHARS     (SYSCALL_NAME_SLOT_BYTES - 1)",
    "#define SYSCALL_NAME_LOG_CHARS     (SYSCALL_NAME_SLOT_BYTES + 2)",
]:
    require(syscall_h, term, "syscall.h constants")

for term in [
    "(name_len < SYSCALL_NAME_MAX_CHARS) && name[name_len]",
    "WCHAR name_w[SYSCALL_NAME_LOG_CHARS];",
    "(i < SYSCALL_NAME_MAX_CHARS) && name_a[i]",
    "UCHAR callName[SYSCALL_NAME_SLOT_BYTES];",
    "if(callNameLen > SYSCALL_NAME_MAX_CHARS)",
    "(add_names ? SYSCALL_NAME_SLOT_BYTES : 0)",
    "((char*)ptr)[entry->name_len] = 0;",
    "ptr += SYSCALL_NAME_SLOT_ULONGS;",
]:
    require(syscall_c, term, "syscall.c source")

for term in [
    "(name_len < SYSCALL_NAME_MAX_CHARS) && name[name_len]",
    "(add_names ? SYSCALL_NAME_SLOT_BYTES : 0)",
    "((char*)ptr)[entry->name_len] = 0;",
    "ptr += SYSCALL_NAME_SLOT_ULONGS;",
]:
    require(syscall_win32_c, term, "syscall_win32.c source")

for term in [
    "WCHAR wname[SYSCALL_NAME_LOG_CHARS];",
    "min(name_len, SYSCALL_NAME_MAX_CHARS)",
]:
    require(syscall_util_c, term, "syscall_util.c source")

for text, label in [
    (syscall_c, "syscall.c"),
    (syscall_win32_c, "syscall_win32.c"),
]:
    reject(text, "(name_len < 64) && name[name_len]", label)
    reject(text, "(add_names ? 64 : 0)", label)
    reject(text, "ptr += 16; // 16 * sizeog(ULONG) = 64", label)
    assert_before(
        text,
        f"{label} copy before in-slot terminator",
        "memcpy(ptr, entry->name, entry->name_len);",
        "((char*)ptr)[entry->name_len] = 0;",
    )

for term in [
    "variable-length null-terminated ASCII",
    "16-`ULONG` query slot",
    "64 bytes",
    "63 bytes",
    "terminator write",
    "No syscall index extraction",
]:
    require(spec, term, "spec shape")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-186",
    "owner: Sandboxie/core/drv/syscall.h",
    "spec: docs/plan/srev-186-syscall-query-name-slot-boundary.md",
    "schema: docs/plan/srev-186-syscall-query-name-slot-boundary.schema.json",
    "checker: docs/plan/check-srev-186.py",
]:
    require(ledger_fragment, term, "ledger fragment header")

for term in [
    "### SREV-186: Syscall Query Name Slot Boundary",
    "SYSCALL_QUERY_NAME_SLOT_BOUNDARY",
    "Sandboxie/core/drv/syscall.h",
    "SYSCALL_NAME_MAX_CHARS",
    "Syscall_Api_Query",
    "Syscall_Api_Query32",
]:
    require(ledger, term, "combined ledger")

print("SREV-186 schema/source gate passed")
