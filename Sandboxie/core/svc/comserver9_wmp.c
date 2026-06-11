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
// Windows Media Player Server Hooking
//---------------------------------------------------------------------------


#include <shobjidl.h>
#include <shlobj.h>
#include <shellapi.h>


//---------------------------------------------------------------------------
// IExecuteCommand from Windows 7 ShObjIdl.h
//---------------------------------------------------------------------------



static HRESULT WMPServer_IExecuteCommand_SetKeyState(
    IExecuteCommand *This, DWORD grfKeyState);
static HRESULT WMPServer_IExecuteCommand_SetParameters(
    IExecuteCommand *This, LPCWSTR pszParameters);
static HRESULT WMPServer_IExecuteCommand_SetPosition(
    IExecuteCommand *This, POINT pt);
static HRESULT WMPServer_IExecuteCommand_SetShowWindow(
    IExecuteCommand *This, int nShow);
static HRESULT WMPServer_IExecuteCommand_SetNoShowUI(
    IExecuteCommand *This, BOOL fNoShowUI);
static HRESULT WMPServer_IExecuteCommand_SetDirectory(
    IExecuteCommand *This, LPCWSTR pszDirectory);
static HRESULT WMPServer_IExecuteCommand_Execute(
    IExecuteCommand *This);


//---------------------------------------------------------------------------
// IShellItemArray from Windows 7 ShObjIdl.h
//---------------------------------------------------------------------------




//---------------------------------------------------------------------------
// IObjectWithSelection from Windows 7 ShObjIdl.h
//---------------------------------------------------------------------------

static HRESULT WMPServer_IObjectWithSelection_SetSelection(
    IObjectWithSelection *This, IShellItemArray *psia);

static HRESULT WMPServer_IObjectWithSelection_GetSelection(
    IObjectWithSelection *This, REFIID riid, void **ppv);


//---------------------------------------------------------------------------
// IDropTarget
//---------------------------------------------------------------------------


static HRESULT WMPServer_IDropTarget_DragEnter(
    IDropTarget *This, IDataObject *pDataObject,
    DWORD grfKeyState, POINTL pt, DWORD *pdwEffect);

static HRESULT WMPServer_IDropTarget_DragOver(
    IDropTarget *This, DWORD grfKeyState, POINTL pt, DWORD *pdwEffect);

static HRESULT WMPServer_IDropTarget_DragLeave(IDropTarget *This);

static HRESULT WMPServer_IDropTarget_Drop(
    IDropTarget *This, IDataObject *pDataObject,
    DWORD grfKeyState, POINTL pt, DWORD *pdwEffect);


//---------------------------------------------------------------------------
// Functions
//---------------------------------------------------------------------------


static IMyUnknown *WMPServer_MyCreateInstance(REFIID riid);
static IMyUnknown *WMPServer_MyCreateInstanceHelper(void);
static void *WMPServer_MyQueryInterface(IMyUnknown *This, REFIID riid);
static BOOLEAN WMPServer_TryWcharBytes(SIZE_T chars, ULONG *bytes);
static void WMPServer_ClearParameters(void);
static HRESULT WMPServer_SetParametersCopy(LPCWSTR pszParameters);
static HRESULT WMPServer_AppendParameterPath(LPCWSTR path);


//---------------------------------------------------------------------------
// GUIDs
//---------------------------------------------------------------------------


// {ED1D0FDF-4414-470A-A56D-CFB68623FC58}
static const GUID CLSID_WindowsMediaPlayer_Play = {
    0xED1D0FDF, 0x4414, 0x470A,
        { 0xA5, 0x6D, 0xCF, 0xB6, 0x86, 0x23, 0xFC, 0x58 }
};

// {45597C98-80F6-4549-84FF-752CF55E2D29}
static const GUID CLSID_WindowsMediaPlayer_Enqueue = {
    0x45597C98, 0x80F6, 0x4549,
        { 0x84, 0xFF, 0x75, 0x2C, 0xF5, 0x5E, 0x2D, 0x29 }
};

// {46986115-84D6-459C-8F95-52DD653E532E}
static const GUID CLSID_WinAmp = {
    0x46986115, 0x84D6, 0x459C,
        { 0x8F, 0x95, 0x52, 0xDD, 0x65, 0x3E, 0x53, 0x2E }
};

// {9EB4C4CB-74C2-4BE9-AA5D-8249F16020AD}
static const GUID CLSID_KmPlayer = {
    0x9EB4C4CB, 0x74C2, 0x4BE9,
        { 0xAA, 0x5D, 0x82, 0x49, 0xF1, 0x60, 0x20, 0xAD }
};

// {7F9185B0-CB92-43C5-80A9-92277A4F7B54}
static const GUID IID_IExecuteCommand = {
    0x7F9185B0, 0xCB92, 0x43C5,
        { 0x80, 0xA9, 0x92, 0x27, 0x7A, 0x4F, 0x7B, 0x54 }
};

// {1C9CD5BB-98E9-4491-A60F-31AACC72B83C}
static const GUID IID_IObjectWithSelection = {
    0x1C9CD5BB, 0x98E9, 0x4491,
        { 0xA6, 0x0F, 0x31, 0xAA, 0xCC, 0x72, 0xB8, 0x3C }
};


//---------------------------------------------------------------------------
// Variables
//---------------------------------------------------------------------------


static WCHAR *WMPServer_Parameters = NULL;


//---------------------------------------------------------------------------
// WMPServer_TryWcharBytes
//---------------------------------------------------------------------------


_FX BOOLEAN WMPServer_TryWcharBytes(SIZE_T chars, ULONG *bytes)
{
    if (chars > ((ULONG)-1) / sizeof(WCHAR))
        return FALSE;

    *bytes = (ULONG)(chars * sizeof(WCHAR));
    return TRUE;
}


//---------------------------------------------------------------------------
// WMPServer_ClearParameters
//---------------------------------------------------------------------------


_FX void WMPServer_ClearParameters(void)
{
    if (WMPServer_Parameters) {
        HeapFree(GetProcessHeap(), 0, WMPServer_Parameters);
        WMPServer_Parameters = NULL;
    }
}


//---------------------------------------------------------------------------
// WMPServer_SetParametersCopy
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_SetParametersCopy(LPCWSTR pszParameters)
{
    SIZE_T len, trim;
    ULONG bytes;
    WCHAR *params;

    WMPServer_ClearParameters();

    if (! pszParameters)
        return S_OK;

    len = wcslen(pszParameters);
    trim = 0;
    while (trim < len && pszParameters[trim] == L' ')
        ++trim;

    len -= trim;
    if (! len)
        return S_OK;

    if (! WMPServer_TryWcharBytes(len + 1, &bytes))
        return E_OUTOFMEMORY;

    params = Dll_Alloc(bytes);
    wmemcpy(params, pszParameters + trim, len);
    params[len] = L'\0';

    WMPServer_Parameters = params;
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_AppendParameterPath
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_AppendParameterPath(LPCWSTR path)
{
    SIZE_T param_len;
    SIZE_T path_len;
    SIZE_T chars;
    ULONG bytes;
    WCHAR *params, *ptr;

    if (! path)
        return E_INVALIDARG;

    param_len = WMPServer_Parameters ? wcslen(WMPServer_Parameters) : 0;
    path_len = wcslen(path);
    chars = param_len + path_len + 4;
    if (chars < param_len || chars < path_len)
        return E_OUTOFMEMORY;
    if (! WMPServer_TryWcharBytes(chars, &bytes))
        return E_OUTOFMEMORY;

    params = Dll_Alloc(bytes);
    ptr = params;

    if (WMPServer_Parameters) {
        wmemcpy(ptr, WMPServer_Parameters, param_len);
        ptr += param_len;
        *ptr++ = L' ';
    }

    *ptr++ = L'\"';
    wmemcpy(ptr, path, path_len);
    ptr += path_len;
    *ptr++ = L'\"';
    *ptr = L'\0';

    WMPServer_ClearParameters();
    WMPServer_Parameters = params;
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_MyCreateInstance
//---------------------------------------------------------------------------


_FX IMyUnknown *WMPServer_MyCreateInstance(REFIID riid)
{
    if (IsEqualIID(riid, &IID_IUnknown)             ||
        IsEqualIID(riid, &IID_IExecuteCommand)      ||
        IsEqualIID(riid, &IID_IObjectWithSelection) ||
        0) {

        return WMPServer_MyCreateInstanceHelper();
    }

    if (ComServer_ImageType == ComServer_ImageType_WINAMP ||
        ComServer_ImageType == ComServer_ImageType_KMPLAYER) {

        if (IsEqualIID(riid, &IID_IDropTarget)) {

            return WMPServer_MyCreateInstanceHelper();
        }
    }

    return NULL;
}


//---------------------------------------------------------------------------
// WMPServer_MyCreateInstanceHelper
//---------------------------------------------------------------------------


_FX IMyUnknown *WMPServer_MyCreateInstanceHelper(void)
{
    ULONG SizeofVtbls;
    IMyUnknown *This;
    ULONG_PTR *ptr;

    SizeofVtbls = 0
        + sizeof(ULONG_PTR) + sizeof(IExecuteCommandVtbl)
        + sizeof(ULONG_PTR) + sizeof(IObjectWithSelectionVtbl)
        + sizeof(ULONG_PTR) + sizeof(IDropTargetVtbl);

    This = ComServer_MyUnknown_New(WMPServer_MyQueryInterface, SizeofVtbls);

    ptr = (ULONG_PTR *)&This->VtblSpace;

    *ptr = (ULONG_PTR)This;
    ++ptr;
    This->Vtbls[1] = (ULONG_PTR)ptr;
    ptr[0] = (ULONG_PTR)ComServer_IUnknown_QueryInterface;
    ptr[1] = (ULONG_PTR)ComServer_IUnknown_AddRef;
    ptr[2] = (ULONG_PTR)ComServer_IUnknown_Release;
    ptr[3] = (ULONG_PTR)WMPServer_IExecuteCommand_SetKeyState;
    ptr[4] = (ULONG_PTR)WMPServer_IExecuteCommand_SetParameters;
    ptr[5] = (ULONG_PTR)WMPServer_IExecuteCommand_SetPosition;
    ptr[6] = (ULONG_PTR)WMPServer_IExecuteCommand_SetShowWindow;
    ptr[7] = (ULONG_PTR)WMPServer_IExecuteCommand_SetNoShowUI;
    ptr[8] = (ULONG_PTR)WMPServer_IExecuteCommand_SetDirectory;
    ptr[9] = (ULONG_PTR)WMPServer_IExecuteCommand_Execute;
    ptr += sizeof(IExecuteCommandVtbl) / sizeof(ULONG_PTR);

    *ptr = (ULONG_PTR)This;
    ++ptr;
    This->Vtbls[2] = (ULONG_PTR)ptr;
    ptr[0] = (ULONG_PTR)ComServer_IUnknown_QueryInterface;
    ptr[1] = (ULONG_PTR)ComServer_IUnknown_AddRef;
    ptr[2] = (ULONG_PTR)ComServer_IUnknown_Release;
    ptr[3] = (ULONG_PTR)WMPServer_IObjectWithSelection_SetSelection;
    ptr[4] = (ULONG_PTR)WMPServer_IObjectWithSelection_GetSelection;
    ptr += sizeof(IObjectWithSelectionVtbl) / sizeof(ULONG_PTR);

    *ptr = (ULONG_PTR)This;
    ++ptr;
    This->Vtbls[3] = (ULONG_PTR)ptr;
    ptr[0] = (ULONG_PTR)ComServer_IUnknown_QueryInterface;
    ptr[1] = (ULONG_PTR)ComServer_IUnknown_AddRef;
    ptr[2] = (ULONG_PTR)ComServer_IUnknown_Release;
    ptr[3] = (ULONG_PTR)WMPServer_IDropTarget_DragEnter;
    ptr[4] = (ULONG_PTR)WMPServer_IDropTarget_DragOver;
    ptr[5] = (ULONG_PTR)WMPServer_IDropTarget_DragLeave;
    ptr[6] = (ULONG_PTR)WMPServer_IDropTarget_Drop;
    ptr += sizeof(IDropTargetVtbl) / sizeof(ULONG_PTR);

    return This;
}



//---------------------------------------------------------------------------
// WMPServer_MyQueryInterface
//---------------------------------------------------------------------------


_FX void *WMPServer_MyQueryInterface(IMyUnknown *This, REFIID riid)
{
    if (IsEqualIID(riid, &IID_IUnknown))
        return (void *)&This->Vtbls[0];

    if (IsEqualIID(riid, &IID_IExecuteCommand))
        return (void *)&This->Vtbls[1];

    if (IsEqualIID(riid, &IID_IObjectWithSelection))
        return (void *)&This->Vtbls[2];

    if (ComServer_ImageType == ComServer_ImageType_WINAMP ||
        ComServer_ImageType == ComServer_ImageType_KMPLAYER) {

        if (IsEqualIID(riid, &IID_IDropTarget))
            return (void *)&This->Vtbls[3];
    }

    return NULL;
}


//---------------------------------------------------------------------------
// WMPServer_IExecuteCommand_SetKeyState
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IExecuteCommand_SetKeyState(
    IExecuteCommand *This, DWORD grfKeyState)
{
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IExecuteCommand_SetParameters
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IExecuteCommand_SetParameters(
    IExecuteCommand *This, LPCWSTR pszParameters)
{
    HRESULT hr = WMPServer_SetParametersCopy(pszParameters);
    if (FAILED(hr))
        return hr;

#ifdef COMSERVER_DEBUG
    { WCHAR txt[128];
    swprintf(txt, L"WMPServer_IExecuteCommand_SetParameters - <%s>\n", WMPServer_Parameters);
    OutputDebugString(txt); }
#endif

    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IExecuteCommand_SetPosition
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IExecuteCommand_SetPosition(
    IExecuteCommand *This, POINT pt)
{
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IExecuteCommand_SetShowWindow
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IExecuteCommand_SetShowWindow(
    IExecuteCommand *This, int nShow)
{
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IExecuteCommand_SetNoShowUI
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IExecuteCommand_SetNoShowUI(
    IExecuteCommand *This, BOOL fNoShowUI)
{
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IExecuteCommand_SetDirectory
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IExecuteCommand_SetDirectory(
    IExecuteCommand *This, LPCWSTR pszDirectory)
{
#ifdef COMSERVER_DEBUG
    WCHAR txt[128];
    swprintf(txt, L"WMPServer_IExecuteCommand_SetDirectory - <%s>\n", pszDirectory);
    OutputDebugString(txt);
#endif

    if (pszDirectory)
        SetCurrentDirectory(pszDirectory);
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IExecuteCommand_Execute
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IExecuteCommand_Execute(
    IExecuteCommand *This)
{
    WCHAR *arg = WMPServer_Parameters;
    if (! arg)
        arg = L"";

    if (wcslen(arg) > 1 && arg[wcslen(arg) - 1] == L'\"')
        arg[wcslen(arg) - 1] = L'\0';
    if (*arg == L'\"')
        ++arg;

    ComServer_RestartProgram(arg);

    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IObjectWithSelection_SetSelection
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IObjectWithSelection_SetSelection(
    IObjectWithSelection *This, IShellItemArray *psia)
{
    ULONG index = 0;
    HRESULT hr;

    if (! psia)
        return E_POINTER;

    while (1) {

        WCHAR *path1 = NULL;

        IShellItem *pShellItem;
        hr = psia->lpVtbl->GetItemAt(psia, index, &pShellItem);
        if (FAILED(hr))
            break;
        ++index;

        hr = IShellItem_GetDisplayName(pShellItem, SIGDN_FILESYSPATH, &path1);
        if (SUCCEEDED(hr) && path1) {
            hr = WMPServer_AppendParameterPath(path1);
            CoTaskMemFree(path1);
            if (FAILED(hr)) {
                IShellItem_Release(pShellItem);
                return hr;
            }
        }

        IShellItem_Release(pShellItem);
    }

#ifdef COMSERVER_DEBUG
    { WCHAR txt[512];
    swprintf(txt, L"WMPServer_IObjectWithSelection_SetSelection - <%s>\n", WMPServer_Parameters);
    OutputDebugString(txt); }
#endif

    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IObjectWithSelection_GetSelection
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IObjectWithSelection_GetSelection(
    IObjectWithSelection *This, REFIID riid, void **ppv)
{
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IDropTarget_DragEnter
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IDropTarget_DragEnter(
    IDropTarget *This, IDataObject *pDataObject,
    DWORD grfKeyState, POINTL pt, DWORD *pdwEffect)
{
    if (! pdwEffect)
        return E_POINTER;

#ifdef COMSERVER_DEBUG
    { OutputDebugString(L"WMPServer_IDropTarget_DragEnter\n"); }
#endif
    *pdwEffect = DROPEFFECT_COPY;
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IDropTarget_DragOver
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IDropTarget_DragOver(
    IDropTarget *This, DWORD grfKeyState, POINTL pt, DWORD *pdwEffect)
{
    if (! pdwEffect)
        return E_POINTER;

#ifdef COMSERVER_DEBUG
    { OutputDebugString(L"WMPServer_IDropTarget_DragOver\n"); }
#endif
    *pdwEffect = DROPEFFECT_COPY;
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IDropTarget_DragLeave
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IDropTarget_DragLeave(IDropTarget *This)
{
#ifdef COMSERVER_DEBUG
    { OutputDebugString(L"WMPServer_IDropTarget_DragLeave\n"); }
#endif
    return S_OK;
}


//---------------------------------------------------------------------------
// WMPServer_IDropTarget_Drop
//---------------------------------------------------------------------------


_FX HRESULT WMPServer_IDropTarget_Drop(
    IDropTarget *This, IDataObject *pDataObject,
    DWORD grfKeyState, POINTL pt, DWORD *pdwEffect)
{
    HRESULT hr;
    FORMATETC format;
    STGMEDIUM medium;

    if ((! pDataObject) || (! pdwEffect))
        return E_POINTER;

#ifdef COMSERVER_DEBUG
    { OutputDebugString(L"WMPServer_IDropTarget_Drop\n"); }
#endif

    format.cfFormat = CF_HDROP;
    format.ptd = NULL;
    format.dwAspect = DVASPECT_CONTENT;
    format.lindex = -1;
    format.tymed = TYMED_HGLOBAL;

    memzero(&medium, sizeof(medium));

    hr = IDataObject_GetData(pDataObject, &format, &medium);

    if (FAILED(hr))
        return hr;

    if (medium.tymed == TYMED_HGLOBAL && medium.hGlobal) {

        HDROP hDrop = (HDROP)medium.hGlobal;
        UINT count = DragQueryFile(hDrop, 0xFFFFFFFF, NULL, 0);
        if (count) {
            UINT chars = DragQueryFile(hDrop, 0, NULL, 0);
            if (chars) {
                ULONG bytes;
                WCHAR *path;

                if (! WMPServer_TryWcharBytes((SIZE_T)chars + 1, &bytes)) {
                    ReleaseStgMedium(&medium);
                    return E_OUTOFMEMORY;
                }

                path = Dll_Alloc(bytes);
                if (DragQueryFile(hDrop, 0, path, chars + 1))
                    ComServer_RestartProgram(path);
                HeapFree(GetProcessHeap(), 0, path);
            }
        }
    }

    ReleaseStgMedium(&medium);

    *pdwEffect = DROPEFFECT_COPY;

    return S_OK;
}
