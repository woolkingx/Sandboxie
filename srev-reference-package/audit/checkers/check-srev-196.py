#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-196 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-196 failed: stale {label} remains {needle!r}")


def between(text: str, start: str, end: str) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start))
    return text[a:b]


schema = json.loads(
    (ROOT / "docs/plan/srev-196-dll-tls-name-buffer-allocation-contract.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-196 failed: schema is not draft-07")
if schema.get("id") != "DLL_TLS_NAME_BUFFER_ALLOCATION_CONTRACT":
    raise SystemExit("SREV-196 failed: wrong schema id")
if schema.get("owner") != "Sandboxie/core/dll/dllmem.c":
    raise SystemExit("SREV-196 failed: wrong owner")
if schema.get("entry_surface") != "Sandboxie/core/dll/dll.h":
    raise SystemExit("SREV-196 failed: wrong entry surface")

contracts = "\n".join(schema["contracts"])
for term in [
    "TlsAlloc failure is represented by TLS_OUT_OF_INDEXES",
    "TlsGetValue may return NULL for a valid empty slot and clears last error on success",
    "TlsSetValue returns zero on failure and must be checked before TLS publication is trusted",
    "Dll_AllocFromPool checks ULONG addition before adding debug padding and the hidden ULONG_PTR prefix",
    "Dll_GetTlsData checks Dll_Alloc before memzero",
    "Dll_GetTlsData frees THREAD_DATA if TlsSetValue fails",
    "Dll_GetTlsNameBuffer checks page-rounding arithmetic before allocation",
    "Dll_GetTlsNameBuffer uses a temporary pointer before publishing name_buffer and name_buffer_len",
    "Dll_PushTlsNameBuffer checks depth before incrementing and indexing name_buffer_count",
    "Dll_PopTlsNameBuffer prevents negative depth",
    "DEBUG_MEMORY name-buffer checks use name_buffer_depth",
]:
    require(contracts, term, "schema contract")

src = (ROOT / "Sandboxie/core/dll/dllmem.c").read_text()
file_init = (ROOT / "Sandboxie/core/dll/file_init.c").read_text()
hdr = (ROOT / "Sandboxie/core/dll/dll.h").read_text()
pool = (ROOT / "Sandboxie/common/pool.c").read_text()
spec = (ROOT / "docs/plan/srev-196-dll-tls-name-buffer-allocation-contract.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-196.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "SREV-265 records one caller-side consequence",
    "must check the returned TLS name buffer before",
]:
    require(spec, term, "spec caller adjacency")

for term in [
    "#define NAME_BUFFER_COUNT       12",
    "#define NAME_BUFFER_DEPTH       16",
    "WCHAR *name_buffer[NAME_BUFFER_COUNT][NAME_BUFFER_DEPTH];",
    "ULONG name_buffer_len[NAME_BUFFER_COUNT][NAME_BUFFER_DEPTH];",
    "int name_buffer_count[NAME_BUFFER_DEPTH];",
    "int name_buffer_depth;",
    "THREAD_DATA *Dll_GetTlsData(ULONG *pLastError);",
    "WCHAR *Dll_GetTlsNameBuffer(THREAD_DATA *data, ULONG which, ULONG size);",
]:
    require(hdr, term, "dll.h THREAD_DATA surface")

for term in [
    "if (size >= LARGE_CHUNK_MAXIMUM)",
    "return NULL;",
    "void *Pool_Alloc(POOL *pool, ULONG size)",
]:
    require(pool, term, "pool allocation failure shape")

for term in [
    "static void *Dll_AllocFailure(void);",
    "static BOOLEAN Dll_AddUlong(ULONG value, ULONG addend, ULONG *result);",
    "static BOOLEAN Dll_RoundTlsNameBufferSize(ULONG size, ULONG *rounded_size);",
]:
    require(src, term, "helper declaration")

alloc = between(src, "_FX void *Dll_AllocFromPool(", "//---------------------------------------------------------------------------\n// Dll_AllocFailure")
for term in [
    "ULONG alloc_size = size;",
    "Dll_AddUlong(alloc_size, 64 * 2, &alloc_size)",
    "Dll_AddUlong(alloc_size, (ULONG)sizeof(ULONG_PTR), &alloc_size)",
    "ptr = Pool_Alloc(pool, alloc_size);",
    "return Dll_AllocFailure();",
    "*(ULONG_PTR *)ptr = alloc_size;",
]:
    require(alloc, term, "Dll_AllocFromPool checked size")
reject(alloc, "size += sizeof(ULONG_PTR);", "unchecked hidden prefix addition")

add = between(src, "_FX BOOLEAN Dll_AddUlong(", "//---------------------------------------------------------------------------\n// Dll_RoundTlsNameBufferSize")
for term in [
    "if (value > (ULONG)-1 - addend)",
    "*result = value + addend;",
    "return TRUE;",
]:
    require(add, term, "checked ULONG addition")

rounding = between(src, "_FX BOOLEAN Dll_RoundTlsNameBufferSize(", "//---------------------------------------------------------------------------\n// Dll_Alloc")
for term in [
    "Dll_AddUlong(size, 64, &size)",
    "Dll_AddUlong(size, PAGE_SIZE - 1, &size)",
    "*rounded_size = size & ~(PAGE_SIZE - 1);",
]:
    require(rounding, term, "checked name-buffer rounding")

tls = between(src, "_FX THREAD_DATA *Dll_GetTlsData(", "//---------------------------------------------------------------------------\n// Dll_FreeTlsData")
for term in [
    "ULONG LastError = GetLastError();",
    "data = TlsGetValue(Dll_TlsIndex);",
    "data = Dll_Alloc(sizeof(THREAD_DATA));",
    "if (! data)",
    "return NULL;",
    "memzero(data, sizeof(THREAD_DATA));",
    "if (! TlsSetValue(Dll_TlsIndex, data))",
    "Dll_Free(data);",
    "data = NULL;",
    "SetLastError(LastError);",
]:
    require(tls, term, "Dll_GetTlsData publication gate")
if not tls.index("if (! data)") < tls.index("memzero(data, sizeof(THREAD_DATA));"):
    raise SystemExit("SREV-196 failed: Dll_GetTlsData zeroes before allocation check")
if not tls.index("if (! TlsSetValue(Dll_TlsIndex, data))") < tls.rindex("SetLastError(LastError);"):
    raise SystemExit("SREV-196 failed: TlsSetValue failure is checked too late")

namebuf = between(src, "ALIGNED WCHAR *Dll_GetTlsNameBuffer", "//---------------------------------------------------------------------------\n// Dll_PushTlsNameBuffer")
for term in [
    "WCHAR *new_name_buffer;",
    "if (! data)",
    "return NULL;",
    "Dll_RoundTlsNameBufferSize(size, &size)",
    "new_name_buffer = Dll_Alloc(size);",
    "if (! new_name_buffer)",
    "memcpy(new_name_buffer, old_name_buffer, old_name_buffer_len);",
    "*name_buffer_len = size;",
    "*name_buffer = new_name_buffer;",
]:
    require(namebuf, term, "Dll_GetTlsNameBuffer allocation gate")
if not namebuf.index("new_name_buffer = Dll_Alloc(size);") < namebuf.index("*name_buffer_len = size;"):
    raise SystemExit("SREV-196 failed: name buffer length published before allocation")
if not namebuf.index("new_name_buffer = Dll_Alloc(size);") < namebuf.index("*name_buffer = new_name_buffer;"):
    raise SystemExit("SREV-196 failed: name buffer pointer published before allocation")
reject(namebuf, "size = (size + 64 + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1);", "unchecked name-buffer rounding")
reject(namebuf, "*name_buffer = Dll_Alloc(*name_buffer_len);", "direct slot allocation")

mount_point = between(
    file_init,
    "the sandbox path may be specified on a directory mount point",
    "//---------------------------------------------------------------------------\n// File_AdjustDrives",
)
for term in [
    "WCHAR *TruePath = Dll_GetTlsNameBuffer(TlsData, TRUE_NAME_BUFFER,",
    "if (TruePath) {\n            wmemcpy(TruePath, Dll_BoxFilePath, Dll_BoxFilePathLen + 1);",
    "WCHAR *AltBoxPath = Dll_Alloc((len + 1) * sizeof(WCHAR));",
    "if (AltBoxPath) {",
    "File_AltBoxPath = AltBoxPath;",
    "File_AltBoxPathLen = len;",
]:
    require(mount_point, term, "file_init caller gate")
reject(
    mount_point,
    "WCHAR *TruePath = Dll_GetTlsNameBuffer(TlsData, TRUE_NAME_BUFFER,\n                                (Dll_BoxFilePathLen + 1) * sizeof(WCHAR));\n        wmemcpy(TruePath, Dll_BoxFilePath, Dll_BoxFilePathLen + 1);",
    "file_init caller gate",
)

push = between(src, "ALIGNED void Dll_PushTlsNameBuffer", "//---------------------------------------------------------------------------\n// Dll_PopTlsNameBuffer")
for term in [
    "if (! data)",
    "if (data->name_buffer_depth >= NAME_BUFFER_DEPTH - 1)",
    "ExitProcess(-1);",
    "++data->name_buffer_depth;",
    "data->name_buffer_count[data->name_buffer_depth] = 0;",
]:
    require(push, term, "push depth gate")
if not push.index("if (data->name_buffer_depth >= NAME_BUFFER_DEPTH - 1)") < push.index("++data->name_buffer_depth;"):
    raise SystemExit("SREV-196 failed: push increments before depth gate")

pop = src[src.index("_FX void Dll_PopTlsNameBuffer"):]
for term in [
    "if (! data)",
    "data->name_buffer_depth <= 0",
    "data->name_buffer_depth = 0;",
    "return;",
    "--data->name_buffer_depth;",
]:
    require(pop, term, "pop depth gate")
if not pop.index("data->name_buffer_depth <= 0") < pop.index("--data->name_buffer_depth;"):
    raise SystemExit("SREV-196 failed: pop decrements before underflow gate")
reject(pop, "data->depth", "DEBUG_MEMORY stale depth field")

for term in [
    "kind: srev-ledger-entry",
    "id: SREV-196",
    "owner: Sandboxie/core/dll/dllmem.c",
    "spec: docs/plan/srev-196-dll-tls-name-buffer-allocation-contract.md",
    "schema: docs/plan/srev-196-dll-tls-name-buffer-allocation-contract.schema.json",
    "checker: docs/plan/check-srev-196.py",
]:
    require(ledger_fragment, term, "ledger fragment")

for term in [
    "### SREV-196: DLL TLS Name Buffer Allocation Contract",
    "DLL_TLS_NAME_BUFFER_ALLOCATION_CONTRACT",
    "Sandboxie/core/dll/dllmem.c",
    "Dll_AddUlong",
    "Dll_RoundTlsNameBufferSize",
    "TlsSetValue",
    "patched-source-needs-windows-runtime",
    "SREV-265",
]:
    require(ledger, term, "combined ledger")

print("SREV-196 schema/source gate passed")
