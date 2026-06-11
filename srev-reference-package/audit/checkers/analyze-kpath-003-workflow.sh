#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

obj="$root/Sandboxie/core/dll/obj.c"
file_dir="$root/Sandboxie/core/dll/file_dir.c"
drv_file="$root/Sandboxie/core/drv/file.c"
settings="$root/Sandboxie/install/SbieSettings.ini"

rel() {
    local path="$1"
    printf '%s' "${path#"$root"/}"
}

lines_for() {
    local file="$1"
    local pattern="$2"
    rg -n "$pattern" "$file" | sed "s#^#$(rel "$file"):#"
}

section() {
    printf '\n## %s\n\n' "$1"
}

echo "# KPATH-003 Workflow Analysis"
echo
echo "Generated from source readback. This script is diagnostic only; it does not prove runtime hang reproduction."

section "Coordinate"
cat <<'TEXT'
thing: hooked NtQueryObject(ObjectNameInformation)
shape: object handle -> object type -> object name -> sandbox path rewrite
boundary: sandboxed user-mode handle query crosses into native NtQueryObject or Sandboxie driver lookup
owner: core/dll/obj.c owns hooked query workflow; core/drv/file.c owns driver object-name lookup
acceptance gate: pipe-backed file handles must not be sent through native object-name query without a hang-safe path
TEXT

section "Entry Points"
lines_for "$obj" 'SBIEDLL_HOOK\(Obj_,NtQueryObject\)|obj_use_driver_obj_lookup|UseDriverObjLookup'

section "Known Hang Evidence"
lines_for "$obj" 'locking up forever|driver to lookup'
lines_for "$file_dir" 'NtQueryObject on a named pipe handle can hang|FILE_DEVICE_NAMED_PIPE'
lines_for "$settings" '^\[UseDriverObjLookup\]|avoid hangs with some handles'
lines_for "$obj" 'Obj_IsNamedPipeFileHandle|FileFsDeviceInformation|FILE_DEVICE_NAMED_PIPE'

section "Workflow: Obj_GetObjectName"
cat <<'TEXT'
Obj_GetObjectName has an explicit safe branch:
  if obj_use_driver_obj_lookup:
      SbieApi_GetFileName(handle) -> driver File_Api_GetName
  else:
      native NtQueryObject(ObjectNameInformation)
TEXT
lines_for "$obj" 'Obj_GetObjectName|SbieApi_GetFileName|ObjectNameInformation, ObjectName'

section "Workflow: Obj_NtQueryObject"
cat <<'TEXT'
Obj_NtQueryObject has a different workflow:
  1. bypass hook for recursive calls or non-name queries
  2. query object type natively
  3. allow File/Key/Directory/Port/Event/Mutant/Section/Semaphore through rewrite path
  4. for File objects, query FileFsDeviceInformation and classify named pipes
  5. route named-pipe File objects, or all File objects when UseDriverObjLookup is enabled, through driver lookup
  6. query object name natively only for non-pipe File objects and non-File supported object types
  7. retry through the same selected name-query path on size mismatch
  8. on selected-path failure, do not fall back to native NtQueryObject for driver-routed File objects
  9. rewrite returned name by object type

Mitigation gate:
  Obj_NtQueryObject must classify named-pipe File objects before native
  object-name query. UseDriverObjLookup remains a broader compatibility setting,
  but named pipes are a default-on safety route.
TEXT
lines_for "$obj" 'obj_NtQueryObject_lock|ObjectInformationClass != ObjectNameInformation|Obj_GetObjectType|type != OBJ_TYPE_FILE|__sys_NtQueryObject\(|File_NtQueryObjectName|Key_NtQueryObjectName|Ipc_NtQueryObjectName'

section "Driver Lookup Path"
cat <<'TEXT'
Driver lookup path used by SbieApi_GetFileName:
  user-mode SbieApi_GetFileName -> API_GET_FILE_NAME -> File_Api_GetName
  File_Api_GetName references the object by handle and can use FILE_OBJECT/DeviceObject metadata before name construction.
TEXT
lines_for "$drv_file" 'File_Api_GetName|ObReferenceObjectByHandle|pObGetObjectType|IoFileObjectType|DeviceType != FILE_DEVICE_DISK|Obj_GetName|FILE_DEVICE_CONSOLE'

section "Static Gap Checks"

if awk '
    /_FX NTSTATUS Obj_NtQueryObject\(/ { in_func=1 }
    in_func && /Obj_IsNamedPipeFileHandle/ { found=1 }
    in_func && /^}/ { in_func=0 }
    END { exit found ? 0 : 1 }
' "$obj"; then
    echo "OK: Obj_NtQueryObject checks named-pipe File handles before name query."
else
    echo "GAP: Obj_NtQueryObject does not classify named-pipe File handles."
fi

native_name_count="$(
    awk '
        /_FX NTSTATUS Obj_NtQueryObject\(/ { in_func=1 }
        in_func && /__sys_NtQueryObject\(/ { count++ }
        in_func && /^}/ { in_func=0 }
        END { print count + 0 }
    ' "$obj"
)"
echo "Native NtQueryObject calls inside Obj_NtQueryObject: $native_name_count"

if rg -q 'FILE_DEVICE_NAMED_PIPE' "$obj"; then
    echo "OK: obj.c checks FILE_DEVICE_NAMED_PIPE."
else
    echo "GAP: obj.c does not check FILE_DEVICE_NAMED_PIPE before native object-name query."
fi

section "Next Probe"
cat <<'TEXT'
Recommended next step:
  Build a Windows repro that creates a synchronous named pipe with pending read,
  then calls NtQueryObject(ObjectNameInformation) inside a sandbox.

Decision after repro:
  Verify that the named-pipe device-type route avoids the hang by default, then
  verify normal file/key/ipc name rewriting. If driver lookup also blocks for a
  target pipe class, the next fix must be a fail-safe status for named-pipe
  object-name queries instead of falling back to native NtQueryObject.
TEXT
