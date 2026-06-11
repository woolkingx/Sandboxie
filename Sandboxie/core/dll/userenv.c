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
// User Env
//---------------------------------------------------------------------------


#include "dll.h"


//---------------------------------------------------------------------------
// Functions
//---------------------------------------------------------------------------


static BOOL UserEnv_RegisterGPNotification(HANDLE hEvent, BOOL bMachine);

static BOOL UserEnv_UnregisterGPNotification(HANDLE hEvent);

static ULONG UserEnv_GetAppliedGPOList(
    ULONG dwFlags, const WCHAR *pMachineName, PSID pSidUser,
    GUID *pGuidExtension, void *ppGPOList);

static NTSTATUS UserEnv_RtlGetVersion(LPOSVERSIONINFOEXW lpVersionInfo);
static BOOL UserEnv_GetVersionExW(LPOSVERSIONINFOEXW lpVersionInfo);
static BOOL UserEnv_GetVersionExA(LPOSVERSIONINFOEXA lpVersionInfo);
static BOOL UserEnv_VerifyVersionInfoW(
    LPOSVERSIONINFOEXW lpVersionInformation,
    DWORD dwTypeMask,
    DWORDLONG dwlConditionMask);

static HRESULT UserEnv_CreateAppContainerProfile(
    PCWSTR              pszAppContainerName,
    PCWSTR              pszDisplayName,
    PCWSTR              pszDescription,
    PSID_AND_ATTRIBUTES pCapabilities,
    DWORD               dwCapabilityCount,
    PSID                *ppSidAppContainerSid);

//---------------------------------------------------------------------------


typedef BOOL (*P_RegisterGPNotification)(HANDLE hEvent, BOOL bMachine);

typedef BOOL (*P_UnregisterGPNotification)(HANDLE hEvent, BOOL bMachine);

typedef ULONG (*P_GetAppliedGPOList)(
    ULONG dwFlags, const WCHAR *pMachineName, PSID pSidUser,
    GUID *pGuidExtension, void *ppGPOList);

typedef NTSTATUS(*P_RtlGetVersion)(LPOSVERSIONINFOEXW);
typedef BOOL (*P_GetVersionExW)(LPOSVERSIONINFOEXW lpVersionInfo);
typedef BOOL (*P_GetVersionExA)(LPOSVERSIONINFOEXA lpVersionInfo);
typedef BOOL (*P_VerifyVersionInfoW)(
    LPOSVERSIONINFOEXW lpVersionInformation,
    DWORD dwTypeMask,
    DWORDLONG dwlConditionMask);
typedef ULONGLONG (WINAPI *P_VerSetConditionMask)(
    ULONGLONG ConditionMask,
    DWORD TypeMask,
    BYTE Condition);

typedef BOOL(*P_CreateAppContainerProfile)(
    PCWSTR              pszAppContainerName,
    PCWSTR              pszDisplayName,
    PCWSTR              pszDescription,
    PSID_AND_ATTRIBUTES pCapabilities,
    DWORD               dwCapabilityCount,
    PSID                *ppSidAppContainerSid);


//---------------------------------------------------------------------------


static P_RegisterGPNotification     __sys_RegisterGPNotification    = NULL;
static P_UnregisterGPNotification   __sys_UnregisterGPNotification  = NULL;
static P_GetAppliedGPOList          __sys_GetAppliedGPOList         = NULL;

static P_RtlGetVersion              __sys_RtlGetVersion = NULL;
static P_GetVersionExW              __sys_GetVersionExW             = NULL;
static P_GetVersionExA              __sys_GetVersionExA             = NULL;
static P_VerifyVersionInfoW         __sys_VerifyVersionInfoW        = NULL;
static P_VerSetConditionMask        __sys_VerSetConditionMask       = NULL;

static P_CreateAppContainerProfile  __sys_CreateAppContainerProfile = NULL;

static DWORD UserEnv_dwBuildNumber = 0;

//---------------------------------------------------------------------------
// UserEnv_Init
//---------------------------------------------------------------------------


_FX BOOLEAN UserEnv_InitVer(HMODULE module)
{
    void* RtlGetVersion;
    void* GetVersionExW;
    void* GetVersionExA;
    void* VerifyVersionInfoW;

    WCHAR str[32];
    if (SbieDll_GetSettingsForName(NULL, Dll_ImageName, L"OverrideOsBuild", str, sizeof(str), NULL))
        UserEnv_dwBuildNumber = _wtoi(str);

    if (UserEnv_dwBuildNumber == 0)
        return TRUE; // don't hook if not needed

    RtlGetVersion = GetProcAddress(GetModuleHandleW(L"ntdll"), "RtlGetVersion");
    GetVersionExW = (P_GetVersionExW)GetProcAddress(module, "GetVersionExW");
    GetVersionExA = (P_GetVersionExA)GetProcAddress(module, "GetVersionExA");
    VerifyVersionInfoW = GetProcAddress(module, "VerifyVersionInfoW");
    __sys_VerSetConditionMask = (P_VerSetConditionMask)
        GetProcAddress(module, "VerSetConditionMask");
    if (!__sys_VerSetConditionMask && Dll_Kernel32)
        __sys_VerSetConditionMask = (P_VerSetConditionMask)
            GetProcAddress(Dll_Kernel32, "VerSetConditionMask");

    SBIEDLL_HOOK(UserEnv_, RtlGetVersion);
    SBIEDLL_HOOK(UserEnv_, GetVersionExW);
    SBIEDLL_HOOK(UserEnv_, GetVersionExA);
    if (VerifyVersionInfoW) {
        *(ULONG_PTR *)&__sys_VerifyVersionInfoW = (ULONG_PTR)
            SbieDll_Hook("VerifyVersionInfoW", VerifyVersionInfoW,
                UserEnv_VerifyVersionInfoW, module);
        if (!__sys_VerifyVersionInfoW)
            return FALSE;
    }

    return TRUE;
}


//---------------------------------------------------------------------------
// UserEnv_Init
//---------------------------------------------------------------------------


_FX BOOLEAN UserEnv_Init(HMODULE module)
{
    ANSI_STRING ansi;
    NTSTATUS status;
    void *RegisterGPNotification;
    void *UnregisterGPNotification;
    void *GetAppliedGPOList;
    void* CreateAppContainerProfile;

    if (module == Dll_KernelBase) {

        //
        // on Windows 8.1, UserEnv!GetAppliedGPOList calls
        // KernelBase!GetAppliedGPOListInternalW, which just hangs
        //

        GetAppliedGPOList = (P_GetAppliedGPOList)
            GetProcAddress(module, "GetAppliedGPOListInternalW");

        SBIEDLL_HOOK(UserEnv_,GetAppliedGPOList);

    } else {

        //
        // hook UserEnv entrypoints
        //

        RegisterGPNotification = (P_RegisterGPNotification)
            GetProcAddress(module, "RegisterGPNotification");

        UnregisterGPNotification = (P_UnregisterGPNotification)
            GetProcAddress(module, "UnregisterGPNotification");

        SBIEDLL_HOOK(UserEnv_,RegisterGPNotification);
        SBIEDLL_HOOK(UserEnv_,UnregisterGPNotification);
    }

    if (!Dll_CompartmentMode) // see Proc_UpdateProcThreadAttribute
    if (Dll_OsBuild >= 9200) // Windows 8 and later
    {
        RtlInitString(&ansi, "CreateAppContainerProfile");
        status = LdrGetProcedureAddress(
            module, &ansi, 0, (void**)&CreateAppContainerProfile);
        if (NT_SUCCESS(status))
            SBIEDLL_HOOK(UserEnv_, CreateAppContainerProfile);
    }

    return TRUE;
}


//---------------------------------------------------------------------------
// UserEnv_RegisterGPNotification
//---------------------------------------------------------------------------


_FX BOOL UserEnv_RegisterGPNotification(HANDLE hEvent, BOOL bMachine)
{
    SetLastError(ERROR_SUCCESS);
    return TRUE;
}


//---------------------------------------------------------------------------
// UserEnv_RegisterGPNotification
//---------------------------------------------------------------------------


_FX BOOL UserEnv_UnregisterGPNotification(HANDLE hEvent)
{
    SetLastError(ERROR_SUCCESS);
    return TRUE;
}


//---------------------------------------------------------------------------
// UserEnv_GetAppliedGPOList
//---------------------------------------------------------------------------


ULONG UserEnv_GetAppliedGPOList(
    ULONG dwFlags, const WCHAR *pMachineName, PSID pSidUser,
    GUID *pGuidExtension, void *ppGPOList)
{
    // emulate error return code from KernelBase!GetAppliedGPOListInternalW
    SetLastError(ERROR_INVALID_FUNCTION);
    return ERROR_PROC_NOT_FOUND;
}

//---------------------------------------------------------------------------
// UserEnv_RtlGetVersion
//---------------------------------------------------------------------------

_FX void UserEnv_MkVersionEx(DWORD* dwBuildNumber, DWORD* dwMajorVersion, DWORD* dwMinorVersion, WORD* wServicePackMajor, WORD* wServicePackMinor)
{
    *dwBuildNumber = UserEnv_dwBuildNumber;
    *wServicePackMajor = 0;
    *wServicePackMinor = 0;

    if (UserEnv_dwBuildNumber <= 2600) { // xp sp3
        *dwMajorVersion = 5;
        *dwMinorVersion = 1;
        *wServicePackMajor = 3;
    }
    else if (UserEnv_dwBuildNumber <= 3790) { // 2003 sp2
        *dwMajorVersion = 5;
        *dwMinorVersion = 2;
        *wServicePackMajor = 2;
    }
    else if (UserEnv_dwBuildNumber <= 6000) { // vista
        *dwMajorVersion = 6;
        *dwMinorVersion = 0;
    }
    else if (UserEnv_dwBuildNumber <= 6001) { // vista sp1
        *dwMajorVersion = 6;
        *dwMinorVersion = 0;
        *wServicePackMajor = 1;
    }
    else if (UserEnv_dwBuildNumber <= 6002) { // vista sp2
        *dwMajorVersion = 6;
        *dwMinorVersion = 0;
        *wServicePackMajor = 2;
    }
    else if (UserEnv_dwBuildNumber <= 7600) { // 7
        *dwMajorVersion = 6;
        *dwMinorVersion = 1;
    }
    else if (UserEnv_dwBuildNumber <= 7601) { // 7 sp1
        *dwMajorVersion = 6;
        *dwMinorVersion = 1;
        *wServicePackMajor = 1;
    }
    else if (UserEnv_dwBuildNumber <= 9200) { // 8
        *dwMajorVersion = 6;
        *dwMinorVersion = 2;
    }
    else if (UserEnv_dwBuildNumber <= 9600) { // 8.1
        *dwMajorVersion = 6;
        *dwMinorVersion = 3;
    }
    else { // windows 10
        *dwMajorVersion = 10;
        *dwMinorVersion = 0;
    }
}

_FX NTSTATUS UserEnv_RtlGetVersion(LPOSVERSIONINFOEXW lpVersionInfo)
{
    NTSTATUS status = __sys_RtlGetVersion(lpVersionInfo);

    if (UserEnv_dwBuildNumber) {
        UserEnv_MkVersionEx(&lpVersionInfo->dwBuildNumber,
            &lpVersionInfo->dwMajorVersion, &lpVersionInfo->dwMinorVersion,
            &lpVersionInfo->wServicePackMajor, &lpVersionInfo->wServicePackMinor);
    }

    return status;
}

//---------------------------------------------------------------------------
// UserEnv_GetVersionExW
//---------------------------------------------------------------------------

_FX BOOL UserEnv_GetVersionExW(LPOSVERSIONINFOEXW lpVersionInfo)
{
    UserEnv_RtlGetVersion(lpVersionInfo);

    // RtlGetVersion always returns STATUS_SUCCESS
    return TRUE;
}

_FX BOOL UserEnv_GetVersionExA(LPOSVERSIONINFOEXA lpVersionInfo)
{
    BOOL rc;
    rc = __sys_GetVersionExA(lpVersionInfo);
    lpVersionInfo->dwMajorVersion = GET_PEB_MAJOR_VERSION;
    lpVersionInfo->dwMinorVersion = GET_PEB_MINOR_VERSION;

    if (UserEnv_dwBuildNumber) {
        UserEnv_MkVersionEx(&lpVersionInfo->dwBuildNumber, 
            &lpVersionInfo->dwMajorVersion, &lpVersionInfo->dwMinorVersion,
            &lpVersionInfo->wServicePackMajor, &lpVersionInfo->wServicePackMinor);
    }

    return rc;
}


//---------------------------------------------------------------------------
// UserEnv_VerifyVersionInfoW
//---------------------------------------------------------------------------


static BOOLEAN UserEnv_GetVersionCondition(
    DWORD TypeMask,
    DWORDLONG ConditionMask,
    BYTE *Condition)
{
    DWORDLONG fieldMask = 0;
    BYTE i;

    if (!__sys_VerSetConditionMask)
        return FALSE;

    for (i = VER_EQUAL; i <= VER_OR; ++i)
        fieldMask |= __sys_VerSetConditionMask(0, TypeMask, i);

    ConditionMask &= fieldMask;

    for (i = VER_EQUAL; i <= VER_OR; ++i) {
        if (ConditionMask == __sys_VerSetConditionMask(0, TypeMask, i)) {
            *Condition = i;
            return TRUE;
        }
    }

    return FALSE;
}


static BOOLEAN UserEnv_CompareVersionValue(
    DWORD Current,
    DWORD Required,
    BYTE Condition)
{
    switch (Condition) {
    case VER_EQUAL:
        return Current == Required;
    case VER_GREATER:
        return Current > Required;
    case VER_GREATER_EQUAL:
        return Current >= Required;
    case VER_LESS:
        return Current < Required;
    case VER_LESS_EQUAL:
        return Current <= Required;
    }

    return FALSE;
}


static BOOLEAN UserEnv_IsVersionValueCondition(BYTE Condition)
{
    return (Condition >= VER_EQUAL && Condition <= VER_LESS_EQUAL);
}


static BOOLEAN UserEnv_CompareVersionSuite(
    WORD Current,
    WORD Required,
    BYTE Condition)
{
    switch (Condition) {
    case VER_AND:
        return (Current & Required) == Required;
    case VER_OR:
        return (Current & Required) != 0;
    }

    return FALSE;
}


static BOOLEAN UserEnv_VerifyOneVersionField(
    DWORD Current,
    DWORD Required,
    DWORD TypeMask,
    DWORDLONG ConditionMask,
    BYTE *Condition,
    BOOLEAN *Different,
    BOOLEAN *InvalidParameter)
{
    if (!UserEnv_GetVersionCondition(TypeMask, ConditionMask, Condition))
        *InvalidParameter = TRUE;
    else if (!UserEnv_IsVersionValueCondition(*Condition))
        *InvalidParameter = TRUE;

    if (*InvalidParameter)
        return FALSE;

    if (!UserEnv_CompareVersionValue(Current, Required, *Condition))
        return FALSE;

    *Different = (Current != Required);
    return TRUE;
}


static BOOLEAN UserEnv_VerifyVersionNumbers(
    const OSVERSIONINFOEXW *CurrentVersion,
    const OSVERSIONINFOEXW *RequiredVersion,
    DWORD TypeMask,
    DWORDLONG ConditionMask,
    BOOLEAN *InvalidParameter)
{
    BYTE condition;
    BOOLEAN different;

    if (TypeMask & VER_MAJORVERSION) {
        if (!UserEnv_VerifyOneVersionField(
                CurrentVersion->dwMajorVersion, RequiredVersion->dwMajorVersion,
                VER_MAJORVERSION, ConditionMask, &condition, &different,
                InvalidParameter))
            return FALSE;
        if (different)
            return TRUE;
    }

    if (TypeMask & VER_MINORVERSION) {
        if (!UserEnv_VerifyOneVersionField(
                CurrentVersion->dwMinorVersion, RequiredVersion->dwMinorVersion,
                VER_MINORVERSION, ConditionMask, &condition, &different,
                InvalidParameter))
            return FALSE;
        if (different)
            return TRUE;
    }

    if (TypeMask & VER_SERVICEPACKMAJOR) {
        if (!UserEnv_VerifyOneVersionField(
                CurrentVersion->wServicePackMajor,
                RequiredVersion->wServicePackMajor,
                VER_SERVICEPACKMAJOR, ConditionMask, &condition, &different,
                InvalidParameter))
            return FALSE;
        if (different)
            return TRUE;
    }

    if (TypeMask & VER_SERVICEPACKMINOR) {
        if (!UserEnv_VerifyOneVersionField(
                CurrentVersion->wServicePackMinor,
                RequiredVersion->wServicePackMinor,
                VER_SERVICEPACKMINOR, ConditionMask, &condition, &different,
                InvalidParameter))
            return FALSE;
    }

    return TRUE;
}


_FX BOOL UserEnv_VerifyVersionInfoW(
    LPOSVERSIONINFOEXW lpVersionInformation,
    DWORD dwTypeMask,
    DWORDLONG dwlConditionMask)
{
    OSVERSIONINFOEXW CurrentVersion;
    NTSTATUS status;
    BYTE condition;
    BOOLEAN invalidParameter = FALSE;
    const DWORD SupportedTypeMask =
        VER_BUILDNUMBER | VER_MAJORVERSION | VER_MINORVERSION |
        VER_PLATFORMID | VER_SERVICEPACKMAJOR | VER_SERVICEPACKMINOR |
        VER_SUITENAME | VER_PRODUCT_TYPE;

    if (!UserEnv_dwBuildNumber || !__sys_VerSetConditionMask)
        return __sys_VerifyVersionInfoW(
            lpVersionInformation, dwTypeMask, dwlConditionMask);

    if (!lpVersionInformation ||
            lpVersionInformation->dwOSVersionInfoSize !=
                sizeof(OSVERSIONINFOEXW) ||
            !dwTypeMask ||
            (dwTypeMask & ~SupportedTypeMask)) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }

    memzero(&CurrentVersion, sizeof(CurrentVersion));
    CurrentVersion.dwOSVersionInfoSize = sizeof(CurrentVersion);

    status = __sys_RtlGetVersion(&CurrentVersion);
    if (!NT_SUCCESS(status)) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }

    UserEnv_MkVersionEx(
        &CurrentVersion.dwBuildNumber,
        &CurrentVersion.dwMajorVersion,
        &CurrentVersion.dwMinorVersion,
        &CurrentVersion.wServicePackMajor,
        &CurrentVersion.wServicePackMinor);

    if (!UserEnv_VerifyVersionNumbers(
            &CurrentVersion, lpVersionInformation,
            dwTypeMask, dwlConditionMask, &invalidParameter)) {
        if (invalidParameter)
            goto invalid_parameter;
        goto old_version;
    }

    if (dwTypeMask & VER_BUILDNUMBER) {
        if (!UserEnv_GetVersionCondition(
                VER_BUILDNUMBER, dwlConditionMask, &condition))
            goto invalid_parameter;
        if (!UserEnv_IsVersionValueCondition(condition))
            goto invalid_parameter;
        if (!UserEnv_CompareVersionValue(
                CurrentVersion.dwBuildNumber,
                lpVersionInformation->dwBuildNumber, condition))
            goto old_version;
    }

    if (dwTypeMask & VER_PLATFORMID) {
        if (!UserEnv_GetVersionCondition(
                VER_PLATFORMID, dwlConditionMask, &condition))
            goto invalid_parameter;
        if (!UserEnv_IsVersionValueCondition(condition))
            goto invalid_parameter;
        if (!UserEnv_CompareVersionValue(
                CurrentVersion.dwPlatformId,
                lpVersionInformation->dwPlatformId, condition))
            goto old_version;
    }

    if (dwTypeMask & VER_PRODUCT_TYPE) {
        if (!UserEnv_GetVersionCondition(
                VER_PRODUCT_TYPE, dwlConditionMask, &condition))
            goto invalid_parameter;
        if (!UserEnv_IsVersionValueCondition(condition))
            goto invalid_parameter;
        if (!UserEnv_CompareVersionValue(
                CurrentVersion.wProductType,
                lpVersionInformation->wProductType, condition))
            goto old_version;
    }

    if (dwTypeMask & VER_SUITENAME) {
        if (!UserEnv_GetVersionCondition(
                VER_SUITENAME, dwlConditionMask, &condition))
            goto invalid_parameter;
        if (condition != VER_AND && condition != VER_OR)
            goto invalid_parameter;
        if (!UserEnv_CompareVersionSuite(
                CurrentVersion.wSuiteMask,
                lpVersionInformation->wSuiteMask, condition))
            goto old_version;
    }

    return TRUE;

invalid_parameter:
    SetLastError(ERROR_INVALID_PARAMETER);
    return FALSE;

old_version:
    SetLastError(ERROR_OLD_WIN_VERSION);
    return FALSE;
}


//---------------------------------------------------------------------------
// UserEnv_CreateAppContainerProfile
//---------------------------------------------------------------------------


_FX HRESULT UserEnv_CreateAppContainerProfile(
    PCWSTR              pszAppContainerName,
    PCWSTR              pszDisplayName,
    PCWSTR              pszDescription,
    PSID_AND_ATTRIBUTES pCapabilities,
    DWORD               dwCapabilityCount,
    PSID                *ppSidAppContainer)
{
  //  HRESULT hr = __sys_CreateAppContainerProfile(
  //      pszAppContainerName,
  //      pszDisplayName,
  //      pszDescription,
  //      pCapabilities,
  //      dwCapabilityCount,
  //      ppSidAppContainerSid);

    if (!ppSidAppContainer)
        return E_POINTER;

    *ppSidAppContainer = NULL;

    // Build a SID that resembles an AppContainer SID: S-1-15-2-<a>-<b>-<c>-<d>
    // SID layout:
    //  - Revision = 1
    //  - IdentifierAuthority = SECURITY_APP_PACKAGE_AUTHORITY (0,0,0,0,0,15)
    //  - SubAuthorities: [2, 0x11111111, 0x22222222, 0x33333333, 0x44444444]
    #define revision SID_REVISION        // 1
    #define subAuthCount 5
    const DWORD subAuth[subAuthCount] = {
        2,              // AppContainer base RID (matches S-1-15-2-...)
        0x11111111,
        0x22222222,
        0x33333333,
        0x44444444
    };

    // IdentifierAuthority is 6 bytes big-endian; value 15 => {0,0,0,0,0,15}
    SID_IDENTIFIER_AUTHORITY appPkgAuthority = { 0, 0, 0, 0, 0, 15 };

    // Allocate enough memory for SID header + N subauthorities
    const SIZE_T sidSize = sizeof(SID) + (subAuthCount - 1) * sizeof(DWORD);

    PSID sid = (PSID)LocalAlloc(LMEM_FIXED, sidSize);
    if (!sid)
        return HRESULT_FROM_WIN32(ERROR_OUTOFMEMORY);

    // Manually populate the SID structure
    SID* s = (SID*)sid;
    s->Revision = revision;
    s->SubAuthorityCount = subAuthCount;
    s->IdentifierAuthority = appPkgAuthority;
    for (BYTE i = 0; i < subAuthCount; ++i)
        s->SubAuthority[i] = subAuth[i];

    *ppSidAppContainer = sid;
    return S_OK;
}
