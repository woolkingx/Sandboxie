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
// Cryptography
//---------------------------------------------------------------------------

#include "dll.h"

#include <windows.h>
#include <wincrypt.h>
#include "core/svc/ComWire.h"



//---------------------------------------------------------------------------
// Functions
//---------------------------------------------------------------------------


static void Crypt_InitPromptData(
    COM_CRYPT_PROTECT_DATA_REQ *req,
    CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct);

static BOOL Crypt_CryptUnprotectData(
    DATA_BLOB *pDataIn, LPWSTR *ppszDataDescr, DATA_BLOB *pOptionalEntropy,
    PVOID pvReserved, CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct,
    DWORD dwFlags, DATA_BLOB *pDataOut);

static BOOL Crypt_CryptProtectData(
    DATA_BLOB *pDataIn, LPCWSTR szDataDescr, DATA_BLOB *pOptionalEntropy,
    PVOID pvReserved, CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct,
    DWORD dwFlags, DATA_BLOB *pDataOut);

static BOOL Crypt_CertGetCertificateChain(
    ULONG_PTR hChainEngine, ULONG_PTR pCertContext, ULONG_PTR pTime,
    ULONG_PTR hAdditionalStore, ULONG_PTR pChainPara, ULONG dwFlags,
    ULONG_PTR pvReserved, ULONG_PTR ppChainContext);

#ifdef _WIN64

static int Crypt_GetKeyStorageInterface(void * a, void *buffer, void* c);
typedef int (*P_GetKeyStorageInterface) (void * a, void *buffer, void * c);
static P_GetKeyStorageInterface __sys_GetKeyStorageInterface = NULL;

static void Crypt_CryptClassErrorHandler(ULONG_PTR a);
typedef void (*P_CryptClassErrorHandler) (ULONG_PTR a);
static P_CryptClassErrorHandler __sys_CryptClassErrorHandler;

#endif // _WIN64

//---------------------------------------------------------------------------

typedef BOOL (*P_CryptUnprotectData)(
    DATA_BLOB *pDataIn, LPWSTR *ppszDataDescr, DATA_BLOB *pOptionalEntropy,
    PVOID pvReserved, CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct,
    DWORD dwFlags, DATA_BLOB *pDataOut);

typedef BOOL (*P_CryptProtectData)(
    DATA_BLOB *pDataIn, LPCWSTR szDataDescr, DATA_BLOB *pOptionalEntropy,
    PVOID pvReserved, CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct,
    DWORD dwFlags, DATA_BLOB *pDataOut);

typedef BOOL (*P_CertGetCertificateChain)(
    ULONG_PTR hChainEngine, ULONG_PTR pCertContext, ULONG_PTR pTime,
    ULONG_PTR hAdditionalStore, ULONG_PTR pChainPara, ULONG dwFlags,
    ULONG_PTR pvReserved, ULONG_PTR ppChainContext);


//---------------------------------------------------------------------------


static P_CryptUnprotectData         __sys_CryptUnprotectData        = NULL;
static P_CryptProtectData           __sys_CryptProtectData          = NULL;
static P_CertGetCertificateChain    __sys_CertGetCertificateChain   = NULL;


//---------------------------------------------------------------------------
// Variables
//---------------------------------------------------------------------------


static BOOLEAN Crypt_CallSbieSvc = FALSE;


//---------------------------------------------------------------------------
// Crypt_AddUlong
//---------------------------------------------------------------------------


_FX BOOLEAN Crypt_AddUlong(ULONG Value, ULONG Addend, ULONG *Result)
{
    if (Value > (~0u - Addend))
        return FALSE;

    *Result = Value + Addend;
    return TRUE;
}


//---------------------------------------------------------------------------
// Crypt_WcharsToBytesWithNull
//---------------------------------------------------------------------------


_FX BOOLEAN Crypt_WcharsToBytesWithNull(ULONG Chars, ULONG *Bytes)
{
    if (Chars > ((~0u / sizeof(WCHAR)) - 1))
        return FALSE;

    *Bytes = (Chars + 1) * sizeof(WCHAR);
    return TRUE;
}


//---------------------------------------------------------------------------
// Crypt_GetBlobLength
//---------------------------------------------------------------------------


_FX BOOLEAN Crypt_GetBlobLength(DATA_BLOB *Blob, ULONG *Length)
{
    if (! Blob)
        return FALSE;

    if (Blob->cbData && (! Blob->pbData))
        return FALSE;

    *Length = Blob->cbData;
    return TRUE;
}


//---------------------------------------------------------------------------
// Crypt_GetOptionalBlobLength
//---------------------------------------------------------------------------


_FX BOOLEAN Crypt_GetOptionalBlobLength(DATA_BLOB *Blob, ULONG *Length)
{
    if (! Blob) {
        *Length = 0;
        return TRUE;
    }

    return Crypt_GetBlobLength(Blob, Length);
}


//---------------------------------------------------------------------------
// Crypt_ValidateReply
//---------------------------------------------------------------------------


_FX BOOLEAN Crypt_ValidateReply(
    COM_CRYPT_PROTECT_DATA_RPL *rpl, ULONG *data_len, ULONG *descr_len)
{
    ULONG rpl_len = rpl->h.length;
    ULONG offset = FIELD_OFFSET(COM_CRYPT_PROTECT_DATA_RPL, data);
    ULONG remaining;

    if (rpl_len < sizeof(COM_CRYPT_PROTECT_DATA_RPL))
        return FALSE;

    if (rpl_len < offset)
        return FALSE;

    remaining = rpl_len - offset;
    if (rpl->data_len > remaining)
        return FALSE;

    remaining -= rpl->data_len;
    if (rpl->descr_len > (remaining / sizeof(WCHAR)))
        return FALSE;

    *data_len = rpl->data_len;
    if (descr_len)
        *descr_len = rpl->descr_len;
    return TRUE;
}


//---------------------------------------------------------------------------
// Crypt_InitPromptData
//---------------------------------------------------------------------------


_FX void Crypt_InitPromptData(
    COM_CRYPT_PROTECT_DATA_REQ *req,
    CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct)
{
    if (pPromptStruct &&
            pPromptStruct->cbSize == sizeof(CRYPTPROTECT_PROMPTSTRUCT)) {

        req->prompt_flags = pPromptStruct->dwPromptFlags;
        req->prompt_hwnd  = (ULONG_PTR)pPromptStruct->hwndApp;

        if (pPromptStruct->szPrompt) {

            ULONG len =
                (wcslen(pPromptStruct->szPrompt) + 1) * sizeof(WCHAR);
            if (len > sizeof(req->prompt_text))
                len = sizeof(req->prompt_text);
            memcpy(req->prompt_text, pPromptStruct->szPrompt, len);

        } else
            req->prompt_text[0] = L'\0';

    } else {

        req->prompt_flags = 0;
        req->prompt_hwnd = 0;
        req->prompt_text[0] = L'\0';
    }

    //
    // if ComServer::CryptProtectDataSlave in the SbieSvc COM Proxy
    // wants to display UI through CryptProtectData/CryptUnprotectData,
    // we want to allow the dialog box to go to the foreground
    //

    Gui_AllowSetForegroundWindow();
}


//---------------------------------------------------------------------------
// Crypt_CryptUnprotectData
//---------------------------------------------------------------------------


_FX BOOL Crypt_CryptUnprotectData(
    DATA_BLOB *pDataIn, LPWSTR *ppszDataDescr, DATA_BLOB *pOptionalEntropy,
    PVOID pvReserved, CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct,
    DWORD dwFlags, DATA_BLOB *pDataOut)
{
    COM_CRYPT_PROTECT_DATA_REQ *req;
    COM_CRYPT_PROTECT_DATA_RPL *rpl;
    ULONG req_len;
    ULONG entropy_len;
    ULONG data_len;
    ULONG reply_data_len;
    ULONG reply_descr_len;
    ULONG descr_bytes;
    ULONG error;
    UCHAR *ptr;

    //
    // first try system procedure
    //

    if (! Crypt_CallSbieSvc) {

        BOOL ok = __sys_CryptUnprotectData(
            pDataIn, ppszDataDescr, pOptionalEntropy, pvReserved,
            pPromptStruct, dwFlags, pDataOut);
        if (ok || GetLastError() != RPC_S_SERVER_UNAVAILABLE)
            return ok;
    }

    Crypt_CallSbieSvc = TRUE;

    //
    // otherwise call SbieSvc decrypt service
    //

    if ((! pDataOut) ||
        (! Crypt_GetBlobLength(pDataIn, &data_len)) ||
        (! Crypt_GetOptionalBlobLength(pOptionalEntropy, &entropy_len))) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }

    req_len = sizeof(COM_CRYPT_PROTECT_DATA_REQ);
    if ((! Crypt_AddUlong(req_len, data_len, &req_len)) ||
        (! Crypt_AddUlong(req_len, entropy_len, &req_len))) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }

    req = (COM_CRYPT_PROTECT_DATA_REQ *)Dll_AllocTemp(req_len);
    if (! req) {
        SetLastError(ERROR_NOT_ENOUGH_MEMORY);
        return FALSE;
    }

    req->h.length = req_len;
    req->h.msgid = MSGID_COM_CRYPT_PROTECT_DATA;

    req->mode = L'U';
    req->flags = dwFlags;
    req->data_len = data_len;
    req->entropy_len = entropy_len;
    req->descr_len = 0;

    ptr = (UCHAR *)req->data;
    if (data_len)
        memcpy(ptr, pDataIn->pbData, data_len);
    if (entropy_len) {
        ptr += data_len;
        memcpy(ptr, pOptionalEntropy->pbData, entropy_len);
    }

    Crypt_InitPromptData(req, pPromptStruct);

    rpl = (COM_CRYPT_PROTECT_DATA_RPL *)
                                SbieDll_CallServer((MSG_HEADER *)req);
    Dll_Free(req);

    if (! rpl)
        error = RPC_S_SERVER_UNAVAILABLE;
    else
        error = rpl->h.status;

    if (error == 0) {

        if (! Crypt_ValidateReply(rpl, &reply_data_len, &reply_descr_len))
            error = ERROR_INVALID_PARAMETER;
    }

    if (error == 0) {

        pDataOut->pbData = NULL;
        pDataOut->cbData = reply_data_len;
        if (reply_data_len)
            pDataOut->pbData = LocalAlloc(LPTR, reply_data_len);

        if (reply_data_len && (! pDataOut->pbData))
            error = ERROR_NOT_ENOUGH_MEMORY;
        else {
            if (reply_data_len)
                memcpy(pDataOut->pbData, rpl->data, reply_data_len);

            if (ppszDataDescr) {

                *ppszDataDescr = NULL;
                if (! Crypt_WcharsToBytesWithNull(reply_descr_len, &descr_bytes))
                    error = ERROR_INVALID_PARAMETER;
                else {
                    *ppszDataDescr = LocalAlloc(LPTR, descr_bytes);
                    if (! *ppszDataDescr) {
                        if (pDataOut->pbData)
                            LocalFree(pDataOut->pbData);
                        pDataOut->pbData = NULL;
                        pDataOut->cbData = 0;
                        error = ERROR_NOT_ENOUGH_MEMORY;
                    } else {
                        wmemcpy(*ppszDataDescr,
                                (WCHAR*)(rpl->data + reply_data_len),
                                reply_descr_len);
                        (*ppszDataDescr)[reply_descr_len] = L'\0';
                    }
                }
            }
        }
    }

    if (rpl)
        Dll_Free(rpl);
    SetLastError(error);
    return (error == 0 ? TRUE : FALSE);
}


//---------------------------------------------------------------------------
// Crypt_CryptProtectData
//---------------------------------------------------------------------------


_FX BOOL Crypt_CryptProtectData(
    DATA_BLOB *pDataIn, LPCWSTR szDataDescr, DATA_BLOB *pOptionalEntropy,
    PVOID pvReserved, CRYPTPROTECT_PROMPTSTRUCT *pPromptStruct,
    DWORD dwFlags, DATA_BLOB *pDataOut)
{
    COM_CRYPT_PROTECT_DATA_REQ *req;
    COM_CRYPT_PROTECT_DATA_RPL *rpl;
    ULONG req_len;
    ULONG entropy_len;
    ULONG data_len;
    ULONG descr_len;
    ULONG descr_bytes;
    ULONG reply_data_len;
    ULONG error;
    UCHAR *ptr;
    size_t descr_len_size;

    //
    // first try system procedure
    //

    if (! Crypt_CallSbieSvc) {

        BOOL ok = __sys_CryptProtectData(
            pDataIn, szDataDescr, pOptionalEntropy, pvReserved,
            pPromptStruct, dwFlags, pDataOut);
        if (ok || GetLastError() != RPC_S_SERVER_UNAVAILABLE)
            return ok;
    }

    Crypt_CallSbieSvc = TRUE;

    //
    // otherwise call SbieSvc crypt service
    //

    if ((! pDataOut) ||
        (! Crypt_GetBlobLength(pDataIn, &data_len)) ||
        (! Crypt_GetOptionalBlobLength(pOptionalEntropy, &entropy_len))) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }

    if (szDataDescr)
        descr_len_size = wcslen(szDataDescr);
    else
        descr_len_size = 0;

    if (descr_len_size > ~0u) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }
    descr_len = (ULONG)descr_len_size;

    if (! Crypt_WcharsToBytesWithNull(descr_len, &descr_bytes)) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }

    req_len = sizeof(COM_CRYPT_PROTECT_DATA_REQ);
    if ((! Crypt_AddUlong(req_len, data_len, &req_len)) ||
        (! Crypt_AddUlong(req_len, entropy_len, &req_len)) ||
        (! Crypt_AddUlong(req_len, descr_bytes, &req_len))) {
        SetLastError(ERROR_INVALID_PARAMETER);
        return FALSE;
    }

    req = (COM_CRYPT_PROTECT_DATA_REQ *)Dll_AllocTemp(req_len);
    if (! req) {
        SetLastError(ERROR_NOT_ENOUGH_MEMORY);
        return FALSE;
    }

    req->h.length = req_len;
    req->h.msgid = MSGID_COM_CRYPT_PROTECT_DATA;

    req->mode = L'P';
    req->flags = dwFlags;
    req->data_len = data_len;
    req->entropy_len = entropy_len;
    req->descr_len = descr_len;

    ptr = (UCHAR *)req->data;
    if (data_len)
        memcpy(ptr, pDataIn->pbData, data_len);
    ptr += data_len;
    if (entropy_len) {
        memcpy(ptr, pOptionalEntropy->pbData, entropy_len);
        ptr += entropy_len;
    }
    if (szDataDescr)
        wmemcpy((WCHAR *)ptr, szDataDescr, descr_len + 1);

    Crypt_InitPromptData(req, pPromptStruct);

    rpl = (COM_CRYPT_PROTECT_DATA_RPL *)
                                SbieDll_CallServer((MSG_HEADER *)req);
    Dll_Free(req);

    if (! rpl)
        error = RPC_S_SERVER_UNAVAILABLE;
    else
        error = rpl->h.status;

    if (error == 0) {

        if (! Crypt_ValidateReply(rpl, &reply_data_len, NULL))
            error = ERROR_INVALID_PARAMETER;
    }

    if (error == 0) {

        pDataOut->pbData = NULL;
        pDataOut->cbData = reply_data_len;
        if (reply_data_len)
            pDataOut->pbData = LocalAlloc(LPTR, reply_data_len);

        if (reply_data_len && (! pDataOut->pbData))
            error = ERROR_NOT_ENOUGH_MEMORY;
        else {
            if (reply_data_len)
                memcpy(pDataOut->pbData, rpl->data, reply_data_len);
        }
    }

    if (rpl)
        Dll_Free(rpl);
    SetLastError(error);
    return (error == 0 ? TRUE : FALSE);
}


//---------------------------------------------------------------------------
// Crypt_CertGetCertificateChain
//---------------------------------------------------------------------------


_FX BOOL Crypt_CertGetCertificateChain(
    ULONG_PTR hChainEngine, ULONG_PTR pCertContext, ULONG_PTR pTime,
    ULONG_PTR hAdditionalStore, ULONG_PTR pChainPara, ULONG dwFlags,
    ULONG_PTR pvReserved, ULONG_PTR ppChainContext)
{
    //
    // if the function CRYPT32!WaitForCryptService detects the CryptSvc
    // service is not started yet, it will start the service and then
    // delays for a fixed length of five seconds.  to eliminate the delay,
    // we need to start the CryptSvc beforehand.  we hook this API because
    // it is used by WinVerifyTrust and ends up calling WaitForCryptService
    //

    BOOLEAN event_created = FALSE;
    HANDLE hEvent = Ipc_GetServerEvent(Scm_CryptSvc, &event_created);
    if (hEvent) {
        if (event_created)
            if (SbieDll_StartBoxedService(Scm_CryptSvc, FALSE))
                WaitForSingleObject(hEvent, 8 * 1000);
        CloseHandle(hEvent);
    }

    //
    // now call the system CertGetCertificateChain
    //

    return __sys_CertGetCertificateChain(
        hChainEngine, pCertContext, pTime, hAdditionalStore,
        pChainPara, dwFlags, pvReserved, ppChainContext);
}


//---------------------------------------------------------------------------
// Crypt_Init
//---------------------------------------------------------------------------


_FX BOOLEAN Crypt_Init(HMODULE module)
{
    void *CryptProtectData;
    void *CryptUnprotectData;
    void *CertGetCertificateChain;

    //
    // in app mode we have our original token so no need to hook this
    //

    if (Dll_CompartmentMode) 
        return TRUE;

    //
    // hook cryptography services
    //

    CryptProtectData = GetProcAddress(module, "CryptProtectData");
    CryptUnprotectData = GetProcAddress(module, "CryptUnprotectData");
    CertGetCertificateChain =
                        GetProcAddress(module, "CertGetCertificateChain");

    // Norton 360 toolbar can make the CryptProtectData export lookup fail on
    // Windows 8.  Treat that as a module-owned hook surface incompatibility:
    // skip Crypt32 hooks for that process instead of failing Crypt_Init.
    if ((! CryptProtectData) && (Dll_OsBuild >= 8400)
            //&& (Dll_ImageType == DLL_IMAGE_MOZILLA_FIREFOX)
            && GetModuleHandle(L"UMEngx86.dll")) {
        // on Windows 8 with Norton 360, and with the Norton toolbar
        // activated in Firefox, the GetProcAddress calls above fail,
        // so silently ignore that
        return TRUE;
    }

    SBIEDLL_HOOK(Crypt_,CryptProtectData);
    SBIEDLL_HOOK(Crypt_,CryptUnprotectData);
    SBIEDLL_HOOK(Crypt_,CertGetCertificateChain);

    return TRUE;
}

#ifdef _WIN64

typedef struct _KeyInterfaceClass
{
    ULONG_PTR header;
    void * KeyInterfaceConstructor;
    void * SPCryptOpenProvider;
    void * unknownClassFunction_2;
    void * unknownClassFunction_3;
    void * unknownClassFunction_4;
    void * unknownClassFunction_5;
    void * unknownClassFunction_6;
    void * unknownClassFunction_7;
    void * unknownClassFunction_8;
    void * ErrorHandler;
} KeyInterfaceClass;


void Crypt_CryptClassErrorHandler(ULONG_PTR classAddress)
{
    if (classAddress <= 2) {
        __sys_CryptClassErrorHandler(0);
    }
    else
        __sys_CryptClassErrorHandler(classAddress);
    return;
}


int Crypt_GetKeyStorageInterface(void * a, void *data, void *c)
{
    int rc;
    KeyInterfaceClass* ClassPtr;
    rc = __sys_GetKeyStorageInterface(a, data, c);

    if (data) {
        void * CryptClassErrorHandler;

        ClassPtr = (KeyInterfaceClass*)(*(ULONG_PTR *)data);
        if (__sys_CryptClassErrorHandler != ClassPtr->ErrorHandler) {
            HMODULE module = NULL; // fix-me: 
            CryptClassErrorHandler = (P_CryptClassErrorHandler)ClassPtr->ErrorHandler;
            SBIEDLL_HOOK(Crypt_, CryptClassErrorHandler);
        }
    }
    return rc;
}


_FX BOOLEAN NcryptProv_Init(HMODULE module)
{
    void * GetKeyStorageInterface;
    GetKeyStorageInterface = GetProcAddress(module, "GetKeyStorageInterface");

    if (GetKeyStorageInterface) {
        SBIEDLL_HOOK(Crypt_, GetKeyStorageInterface);
    }
    return TRUE;
}

#endif  // _WIN64
