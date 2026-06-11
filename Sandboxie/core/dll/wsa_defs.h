/*
 * Copyright 2022 DavidXanatos, xanasoft.com
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


#ifndef _WSA_DEFS_H
#define _WSA_DEFS_H

#ifndef WSAAPI
#define WSAAPI WINAPI
#endif

//---------------------------------------------------------------------------
// Prototypes
//---------------------------------------------------------------------------

typedef int (WSAAPI *P_WSAStartup)(
    WORD wVersionRequested,
    void* lpWSAData);
    
typedef int (WSAAPI *P_WSACleanup)(void);

typedef SOCKET (WSAAPI *P_socket)(
  int af,
  int type,
  int protocol);

typedef int (WSAAPI *P_WSAIoctl)(
    SOCKET                             s,
    DWORD                              dwIoControlCode,
    LPVOID                             lpvInBuffer,
    DWORD                              cbInBuffer,
    LPVOID                             lpvOutBuffer,
    DWORD                              cbOutBuffer,
    LPDWORD                            lpcbBytesReturned,
    LPWSAOVERLAPPED                    lpOverlapped,
    LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine);

typedef int (WSAAPI *P_ioctlsocket)(
    SOCKET  s,
    long    cmd,
    ULONG*  argp);

typedef int (WSAAPI *P_select)(
    int nfds,
    void *readfds,
    void *writefds,
    void *exceptfds,
    const void *timeout);

typedef int (WSAAPI *P_WSAAsyncSelect)(
    SOCKET  s,
    HWND    hWnd,
    UINT    wMsg,
    long    lEvent);

typedef int (WSAAPI *P_WSAEventSelect)(
    SOCKET  s,
    void*   hEventObject,
    long    lNetworkEvents);

typedef int (WSAAPI *P_WSAEnumNetworkEvents)(
    SOCKET  s,
    void*   hEventObject,
    void*   lpNetworkEvents
);

typedef int (WSAAPI *P_WSANSPIoctl)(
    HANDLE          hLookup,
    DWORD           dwControlCode,
    LPVOID          lpvInBuffer,
    DWORD           cbInBuffer,
    LPVOID          lpvOutBuffer,
    DWORD           cbOutBuffer,
    LPDWORD         lpcbBytesReturned,
    LPWSACOMPLETION lpCompletion);

typedef SOCKET (WSAAPI *P_WSASocketW)(
    int                 af,
    int                 type,
    int                 protocol,
    LPWSAPROTOCOL_INFOW lpProtocolInfo,
    unsigned int        g,
    DWORD               dwFlags);

typedef int (WSAAPI *P_WSAGetLastError)();

typedef void (WSAAPI *P_WSASetLastError)(int err);

typedef int (WSAAPI *P_bind)(
    SOCKET         s,
    const void     *name,
    int            namelen);

typedef int (WSAAPI *P_getsockname)(
    SOCKET         s,
    void           *name,
    int            *namelen);

typedef int (WSAAPI *P_WSAFDIsSet)(
  SOCKET unnamedParam1,
  void *unnamedParam2);

typedef int (WSAAPI *P_connect)(
    SOCKET         s,
    const void     *name,
    int            namelen);

typedef int (WSAAPI *P_WSAConnect)(
    SOCKET         s,
    const void     *name,
    int            namelen,
    LPWSABUF       lpCallerData,
    LPWSABUF       lpCalleeData,
    LPQOS          lpSQOS,
    LPQOS          lpGQOS);

typedef BOOL (WSAAPI *P_ConnectEx) (
    SOCKET          s,
    const void      *name,
    int             namelen,
    PVOID           lpSendBuffer,
    DWORD           dwSendDataLength,
    LPDWORD         lpdwBytesSent,
    LPOVERLAPPED    lpOverlapped);

typedef int (WSAAPI *P_listen)(
    SOCKET         s,
    int            backlog);

typedef SOCKET (WSAAPI *P_accept)(
    SOCKET   s,
    void     *addr,
    int      *addrlen);

typedef SOCKET (WSAAPI *P_WSAAccept)(
    SOCKET          s,
    void            *addr,
    LPINT           addrlen,
    LPCONDITIONPROC lpfnCondition,
    DWORD_PTR       dwCallbackData);

typedef BOOL (WSAAPI *P_AcceptEx)(
    SOCKET       sListenSocket,
    SOCKET       sAcceptSocket,
    PVOID        lpOutputBuffer,
    DWORD        dwReceiveDataLength,
    DWORD        dwLocalAddressLength,
    DWORD        dwRemoteAddressLength,
    LPDWORD      lpdwBytesReceived,
    LPOVERLAPPED lpOverlapped);

typedef int (WSAAPI *P_recv)(
    SOCKET      s,
    char*       buf,
    int         len,
    int         flags);

typedef int (WSAAPI *P_send)(
    SOCKET      s,
    const char* buf,
    int         len,
    int         flags);

typedef int (WSAAPI *P_sendto)(
    SOCKET         s,
    const char     *buf,
    int            len,
    int            flags,
    const void     *to,
    int            tolen);

typedef int (WSAAPI *P_WSASendTo)(
    SOCKET                             s,
    LPWSABUF                           lpBuffers,
    DWORD                              dwBufferCount,
    LPDWORD                            lpNumberOfBytesSent,
    DWORD                              dwFlags,
    const void                         *lpTo,
    int                                iTolen,
    LPWSAOVERLAPPED                    lpOverlapped,
    LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine);

typedef int (WSAAPI *P_recvfrom)(
    SOCKET   s,
    char     *buf,
    int      len,
    int      flags,
    void     *from,
    int      *fromlen);

typedef int (WSAAPI *P_WSARecvFrom)(
    SOCKET                             s,
    LPWSABUF                           lpBuffers,
    DWORD                              dwBufferCount,
    LPDWORD                            lpNumberOfBytesRecvd,
    LPDWORD                            lpFlags,
    void                               *lpFrom,
    LPINT                              lpFromlen,
    LPWSAOVERLAPPED                    lpOverlapped,
    LPWSAOVERLAPPED_COMPLETION_ROUTINE lpCompletionRoutine);

typedef int (WSAAPI *P_shutdown)(SOCKET s, int how);

typedef int (WSAAPI *P_closesocket)(SOCKET s);





typedef enum _WSAEcomparator
{
    COMP_EQUAL = 0,
    COMP_NOTLESS
} WSAECOMPARATOR, *PWSAECOMPARATOR, *LPWSAECOMPARATOR;

typedef struct _WSAVersion
{
    DWORD           dwVersion;
    WSAECOMPARATOR  ecHow;
}WSAVERSION, *PWSAVERSION, *LPWSAVERSION;

typedef struct _AFPROTOCOLS {
    INT iAddressFamily;
    INT iProtocol;
} AFPROTOCOLS, *PAFPROTOCOLS, *LPAFPROTOCOLS;

typedef struct _SOCKET_ADDRESS {
    LPSOCKADDR lpSockaddr;
    INT iSockaddrLength;
} SOCKET_ADDRESS, *PSOCKET_ADDRESS, *LPSOCKET_ADDRESS;

typedef struct _CSADDR_INFO {
    SOCKET_ADDRESS LocalAddr ;
    SOCKET_ADDRESS RemoteAddr ;
    INT iSocketType ;
    INT iProtocol ;
} CSADDR_INFO, *PCSADDR_INFO, FAR * LPCSADDR_INFO ;

typedef struct _WSAQuerySetW
{
    DWORD           dwSize;
    LPWSTR          lpszServiceInstanceName;
    LPGUID          lpServiceClassId;
    LPWSAVERSION    lpVersion;
    LPWSTR          lpszComment;
    DWORD           dwNameSpace;
    LPGUID          lpNSProviderId;
    LPWSTR          lpszContext;
    DWORD           dwNumberOfProtocols;
    LPAFPROTOCOLS   lpafpProtocols;
    LPWSTR          lpszQueryString;
    DWORD           dwNumberOfCsAddrs;
    LPCSADDR_INFO   lpcsaBuffer;
    DWORD           dwOutputFlags;
    LPBLOB          lpBlob;
} WSAQUERYSETW, *PWSAQUERYSETW, *LPWSAQUERYSETW;

struct  hostent {
        char    FAR * h_name;           /* official name of host */
        char    FAR * FAR * h_aliases;  /* alias list */
        short   h_addrtype;             /* host address type */
        short   h_length;               /* length of address */
        char    FAR * FAR * h_addr_list; /* list of addresses */
#define h_addr  h_addr_list[0]          /* address, for backward compat */
};

typedef struct hostent HOSTENT;

typedef int (WSAAPI *P_WSALookupServiceBeginW)(
    LPWSAQUERYSETW  lpqsRestrictions,
    DWORD           dwControlFlags,
    LPHANDLE        lphLookup);

typedef int (WSAAPI *P_WSALookupServiceNextW)(
    HANDLE          hLookup,
    DWORD           dwControlFlags,
    LPDWORD         lpdwBufferLength,
    LPWSAQUERYSETW  lpqsResults);

typedef int (WSAAPI *P_WSALookupServiceEnd)(HANDLE  hLookup);

typedef struct addrinfoW {
    int     ai_flags;
    int     ai_family;
    int     ai_socktype;
    int     ai_protocol;
    size_t  ai_addrlen;
    PWSTR   ai_canonname;
    struct sockaddr *ai_addr;
    struct addrinfoW *ai_next;
} ADDRINFOW, *PADDRINFOW;

typedef int (WSAAPI *P_GetAddrInfoW)(
    PCWSTR          pNodeName,
    PCWSTR          pServiceName,
    const ADDRINFOW *pHints,
    PADDRINFOW      *ppResult);

typedef void (WSAAPI *P_FreeAddrInfoW)(
    PADDRINFOW      pAddrInfo);

typedef PCSTR (WSAAPI *P_inet_ntop)(
    int            family,
    const void     *pAddr,
    PSTR           pStringBuf,
    size_t         StringBufSize);

typedef ULONG (WINAPI *P_GetAdaptersAddresses)(
    ULONG Family,
    ULONG Flags,
    PVOID Reserved,
    void* AdapterAddresses,
    PULONG SizePointer);

#endif _WSA_DEFS_H
