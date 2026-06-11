#!/usr/bin/env bash
set -euo pipefail

root="${1:-$(git rev-parse --show-toplevel)}"
file="$root/Sandboxie/core/drv/api.c"

body="$(awk '
  /_FX NTSTATUS Api_CopyStringFromUser\(/ { in_func=1 }
  in_func { print }
  in_func && /^}/ { exit }
' "$file")"

require() {
  local needle="$1"
  local message="$2"
  if ! grep -Fq "$needle" <<<"$body"; then
    printf 'KPATH-001 check failed: %s\n' "$message" >&2
    exit 1
  fi
}

reject() {
  local needle="$1"
  local message="$2"
  if grep -Fq "$needle" <<<"$body"; then
    printf 'KPATH-001 check failed: %s\n' "$message" >&2
    exit 1
  fi
}

require "if (uni->Length & (sizeof(WCHAR) - 1))" "odd UNICODE_STRING byte lengths must be rejected"
require "ProbeForRead(buff, uni->Length, sizeof(WCHAR));" "probe must cover only the declared payload length"
require "memcpy(*str, buff, uni->Length);" "copy must cover only the declared payload length"
require "(*str)[uni->Length / sizeof(WCHAR)] = L'\\0';" "terminator index must be derived from payload length"
reject "memcpy(*str, buff, *len);" "copying allocation length reads caller terminator and keeps the old over-copy contract"
reject "(*str)[*len / sizeof(WCHAR)] = L'\\0';" "terminator index based on allocation length writes past the allocation"

printf 'KPATH-001 check passed\n'
