#!/usr/bin/env python3
import json
from pathlib import Path
from ledger_reader import read_combined_ledger


ROOT = Path(__file__).resolve().parents[2]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"SREV-141 failed: {label} missing {needle!r}")


def reject(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"SREV-141 failed: {label} still contains {needle!r}")


schema = json.loads(
    (ROOT / "docs/plan/srev-141-obj-callback-kernelhandle-boundary.schema.json").read_text()
)
if schema.get("$schema") != "http://json-schema.org/draft-07/schema#":
    raise SystemExit("SREV-141 failed: schema is not draft-07")
if schema.get("id") != "OBJ_CALLBACK_KERNELHANDLE_BOUNDARY":
    raise SystemExit("SREV-141 failed: wrong schema id")

contracts = "\n".join(schema["contracts"])
for term in [
    "obj_flt.c owns only Object Manager process and thread handle pre-operation filtering",
    "ObRegisterCallbacks registration is limited to the object types and operations declared in OB_OPERATION_REGISTRATION",
    "The local registration has exactly two object-type entries PsProcessType and PsThreadType",
    "KernelHandle means the target handle is a kernel handle and is not a previous-mode field or ExGetPreviousMode substitute",
    "Non-kernel process and thread handle callbacks must flow to Thread_CheckObject_CommonEx so policy can remove rights from DesiredAccess",
    "The pre-operation callback may restrict DesiredAccess and must not add rights beyond the requested mask",
    "IPC message isolation is outside this callback and remains owned by IPC LPC ALPC hook and endpoint-filter surfaces",
]:
    require(contracts, term, "schema")

source = (ROOT / "Sandboxie/core/drv/obj_flt.c").read_text()
thread_c = (ROOT / "Sandboxie/core/drv/thread.c").read_text()
thread_h = (ROOT / "Sandboxie/core/drv/thread.h").read_text()
srev015 = (ROOT / "docs/plan/srev-015-alpc-connect-flags.md").read_text()
srev138 = (ROOT / "docs/plan/srev-138-alpc-local-header-contract.md").read_text()
kpath006 = (ROOT / "docs/plan/2026-05-27-sandboxie-kernel-path-audit.md").read_text()
spec = (ROOT / "docs/plan/srev-141-obj-callback-kernelhandle-boundary.md").read_text()
ledger = read_combined_ledger(ROOT)
ledger_fragment = (ROOT / "docs/plan/ledger/srev-141.md").read_text()

for term in schema["official_references"]:
    require(spec, term, "spec official reference")

for term in [
    "static P_ObRegisterCallbacks pObRegisterCallbacks = NULL;",
    "static P_ObUnRegisterCallbacks pObUnRegisterCallbacks = NULL;",
    "static OB_CALLBACK_REGISTRATION  Obj_CallbackRegistration = { 0 };",
    "static OB_OPERATION_REGISTRATION Obj_OperationRegistrations[2] = { { 0 }, { 0 } };",
    "pObRegisterCallbacks = (P_ObRegisterCallbacks)MmGetSystemRoutineAddress(&uni);",
    "pObUnRegisterCallbacks = (P_ObUnRegisterCallbacks)MmGetSystemRoutineAddress(&uni);",
    "Obj_OperationRegistrations[0].ObjectType = PsProcessType;",
    "Obj_OperationRegistrations[0].Operations = OB_OPERATION_HANDLE_CREATE | OB_OPERATION_HANDLE_DUPLICATE;",
    "Obj_OperationRegistrations[0].PreOperation = Obj_PreOperationCallback;",
    "Obj_OperationRegistrations[1].ObjectType = PsThreadType;",
    "Obj_OperationRegistrations[1].Operations = OB_OPERATION_HANDLE_CREATE | OB_OPERATION_HANDLE_DUPLICATE;",
    "Obj_OperationRegistrations[1].PreOperation = Obj_PreOperationCallback;",
    "Obj_CallbackRegistration.Version                    = OB_FLT_REGISTRATION_VERSION;",
    "Obj_CallbackRegistration.OperationRegistrationCount = 2;",
    "Obj_CallbackRegistration.Altitude                   = Driver_Altitude;",
    "Obj_CallbackRegistration.OperationRegistration      = Obj_OperationRegistrations;",
    "status = pObRegisterCallbacks (&Obj_CallbackRegistration, &Obj_FilterCookie);",
    "pObUnRegisterCallbacks(Obj_FilterCookie);",
]:
    require(source, term, "object callback registration")

for term in [
    "Skip kernel-handle callbacks. Non-kernel process/thread handles still",
    "pass through DesiredAccess policy before the handle is granted.",
    "if (PreInfo->KernelHandle)\n        return OB_PREOP_SUCCESS;",
]:
    require(source, term, "KernelHandle gate")

reject(source, "Filter only if request made outside of the kernel", "stale previous-mode comment")
reject(source, "//if (ExGetPreviousMode() == KernelMode)", "dead previous-mode branch")
reject(source, "PreInfo->KernelHandle == 1", "boolean bit test")

for term in [
    "case OB_OPERATION_HANDLE_CREATE:",
    "DesiredAccess = &PreInfo->Parameters->CreateHandleInformation.DesiredAccess;",
    "case OB_OPERATION_HANDLE_DUPLICATE:",
    "DesiredAccess = &PreInfo->Parameters->DuplicateHandleInformation.DesiredAccess;",
    "InitialDesiredAccess = *DesiredAccess;",
    "if (PreInfo->ObjectType == *PsProcessType)",
    "HANDLE TargetProcessId = PsGetProcessId((PEPROCESS)PreInfo->Object);",
    "*DesiredAccess = Thread_CheckObject_CommonEx(TargetProcessId, ProcessObject, InitialDesiredAccess, TRUE, TRUE);",
    "else if (PreInfo->ObjectType == *PsThreadType)",
    "HANDLE TargetProcessId = PsGetThreadProcessId ((PETHREAD)PreInfo->Object);",
    "PEPROCESS ProcessObject = PsGetThreadProcess((PETHREAD)PreInfo->Object);",
    "*DesiredAccess = Thread_CheckObject_CommonEx(TargetProcessId, ProcessObject, InitialDesiredAccess, FALSE, TRUE);",
]:
    require(source, term, "DesiredAccess policy route")

for term in [
    "proper  IPC isolation requires filtering of NtRequestPort, NtRequestWaitReplyPort, and NtAlpcSendWaitReceivePort calls",
    "\"Process\"    -> Thread_CheckProcessObject        <- PsProcessType",
    "\"Thread\"     -> Thread_CheckThreadObject         <- PsThreadType",
    "opening/creation of files is handled by a minifilter installed with FltRegisterFilter",
    "opening/creation of registry keys is handled by CmRegisterCallbackEx",
]:
    require(source, term, "local topology comment")

for term in [
    "ACCESS_MASK Thread_CheckObject_CommonEx(",
]:
    require(thread_h, term, "thread header owner")

for term in [
    "_FX ACCESS_MASK Thread_CheckObject_CommonEx(",
    "if (pid == cur_pid)\n        return DesiredAccess;",
    "PROCESS *proc = Process_Find(NULL, NULL);",
    "if (!proc || (proc == PROCESS_TERMINATED) || proc->bHostInject)",
    "if (!proc || (proc == PROCESS_TERMINATED) || proc->bHostInject || proc->disable_object_flt)",
    "return 0; // deny access",
    "return DesiredAccess;",
]:
    require(thread_c, term, "Thread_CheckObject_CommonEx owner")

for term in [
    "Microsoft Learn does not expose a public `NtAlpcConnectPort`",
    "Ledger keeps the issue open for runtime capture",
]:
    require(srev015, term, "SREV-015 ALPC precedent")

for term in [
    "Endpoint policy may read payload bytes only after a caller has validated the",
    "`PORT_MESSAGE` header",
]:
    require(srev138, term, "SREV-138 IPC precedent")

for term in [
    "KPATH-006: RPC Endpoint Filters Need A Spec-Based Opnum Parser",
    "`PORT_MESSAGE` is the carrier; RPC/NCALRPC is the payload protocol",
    "Ipc_GetRpcMsgId",
]:
    require(kpath006, term, "KPATH-006 IPC parser precedent")

for term in [
    "### SREV-141: Object Callback KernelHandle Boundary",
    "OBJ_CALLBACK_KERNELHANDLE_BOUNDARY",
    "srev-141-obj-callback-kernelhandle-boundary.schema.json",
    "KernelHandle",
    "Thread_CheckObject_CommonEx",
]:
    require(ledger, term, "combined ledger")
    require(ledger_fragment, term, "ledger fragment")

print("SREV-141 schema/source gate passed")
