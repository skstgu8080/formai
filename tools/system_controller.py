#!/usr/bin/env python3
"""
System Controller - Full system access with admin privileges
Provides control over processes, registry, network, and file system
"""
import subprocess
import sys
import os
from typing import List, Optional, Dict, Any


class SystemController:
    """
    Full system control with administrator privileges
    Requires FormAI to be running as admin
    """

    @staticmethod
    def kill_process_by_name(process_name: str) -> Dict[str, Any]:
        """
        Kill all processes matching the given name

        Args:
            process_name: Name of process to kill (e.g., 'chrome.exe')

        Returns:
            Result with count of processes killed
        """
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", process_name],
                    capture_output=True,
                    text=True
                )
                return {
                    "success": result.returncode == 0,
                    "message": result.stdout if result.returncode == 0 else result.stderr
                }
            else:
                # Unix-like systems
                result = subprocess.run(
                    ["pkill", "-9", process_name],
                    capture_output=True,
                    text=True
                )
                return {
                    "success": result.returncode == 0,
                    "message": "Process killed" if result.returncode == 0 else result.stderr
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def kill_process_by_port(port: int) -> Dict[str, Any]:
        """
        Kill process listening on specific port

        Args:
            port: Port number

        Returns:
            Result with process info
        """
        try:
            if sys.platform == "win32":
                # Find PID using port
                result = subprocess.run(
                    ["netstat", "-ano", "-p", "TCP"],
                    capture_output=True,
                    text=True
                )

                # Parse output to find PID
                for line in result.stdout.split('\n'):
                    if f":{port}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]

                        # Kill the process
                        kill_result = subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True,
                            text=True
                        )

                        return {
                            "success": kill_result.returncode == 0,
                            "pid": pid,
                            "port": port,
                            "message": kill_result.stdout if kill_result.returncode == 0 else kill_result.stderr
                        }

                return {
                    "success": False,
                    "message": f"No process found on port {port}"
                }
            else:
                # Unix-like systems
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True,
                    text=True
                )

                if result.stdout.strip():
                    pid = result.stdout.strip()
                    subprocess.run(["kill", "-9", pid])
                    return {
                        "success": True,
                        "pid": pid,
                        "port": port
                    }
                return {
                    "success": False,
                    "message": f"No process found on port {port}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def start_process(exe_path: str, args: List[str] = None, wait: bool = False) -> Dict[str, Any]:
        """
        Start a new process

        Args:
            exe_path: Path to executable
            args: Command line arguments
            wait: Whether to wait for process to complete

        Returns:
            Result with process info
        """
        try:
            command = [exe_path] + (args or [])

            if wait:
                result = subprocess.run(command, capture_output=True, text=True)
                return {
                    "success": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
            else:
                process = subprocess.Popen(command)
                return {
                    "success": True,
                    "pid": process.pid
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def set_registry_key(key_path: str, name: str, value: str, value_type: str = "REG_SZ") -> Dict[str, Any]:
        """
        Set Windows registry key (Windows only)

        Args:
            key_path: Registry key path (e.g., "HKCU\\Software\\MyApp")
            name: Value name
            value: Value data
            value_type: Registry value type (REG_SZ, REG_DWORD, etc.)

        Returns:
            Result of operation
        """
        if sys.platform != "win32":
            return {
                "success": False,
                "error": "Registry operations only supported on Windows"
            }

        try:
            import winreg

            # Parse key path
            if key_path.startswith("HKCU"):
                root = winreg.HKEY_CURRENT_USER
                path = key_path[5:]  # Remove "HKCU\\"
            elif key_path.startswith("HKLM"):
                root = winreg.HKEY_LOCAL_MACHINE
                path = key_path[5:]  # Remove "HKLM\\"
            else:
                return {
                    "success": False,
                    "error": "Key path must start with HKCU or HKLM"
                }

            # Open or create key
            key = winreg.CreateKey(root, path)

            # Set value
            if value_type == "REG_DWORD":
                winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))
            else:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

            winreg.CloseKey(key)

            return {
                "success": True,
                "key": key_path,
                "name": name,
                "value": value
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_registry_key(key_path: str, name: str) -> Dict[str, Any]:
        """
        Get Windows registry key value (Windows only)

        Args:
            key_path: Registry key path
            name: Value name

        Returns:
            Value and type
        """
        if sys.platform != "win32":
            return {
                "success": False,
                "error": "Registry operations only supported on Windows"
            }

        try:
            import winreg

            # Parse key path
            if key_path.startswith("HKCU"):
                root = winreg.HKEY_CURRENT_USER
                path = key_path[5:]
            elif key_path.startswith("HKLM"):
                root = winreg.HKEY_LOCAL_MACHINE
                path = key_path[5:]
            else:
                return {
                    "success": False,
                    "error": "Key path must start with HKCU or HKLM"
                }

            # Open key
            key = winreg.OpenKey(root, path)
            value, value_type = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)

            return {
                "success": True,
                "value": value,
                "type": value_type
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def modify_hosts_file(domain: str, ip: str, remove: bool = False) -> Dict[str, Any]:
        """
        Modify Windows hosts file (requires admin)

        Args:
            domain: Domain name
            ip: IP address
            remove: Whether to remove the entry

        Returns:
            Result of operation
        """
        try:
            if sys.platform == "win32":
                hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            else:
                hosts_path = "/etc/hosts"

            # Read current hosts file
            with open(hosts_path, 'r') as f:
                lines = f.readlines()

            # Filter out existing entries for this domain
            new_lines = [line for line in lines if domain not in line]

            # Add new entry if not removing
            if not remove:
                new_lines.append(f"\n{ip} {domain}\n")

            # Write back
            with open(hosts_path, 'w') as f:
                f.writelines(new_lines)

            return {
                "success": True,
                "action": "removed" if remove else "added",
                "domain": domain,
                "ip": ip
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def set_system_proxy(proxy_url: str, enable: bool = True) -> Dict[str, Any]:
        """
        Set system-wide proxy (Windows only)

        Args:
            proxy_url: Proxy URL (e.g., "127.0.0.1:8080")
            enable: Whether to enable or disable

        Returns:
            Result of operation
        """
        if sys.platform != "win32":
            return {
                "success": False,
                "error": "System proxy only supported on Windows"
            }

        try:
            import winreg

            # Internet Settings registry key
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)

            # Set proxy server
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_url)

            # Enable/disable proxy
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enable else 0)

            winreg.CloseKey(key)

            return {
                "success": True,
                "proxy": proxy_url,
                "enabled": enable
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
_system_controller = None

def get_system_controller() -> SystemController:
    """Get or create system controller instance"""
    global _system_controller
    if _system_controller is None:
        _system_controller = SystemController()
    return _system_controller
