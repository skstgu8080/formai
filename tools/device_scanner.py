"""
Device Scanner - Enumerate all connected devices on Windows/Linux
"""
import platform
import subprocess
import json
from typing import List, Dict


def scan_all_devices() -> Dict:
    """Scan for all connected devices on the system"""
    system = platform.system()

    if system == "Windows":
        return scan_windows_devices()
    elif system == "Linux":
        return scan_linux_devices()
    else:
        return {
            "success": False,
            "error": f"Unsupported platform: {system}"
        }


def scan_windows_devices() -> Dict:
    """Scan devices on Windows using PowerShell and wmic"""
    devices = {
        "success": True,
        "platform": "Windows",
        "cameras": scan_windows_cameras(),
        "audio_devices": scan_windows_audio(),
        "usb_devices": scan_windows_usb(),
        "network_adapters": scan_windows_network(),
        "storage_devices": scan_windows_storage(),
        "display_devices": scan_windows_displays(),
        "all_pnp_devices": scan_windows_pnp()
    }
    return devices


def scan_windows_cameras() -> List[Dict]:
    """Get list of camera devices on Windows"""
    cameras = []
    try:
        # Try using PowerShell to enumerate cameras
        cmd = 'powershell "Get-PnpDevice | Where-Object {$_.Class -eq \'Camera\' -or $_.FriendlyName -like \'*camera*\' -or $_.FriendlyName -like \'*webcam*\'} | Select-Object FriendlyName, Status, InstanceId | ConvertTo-Json"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]

            for idx, device in enumerate(data):
                cameras.append({
                    "index": idx,
                    "name": device.get("FriendlyName", "Unknown Camera"),
                    "status": device.get("Status", "Unknown"),
                    "instance_id": device.get("InstanceId", "")
                })
    except Exception as e:
        cameras.append({"error": str(e)})

    return cameras


def scan_windows_audio() -> List[Dict]:
    """Get list of audio devices on Windows"""
    audio_devices = []
    try:
        cmd = 'powershell "Get-PnpDevice | Where-Object {$_.Class -eq \'AudioEndpoint\' -or $_.Class -eq \'MEDIA\'} | Select-Object FriendlyName, Status, InstanceId | ConvertTo-Json"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]

            for device in data:
                audio_devices.append({
                    "name": device.get("FriendlyName", "Unknown Audio Device"),
                    "status": device.get("Status", "Unknown"),
                    "instance_id": device.get("InstanceId", "")
                })
    except Exception as e:
        audio_devices.append({"error": str(e)})

    return audio_devices


def scan_windows_usb() -> List[Dict]:
    """Get list of USB devices on Windows"""
    usb_devices = []
    try:
        cmd = 'powershell "Get-PnpDevice | Where-Object {$_.InstanceId -like \'USB*\'} | Select-Object FriendlyName, Status, InstanceId, Class | ConvertTo-Json"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]

            for device in data:
                usb_devices.append({
                    "name": device.get("FriendlyName", "Unknown USB Device"),
                    "status": device.get("Status", "Unknown"),
                    "class": device.get("Class", "Unknown"),
                    "instance_id": device.get("InstanceId", "")
                })
    except Exception as e:
        usb_devices.append({"error": str(e)})

    return usb_devices


def scan_windows_network() -> List[Dict]:
    """Get list of network adapters on Windows"""
    adapters = []
    try:
        cmd = 'powershell "Get-NetAdapter | Select-Object Name, Status, MacAddress, LinkSpeed | ConvertTo-Json"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]

            for adapter in data:
                adapters.append({
                    "name": adapter.get("Name", "Unknown Adapter"),
                    "status": adapter.get("Status", "Unknown"),
                    "mac_address": adapter.get("MacAddress", ""),
                    "link_speed": adapter.get("LinkSpeed", "Unknown")
                })
    except Exception as e:
        adapters.append({"error": str(e)})

    return adapters


def scan_windows_storage() -> List[Dict]:
    """Get list of storage devices on Windows"""
    storage = []
    try:
        cmd = 'powershell "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, Size, BusType | ConvertTo-Json"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]

            for disk in data:
                size_gb = int(disk.get("Size", 0)) / (1024**3) if disk.get("Size") else 0
                storage.append({
                    "name": disk.get("FriendlyName", "Unknown Disk"),
                    "media_type": disk.get("MediaType", "Unknown"),
                    "size_gb": round(size_gb, 2),
                    "bus_type": disk.get("BusType", "Unknown")
                })
    except Exception as e:
        storage.append({"error": str(e)})

    return storage


def scan_windows_displays() -> List[Dict]:
    """Get list of display devices on Windows"""
    displays = []
    try:
        cmd = 'powershell "Get-PnpDevice | Where-Object {$_.Class -eq \'Monitor\' -or $_.Class -eq \'Display\'} | Select-Object FriendlyName, Status | ConvertTo-Json"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]

            for display in data:
                displays.append({
                    "name": display.get("FriendlyName", "Unknown Display"),
                    "status": display.get("Status", "Unknown")
                })
    except Exception as e:
        displays.append({"error": str(e)})

    return displays


def scan_windows_pnp() -> List[Dict]:
    """Get comprehensive list of all PnP devices on Windows"""
    devices = []
    try:
        # Get summary of device counts by class
        cmd = 'powershell "Get-PnpDevice | Where-Object {$_.Status -eq \'OK\'} | Group-Object Class | Select-Object Name, Count | Sort-Object Count -Descending | ConvertTo-Json"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, dict):
                data = [data]

            for item in data:
                devices.append({
                    "class": item.get("Name", "Unknown"),
                    "count": item.get("Count", 0)
                })
    except Exception as e:
        devices.append({"error": str(e)})

    return devices


def scan_linux_devices() -> Dict:
    """Scan devices on Linux using lsusb, lspci, etc."""
    devices = {
        "success": True,
        "platform": "Linux",
        "cameras": scan_linux_cameras(),
        "audio_devices": scan_linux_audio(),
        "usb_devices": scan_linux_usb(),
        "pci_devices": scan_linux_pci(),
        "storage_devices": scan_linux_storage()
    }
    return devices


def scan_linux_cameras() -> List[Dict]:
    """Get list of camera devices on Linux"""
    cameras = []
    try:
        # Check /dev/video* devices
        import os
        video_devices = [d for d in os.listdir('/dev') if d.startswith('video')]
        for idx, device in enumerate(sorted(video_devices)):
            cameras.append({
                "index": idx,
                "name": f"/dev/{device}",
                "status": "Available"
            })
    except Exception as e:
        cameras.append({"error": str(e)})

    return cameras


def scan_linux_audio() -> List[Dict]:
    """Get list of audio devices on Linux"""
    audio_devices = []
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'card' in line.lower():
                    audio_devices.append({"name": line.strip()})
    except Exception as e:
        audio_devices.append({"error": str(e)})

    return audio_devices


def scan_linux_usb() -> List[Dict]:
    """Get list of USB devices on Linux"""
    usb_devices = []
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if line.strip():
                    usb_devices.append({"name": line.strip()})
    except Exception as e:
        usb_devices.append({"error": str(e)})

    return usb_devices


def scan_linux_pci() -> List[Dict]:
    """Get list of PCI devices on Linux"""
    pci_devices = []
    try:
        result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if line.strip():
                    pci_devices.append({"name": line.strip()})
    except Exception as e:
        pci_devices.append({"error": str(e)})

    return pci_devices


def scan_linux_storage() -> List[Dict]:
    """Get list of storage devices on Linux"""
    storage = []
    try:
        result = subprocess.run(['lsblk', '-d', '-o', 'NAME,SIZE,TYPE'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.split('\n')[1:]  # Skip header
            for line in lines:
                if line.strip():
                    storage.append({"name": line.strip()})
    except Exception as e:
        storage.append({"error": str(e)})

    return storage


if __name__ == "__main__":
    # Test the scanner
    import pprint
    devices = scan_all_devices()
    pprint.pprint(devices)
