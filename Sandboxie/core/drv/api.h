/*
 * Copyright 2004-2020 Sandboxie Holdings, LLC 
 * Copyright 2020 David Xanatos, xanasoft.com
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
// Driver API
//---------------------------------------------------------------------------


#ifndef _MY_API_H
#define _MY_API_H


#include "driver.h"
#include "api_defs.h"

// API_ARGS are 64-bit slots, but WOW64 callers can pass the 32-bit
// NtCurrentProcess sentinel.  Accept only the native -1 and zero-extended
// 32-bit -1 forms; do not match arbitrary 64-bit values by truncation.
#define IS_ARG_CURRENT_PROCESS(h) \
    (((ULONG_PTR)(h) == (ULONG_PTR)-1) || ((ULONG_PTR)(h) == (ULONG_PTR)0xffffffff))


//---------------------------------------------------------------------------
// Structures and Types
//---------------------------------------------------------------------------


typedef struct _Sbie_SeFilterTokenArg
{
    PACCESS_TOKEN       ExistingToken;
    ULONG               Flags;
    PTOKEN_GROUPS       SidsToDisable;
    PTOKEN_PRIVILEGES   PrivilegesToDelete;
    PTOKEN_GROUPS       RestrictedSids;
    PACCESS_TOKEN       *NewToken;
    NTSTATUS            *status;
} Sbie_SeFilterTokenArg;

typedef struct _Sbie_SepFilterTokenArg
{
    void*           TokenObject;
    ULONG_PTR       SidCount;
    ULONG_PTR       SidPtr;
    ULONG_PTR       LengthIncrease;
    void            **NewToken;
    NTSTATUS        *status;
} Sbie_SepFilterTokenArg;

//---------------------------------------------------------------------------
// Functions
//---------------------------------------------------------------------------


BOOLEAN Api_Init(void);

void Api_Unload(void);

//
// Disable API services in preparation of driver unload
//

BOOLEAN Api_Disable(void);

//
// Adds an API function
//

typedef NTSTATUS(*P_Api_Function)(PROCESS *, ULONG64 *parms);

void Api_SetFunction(ULONG func_code, P_Api_Function func_ptr);

//
// Resets the recorded information for SbieSvc process, when it terminates
//

void Api_ResetServiceProcess(void);

//
// Send a request kernel to the user mode service
//

BOOLEAN Api_SendServiceMessage(ULONG msgid, ULONG data_len, void *data);

//
// Add message to log buffer
//

void Api_AddMessage(
	NTSTATUS error_code,
	const WCHAR** strings, ULONG* lengths,
	ULONG session_id,
	ULONG process_id);


//
// Copies boxname parameter from user
//

BOOLEAN Api_CopyBoxNameFromUser(
    WCHAR *boxname34, const WCHAR *user_boxname);

//
// Copies SID string parameter from user
//

BOOLEAN Api_CopySidStringFromUser(
    WCHAR *sidstring96, const WCHAR *user_sidstring);

//
// Copies the 'len' bytes from the kernel mode buffer at 'str',
// into the user mode buffer specified by 'uni', and updates uni->Length.
// May raise STATUS_BUFFER_TOO_SMALL or STATUS_ACCESS_VIOLATION
//

void Api_CopyStringToUser(
    UNICODE_STRING64 *uni, WCHAR *str, size_t len);

NTSTATUS Api_CopyStringFromUser(
    WCHAR** str, size_t* len, UNICODE_STRING64* uni);

NTSTATUS Sbie_SepFilterTokenHandler(
    void*       TokenObject,
    ULONG_PTR   SidCount,
    ULONG_PTR   SidPtr,
    ULONG_PTR   LengthIncrease,
    void        **NewToken);

//---------------------------------------------------------------------------
// Variables
//---------------------------------------------------------------------------


extern volatile HANDLE Api_ServiceProcessId;


//---------------------------------------------------------------------------


#endif // _MY_API_H
