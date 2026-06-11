#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
obj="$root/Sandboxie/core/dll/obj.c"

rg -q "if \\(\\*Length < sizeof\\(OBJECT_NAME_INFORMATION\\)\\)" "$obj"
rg -q "status = SbieApi_GetFileName\\(ObjectHandle, NameBuf, &NameLen, NULL\\);" "$obj"
rg -q "\\*Length = sizeof\\(OBJECT_NAME_INFORMATION\\) \\+ NameLen;" "$obj"
rg -q "Obj_IsNamedPipeFileHandle\\(ObjectHandle\\)" "$obj"
rg -q "FileFsDeviceInformation" "$obj"
rg -q "FILE_DEVICE_NAMED_PIPE" "$obj"
rg -q "obj_use_driver_obj_lookup \\|\\| Obj_IsNamedPipeFileHandle\\(ObjectHandle\\)" "$obj"
rg -q "Obj_GetObjectNameFromDriver\\(ObjectHandle, name, &outlen\\)" "$obj"
rg -q "STATUS_BUFFER_TOO_SMALL" "$obj"

awk '
    /if \(! NT_SUCCESS\(status\)\)/ { in_fail=1 }
    in_fail && /use_driver_name_lookup/ { saw_guard=1 }
    in_fail && /goto finish;/ && saw_guard { saw_guard_finish=1 }
    in_fail && /status = __sys_NtQueryObject/ {
        if (!saw_guard_finish) {
            exit 1
        }
        saw_native_after_guard=1
    }
    in_fail && /^    }/ {
        if (!saw_guard_finish || !saw_native_after_guard) {
            exit 1
        }
        exit 0
    }
' "$obj"

echo "KPATH-003 check passed"
