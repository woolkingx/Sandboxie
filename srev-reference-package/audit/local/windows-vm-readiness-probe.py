#!/usr/bin/env python3
"""Probe a disposable Windows VM from the Linux controller.

This script is intentionally dependency-light. It does not know passwords and
does not change the VM. If SSH key access is available, it collects the first
readiness facts needed by docs/plan/local/windows-test-vm-requirements.md.
"""

from __future__ import annotations

import argparse
import base64
import json
import socket
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


DEFAULT_PORTS = (22, 5985, 3389, 5986)


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout.strip(),
            "stderr": self.stderr.strip(),
        }


def check_port(host: str, port: int, timeout: float) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def run_command(command: list[str], timeout: int) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            command=command,
            returncode=124,
            stdout=exc.stdout or "",
            stderr=f"timeout after {exc.timeout} seconds",
        )
    return CommandResult(
        command=command,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def ssh_command(host: str, user: str, remote_command: str, timeout: int) -> list[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={timeout}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{user}@{host}",
        remote_command,
    ]


def powershell_command(script: str) -> str:
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}"


def collect_ssh_readiness(host: str, user: str, timeout: int) -> dict[str, Any]:
    checks = {
        "hostname": "hostname",
        "whoami": "whoami",
        "powershell_version": powershell_command("$PSVersionTable.PSVersion.ToString()"),
        "computer_info": powershell_command(
            "Get-CimInstance Win32_OperatingSystem | "
            "Select-Object Caption,Version,BuildNumber | "
            "ConvertTo-Json -Compress"
        ),
        "computer_system": powershell_command(
            "Get-CimInstance Win32_ComputerSystem | "
            "Select-Object Manufacturer,Model,TotalPhysicalMemory,NumberOfLogicalProcessors | "
            "ConvertTo-Json -Compress"
        ),
        "services": powershell_command(
            "Get-Service sshd,WinRM,WinDefend,mpssvc -ErrorAction SilentlyContinue | "
            "Select-Object Name,Status,StartType | ConvertTo-Json -Compress"
        ),
        "testsigning": powershell_command(
            "bcdedit /enum | Select-String -Pattern testsigning | ForEach-Object { $_.Line }"
        ),
        "tool_path": powershell_command(
            "$tools=@('git','python','pwsh','msbuild','cl','link','signtool','inf2cat','windbg'); "
            "foreach($t in $tools){ "
            "  Write-Output ('== ' + $t + ' =='); "
            "  where.exe $t 2>$null "
            "}"
        ),
        "vswhere": powershell_command(
            "$vswhere='${env:ProgramFiles(x86)}\\Microsoft Visual Studio\\Installer\\vswhere.exe'; "
            "if(Test-Path $vswhere){ "
            "  & $vswhere -latest -products * "
            "    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 "
            "    -property installationPath "
            "} else { 'missing-vswhere' }"
        ),
    }

    results: dict[str, Any] = {}
    for name, remote_command in checks.items():
        result = run_command(ssh_command(host, user, remote_command, timeout), timeout + 20)
        results[name] = result.as_dict()
        if name == "hostname" and result.returncode != 0:
            break
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Windows VM IPv4 address or DNS name")
    parser.add_argument("--user", default="sbie-test", help="SSH user to test")
    parser.add_argument("--timeout", type=int, default=6, help="Network timeout in seconds")
    parser.add_argument(
        "--ports",
        type=int,
        nargs="*",
        default=list(DEFAULT_PORTS),
        help="TCP ports to check before SSH readiness",
    )
    args = parser.parse_args()

    ports = {
        str(port): check_port(args.host, port, float(args.timeout))
        for port in args.ports
    }
    report: dict[str, Any] = {
        "schema": "windows-vm-readiness-probe/v1",
        "host": args.host,
        "user": args.user,
        "ports": ports,
        "ssh": {},
        "ready": False,
    }

    if ports.get("22"):
        report["ssh"] = collect_ssh_readiness(args.host, args.user, args.timeout)

    hostname = report["ssh"].get("hostname", {}) if isinstance(report["ssh"], dict) else {}
    report["ready"] = bool(hostname.get("returncode") == 0)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OSError as exc:
        print(
            json.dumps(
                {
                    "schema": "windows-vm-readiness-probe/v1",
                    "ready": False,
                    "error": type(exc).__name__,
                    "message": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(2)
