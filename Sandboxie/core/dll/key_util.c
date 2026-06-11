/*
 * Copyright 2004-2020 Sandboxie Holdings, LLC 
 *
 * This program is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

//---------------------------------------------------------------------------
// Key Utilities
//---------------------------------------------------------------------------

#include <limits.h>

//---------------------------------------------------------------------------
// Key_OpenIfBoxed
//---------------------------------------------------------------------------


_FX NTSTATUS Key_OpenIfBoxed(
    HANDLE *out_handle, ACCESS_MASK access, OBJECT_ATTRIBUTES *objattrs)
{
    NTSTATUS status;
    WCHAR *TruePath;
    WCHAR *CopyPath;

    if (! objattrs)
        return STATUS_INVALID_PARAMETER;

    status = Key_GetName(
        objattrs->RootDirectory, objattrs->ObjectName,
        &TruePath, &CopyPath, NULL);

    if (NT_SUCCESS(status)) {

        ULONG mp_flags = SbieDll_MatchPath(L'k', TruePath);
        if ((mp_flags & ~PATH_WRITE_FLAG) != 0)
            status = STATUS_BAD_INITIAL_PC;
        else
            status = NtOpenKey(out_handle, access, objattrs);
    }

    return status;
}


//---------------------------------------------------------------------------
// Key_OpenOrCreateIfBoxed
//---------------------------------------------------------------------------


_FX NTSTATUS Key_OpenOrCreateIfBoxed(
    HANDLE *out_handle, ACCESS_MASK access, OBJECT_ATTRIBUTES *objattrs)
{
    NTSTATUS status = Key_OpenIfBoxed(out_handle, access, objattrs);

    if (status == STATUS_OBJECT_NAME_NOT_FOUND) {

        PSECURITY_DESCRIPTOR SaveSD = objattrs->SecurityDescriptor;
        objattrs->SecurityDescriptor = Secure_EveryoneSD;

        status = NtCreateKey(
            out_handle, access, objattrs, 0, NULL, 0, NULL);

        objattrs->SecurityDescriptor = SaveSD;
    }

    return status;
}


//---------------------------------------------------------------------------
// Key_DeleteValueFromCLSID
//---------------------------------------------------------------------------


_FX void Key_DeleteValueFromCLSID(
    const WCHAR *Xxxid, const WCHAR *Guid, const WCHAR *ValueName)
{
    static const WCHAR *_HKLM_Classes =
        L"\\registry\\machine\\software\\classes\\";
    NTSTATUS status;
    OBJECT_ATTRIBUTES objattrs;
    UNICODE_STRING objname;
    ULONG DesiredAccess;
    SIZE_T path_len;
    WCHAR *path;
    HANDLE handle;

    DesiredAccess = KEY_SET_VALUE;
#ifndef _WIN64
    if (Dll_IsWow64)
        DesiredAccess |= KEY_WOW64_64KEY;
#endif

    path_len = wcslen(_HKLM_Classes) + wcslen(Xxxid) + wcslen(Guid) + 4;
    if (path_len > ULONG_MAX / sizeof(WCHAR))
        return;

    path = Dll_AllocTemp((ULONG)(path_len * sizeof(WCHAR)));
    if (! path)
        return;

    Sbie_snwprintf(path, path_len, L"%s%s\\{%s}", _HKLM_Classes, Xxxid, Guid);
    RtlInitUnicodeString(&objname, path);

    InitializeObjectAttributes(
        &objattrs, &objname, OBJ_CASE_INSENSITIVE, NULL, NULL);

    status = Key_OpenIfBoxed(&handle, DesiredAccess, &objattrs);
    if (NT_SUCCESS(status)) {

        RtlInitUnicodeString(&objname, ValueName);
        NtDeleteValueKey(handle, &objname);

        NtClose(handle);
    }

    Dll_Free(path);
}
