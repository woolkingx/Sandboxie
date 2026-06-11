#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-097 failed: {label} missing {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-097-zw-redirector-hal7600-skip-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-097 failed: schema is not draft-07")
if schema.get("id") != "ZW_REDIRECTOR_HAL7600_SKIP_CONTRACT":
    raise SystemExit("SREV-097 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "scans kernel Zw redirector bytes only to locate an existing stub",
    "scanner skip over a known replacement stub",
    "32-bit HAL7600 pattern is 33 C0 C2 08 00",
    "64-bit HAL7600 pattern is 33 C0 C3",
    "must not treat the HAL7600 replacement stub as a legal Zw redirector",
    "must not patch kernel code from this scanner branch",
    "ordinary 32-bit Zw redirector parsing and fallback search remain unchanged",
    "ordinary 64-bit Zw redirector parsing remains unchanged",
]:
    require(contracts, term, "schema")

hook_c = (ROOT / "Sandboxie/core/drv/hook.c").read_text()
hook32 = (ROOT / "Sandboxie/core/drv/hook_32.c").read_text()
hook64 = (ROOT / "Sandboxie/core/drv/hook_64.c").read_text()
spec = (ROOT / "docs/plan/srev-097-zw-redirector-hal7600-skip-contract.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in [
    "svc_addr = Hook_GetNtServiceInternal(svc_num, ParamCount);",
    "svc_addr = Hook_GetZwServiceInternal(svc_num);",
    "Hook_GetServiceIndex(DllProc, SkipIndexes)",
]:
    require(hook_c, term, "hook.c service topology")

for term in [
    "Hook_Find_ZwRoutine_1(ServiceIndex, &routine)",
    "Hook_Find_ZwRoutine_2(ServiceIndex, &routine)",
    "if (*(ULONG *)addr == 0x08C2C033 && addr[4] == 0x00)",
    "HAL7600 pattern: 33 C0 C2 08 00",
    "scanner skip over a third-party replacement stub",
    "legal Zw redirector shape",
    "not code-patching permission",
    "addr[i + 0] == 0xC2",
    "addr[i + 1] == 0x08 && addr[i + 2] == 0x00",
    "addr += i + 3;",
    "goto skip_padding_bytes;",
    "case 0xC2:  addr += 3;  break;",
    "case 0xC3:  addr += 1;  break;",
    "case 0x90:  addr += 1;  break;",
    "case 0x8B:  addr += 2;  break;",
]:
    require(hook32, term, "hook_32.c HAL7600 scanner")

for term in [
    "Hook_Find_ZwRoutine(ServiceIndex, &routine)",
    "if (*(USHORT *)addr == 0xC033 && addr[2] == 0xC3)",
    "HAL7600 pattern: 33 C0 C3",
    "scanner skip over a third-party replacement stub",
    "legal Zw redirector shape",
    "not code-patching permission",
    "if (*(USHORT *)(addr + i) == 0x9066)",
    "addr += i + 2;",
    "continue;",
    "if (addr[0] != 0x48 || addr[1] != 0x8B)",
    "if (addr[0] != 0xB8)",
    "if (addr[0] != 0xE9)",
    "if ((addr[0] != 0x66 && addr[0] != 0xC3) || addr[1] != 0x90)",
]:
    require(hook64, term, "hook_64.c HAL7600 scanner")

if "$Workaround$ - 3rd party fix" in hook32 or "$Workaround$ - 3rd party fix" in hook64:
    raise SystemExit("SREV-097 failed: stale generic workaround label remains")

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "native operating system services",
    "same kernel-mode",
    "instruction-format and instruction-reference source",
    "read-only system memory",
    "instruction-cache flushing",
    "No runtime behavior was changed.",
]:
    require(spec, term, "spec official shape")

for term in [
    "### SREV-097: Zw Redirector HAL7600 Skip Contract",
    "ZW_REDIRECTOR_HAL7600_SKIP_CONTRACT",
    "srev-097-zw-redirector-hal7600-skip-contract.schema.json",
]:
    require(ledger, term, "ledger")

print("SREV-097 schema/source gate passed")
