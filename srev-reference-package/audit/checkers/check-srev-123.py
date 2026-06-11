#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-123 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-123 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-123-scm-create-request-allocation-lifetime.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-123 failed: schema is not draft-07")
if schema.get("id") != "SCM_CREATE_REQUEST_ALLOCATION_LIFETIME":
    raise SystemExit("SREV-123 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "Dll_Alloc and Dll_AllocTemp may fail before returning writable storage",
    "Scm_AddBoxedService writes names2 only after Dll_AllocTemp succeeds",
    "Scm_CreateServiceW writes the fake service handle name only after Dll_Alloc succeeds",
    "Scm_CreateServiceW allocates the fake service handle before Scm_AddBoxedService mutates SandboxedServices",
    "Scm_CreateServiceW frees the fake service handle if Scm_AddBoxedService fails",
    "Scm_StartBoxedService2 fills SERVICE_RUN_REQ only after Dll_Alloc succeeds",
    "Scm_StartBoxedService2 frees SERVICE_RUN_REQ after SbieDll_CallServer returns",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/dll/scm_create.c").read_text()
dllmem = (ROOT / "Sandboxie/core/dll/dllmem.c").read_text()
spec = (ROOT / "docs/plan/srev-123-scm-create-request-allocation-lifetime.md").read_text()
ledger = read_combined_ledger(ROOT)

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "_FX void *Dll_AllocFromPool(POOL *pool, ULONG size)",
    "ULONG alloc_size = size;",
    "ptr = Pool_Alloc(pool, alloc_size);",
    "if (! ptr)\n        return Dll_AllocFailure();",
    "_FX void *Dll_AllocFailure(void)",
    "if (! Dll_BoxName)\n        return NULL;",
    "return NULL;",
    "_FX void *Dll_Alloc(ULONG size)",
    "_FX void *Dll_AllocTemp(ULONG size)",
]:
    require(dllmem, term, "Dll allocation failure shape")

add_boxed = source[
    source.index("_FX NTSTATUS Scm_AddBoxedService"):
    source.index("// Scm_CreateServiceW")
]
for term in [
    "names2 = Dll_AllocTemp((len + wcslen(ServiceName) + 8) * sizeof(WCHAR));",
    "if (! names2) {\n        status = STATUS_INSUFFICIENT_RESOURCES;\n        goto finish;\n    }",
    "wmemcpy(names2, names1, len);",
    "NtSetValueKey(\n            hkey, &uni, 0, REG_MULTI_SZ, names2, len * sizeof(WCHAR));",
    "Dll_Free(names2);",
    "Scm_ReleaseMutex(hMutex);",
    "Dll_Free(names1);",
]:
    require(add_boxed, term, "Scm_AddBoxedService")
if add_boxed.index("if (! names2)") > add_boxed.index("wmemcpy(names2"):
    raise SystemExit("SREV-123 failed: names2 allocation gate is after write")
reject(add_boxed, "names2 = Dll_AllocTemp((len + wcslen(ServiceName) + 8) * sizeof(WCHAR));\n    wmemcpy(names2", "unguarded names2 allocation")

create_service = source[
    source.index("_FX SC_HANDLE Scm_CreateServiceW"):
    source.index("// Scm_CreateServiceA")
]
for term in [
    "ULONG error = ERROR_INVALID_PARAMETER;",
    "name = Dll_Alloc(\n        sizeof(ULONG) + (wcslen(lpServiceName) + 1) * sizeof(WCHAR));",
    "if (! name) {\n        status = STATUS_INSUFFICIENT_RESOURCES;\n        error = ERROR_NOT_ENOUGH_MEMORY;\n        goto abort;\n    }",
    "*(ULONG *)name = tzuk;",
    "wcscpy((WCHAR *)(((ULONG *)name) + 1), lpServiceName);",
    "status = Scm_AddBoxedService(lpServiceName);",
    "if (! NT_SUCCESS(status)) {\n        Dll_Free(name);\n        goto abort;\n    }",
    "SetLastError(error);",
]:
    require(create_service, term, "Scm_CreateServiceW")
if create_service.index("if (! name)") > create_service.index("*(ULONG *)name = tzuk;"):
    raise SystemExit("SREV-123 failed: fake handle allocation gate is after write")
if create_service.index("name = Dll_Alloc(") > create_service.index("status = Scm_AddBoxedService(lpServiceName);"):
    raise SystemExit("SREV-123 failed: fake handle allocation moved after boxed-service list mutation")
reject(create_service, "name = Dll_Alloc(\n        sizeof(ULONG) + (wcslen(lpServiceName) + 1) * sizeof(WCHAR));\n    *(ULONG *)name = tzuk;", "unguarded fake handle allocation")

start_boxed = source[
    source.index("_FX ULONG Scm_StartBoxedService2"):
    source.index("// Scm_StartServiceWImpl")
]
for term in [
    "req = Dll_Alloc(req_len);",
    "if (! req) {\n        if (free_path)\n            HeapFree(GetProcessHeap(), 0, path);\n        return ERROR_NOT_ENOUGH_MEMORY;\n    }",
    "req->h.length = req_len;",
    "req->h.msgid = MSGID_SERVICE_RUN;",
    "rpl = (MSG_HEADER *)SbieDll_CallServer(&req->h);",
    "Dll_Free(req);",
]:
    require(start_boxed, term, "Scm_StartBoxedService2")
if start_boxed.index("if (! req)") > start_boxed.index("req->h.length = req_len;"):
    raise SystemExit("SREV-123 failed: SERVICE_RUN_REQ allocation gate is after write")
if start_boxed.index("Dll_Free(req);") < start_boxed.index("SbieDll_CallServer"):
    raise SystemExit("SREV-123 failed: SERVICE_RUN_REQ free is before call-server use")
reject(start_boxed, "req = Dll_Alloc(req_len);\n    req->h.length = req_len;", "unguarded SERVICE_RUN_REQ allocation")

for term in [
    "### SREV-123: SCM Create Request Allocation Lifetime",
    "SCM_CREATE_REQUEST_ALLOCATION_LIFETIME",
    "srev-123-scm-create-request-allocation-lifetime.schema.json",
    "Sandboxie/core/dll/scm_create.c",
    "Scm_AddBoxedService",
    "Scm_CreateServiceW",
    "Scm_StartBoxedService2",
    "SERVICE_RUN_REQ",
    "ERROR_NOT_ENOUGH_MEMORY",
    "STATUS_INSUFFICIENT_RESOURCES",
]:
    require(ledger, term, "ledger")

print("SREV-123 schema/source gate passed")
