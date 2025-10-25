"""
Camera Handler Module - Camera access and streaming
"""
import cv2
import base64
import numpy as np
import platform
import os
import logging
from typing import Optional, List, Dict
from datetime import datetime
import threading
import time

# Configure logging - only show errors by default
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Check if verbose camera logging is enabled
CAMERA_VERBOSE = os.getenv("CAMERA_VERBOSE", "false").lower() == "true"


class CameraHandler:
    """Handles camera operations for remote access"""

    def __init__(self):
        self.active_camera: Optional[cv2.VideoCapture] = None
        self.camera_index: int = 0
        self.is_streaming: bool = False
        self._lock = threading.Lock()
        self.is_windows = platform.system() == "Windows"

    def _open_camera(self, index: int, retries: int = 3) -> Optional[cv2.VideoCapture]:
        """
        Open camera with platform-specific backend and retry logic

        Args:
            index: Camera index
            retries: Number of retry attempts

        Returns:
            VideoCapture object or None
        """
        for attempt in range(retries):
            try:
                # Use DirectShow backend on Windows for better compatibility
                if self.is_windows:
                    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
                else:
                    cap = cv2.VideoCapture(index)

                if cap.isOpened():
                    # Verify we can actually read a frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        return cap
                    else:
                        if CAMERA_VERBOSE:
                            logger.warning(f"Camera {index} opened but failed to read frame (attempt {attempt + 1}/{retries})")
                        cap.release()
                else:
                    if CAMERA_VERBOSE:
                        logger.warning(f"Failed to open camera {index} (attempt {attempt + 1}/{retries})")

                # Wait before retry
                if attempt < retries - 1:
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error opening camera {index}: {e}")
                if attempt < retries - 1:
                    time.sleep(0.5)

        return None

    def list_cameras(self) -> List[Dict[str, any]]:
        """
        List all available cameras

        Returns:
            List of camera info dictionaries
        """
        cameras = []

        # Test up to 10 camera indices
        for index in range(10):
            cap = self._open_camera(index, retries=1)
            if cap is not None:
                try:
                    # Get camera properties
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = int(cap.get(cv2.CAP_PROP_FPS))

                    cameras.append({
                        "index": index,
                        "name": f"Camera {index}",
                        "resolution": f"{width}x{height}",
                        "width": width,
                        "height": height,
                        "fps": fps,
                        "available": True
                    })
                finally:
                    cap.release()
            else:
                # Camera index doesn't exist, stop searching
                if index > 0:  # Only stop if we've tried at least camera 0
                    break

        return cameras

    def start_camera(self, camera_index: int = 0, width: int = 1920, height: int = 1080, fps: int = 30) -> Dict[str, any]:
        """
        Start camera streaming with high-quality settings

        Args:
            camera_index: Camera index to use (default: 0)
            width: Desired frame width (default: 1920 for Full HD)
            height: Desired frame height (default: 1080 for Full HD)
            fps: Desired frame rate (default: 30)

        Returns:
            Status dictionary
        """
        with self._lock:
            # Stop existing camera if running
            if self.active_camera is not None:
                self.stop_camera()

            # Initialize camera with retry logic
            if CAMERA_VERBOSE:
                logger.info(f"Attempting to open camera {camera_index} on {platform.system()}...")
            self.active_camera = self._open_camera(camera_index, retries=3)

            if self.active_camera is None:
                error_msg = f"Failed to open camera {camera_index} after 3 attempts"
                if self.is_windows:
                    error_msg += ". Note: Windows requires DirectShow backend (CAP_DSHOW)"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

            # Set high-quality camera properties
            if CAMERA_VERBOSE:
                logger.info(f"Setting camera to {width}x{height} @ {fps}fps...")
            self.active_camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.active_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.active_camera.set(cv2.CAP_PROP_FPS, fps)

            # Additional quality settings
            self.active_camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            self.active_camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce latency

            # Get actual camera properties (may differ from requested)
            actual_width = int(self.active_camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.active_camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.active_camera.get(cv2.CAP_PROP_FPS))

            self.camera_index = camera_index
            self.is_streaming = True

            success_msg = f"Camera {camera_index} started: {actual_width}x{actual_height} @ {actual_fps}fps"
            if actual_width != width or actual_height != height or actual_fps != fps:
                success_msg += f" (requested {width}x{height} @ {fps}fps)"

            if CAMERA_VERBOSE:
                logger.info(success_msg)

            return {
                "success": True,
                "camera_index": camera_index,
                "resolution": f"{actual_width}x{actual_height}",
                "width": actual_width,
                "height": actual_height,
                "fps": actual_fps,
                "message": success_msg
            }

    def capture_snapshot(self) -> Dict[str, any]:
        """
        Capture a single frame from active camera

        Returns:
            Dictionary with base64 encoded JPEG and metadata
        """
        with self._lock:
            if self.active_camera is None or not self.active_camera.isOpened():
                logger.error("No active camera. Call start_camera first.")
                return {
                    "success": False,
                    "error": "No active camera. Call start_camera first."
                }

            # Capture frame
            ret, frame = self.active_camera.read()

            if not ret or frame is None:
                logger.error("Failed to capture frame from camera")
                return {
                    "success": False,
                    "error": "Failed to capture frame. Camera may be in use by another application."
                }

            # Encode frame as JPEG with high quality
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)

            if not ret:
                logger.error("Failed to encode frame as JPEG")
                return {
                    "success": False,
                    "error": "Failed to encode frame as JPEG"
                }

            # Convert to base64
            jpg_bytes = buffer.tobytes()
            jpg_base64 = base64.b64encode(jpg_bytes).decode('utf-8')

            # Get frame metadata
            height, width = frame.shape[:2]

            # Removed verbose SUCCESS message - only log if verbose mode enabled
            if CAMERA_VERBOSE:
                logger.debug(f"Captured frame {width}x{height} ({len(jpg_bytes)} bytes)")

            return {
                "success": True,
                "image": jpg_base64,
                "format": "jpeg",
                "camera_index": self.camera_index,
                "resolution": f"{width}x{height}",
                "width": width,
                "height": height,
                "size": len(jpg_bytes),
                "timestamp": datetime.utcnow().isoformat()
            }

    def quick_snapshot(self, camera_index: int = 0, quality: int = 95) -> Dict[str, any]:
        """
        Quick snapshot - opens camera, captures one frame, closes camera
        Inspired by dystopia-c2's webshot() function
        This is simpler and more reliable than maintaining a persistent camera session

        Args:
            camera_index: Camera index to use (default: 0)
            quality: JPEG quality 1-100 (default: 95 for high quality)

        Returns:
            Dictionary with base64 encoded JPEG and metadata
        """
        if CAMERA_VERBOSE:
            logger.info(f"Quick snapshot from camera {camera_index}...")

        # Open camera
        cap = self._open_camera(camera_index, retries=3)

        if cap is None:
            error_msg = f"Failed to open camera {camera_index} for quick snapshot"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

        try:
            # Set high-quality camera properties before capturing
            if CAMERA_VERBOSE:
                logger.info("Setting camera to 1920x1080 for high-quality snapshot...")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Wait a moment for camera to adjust to new settings
            time.sleep(0.1)

            # Capture frame
            ret, frame = cap.read()

            if not ret or frame is None:
                logger.error("Failed to capture frame")
                return {
                    "success": False,
                    "error": "Failed to capture frame"
                }

            # Encode frame as JPEG
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            ret, buffer = cv2.imencode('.jpg', frame, encode_param)

            if not ret:
                logger.error("Failed to encode frame")
                return {
                    "success": False,
                    "error": "Failed to encode frame as JPEG"
                }

            # Convert to base64
            jpg_bytes = buffer.tobytes()
            jpg_base64 = base64.b64encode(jpg_bytes).decode('utf-8')

            # Get frame metadata
            height, width = frame.shape[:2]

            if CAMERA_VERBOSE:
                logger.info(f"Quick snapshot {width}x{height} ({len(jpg_bytes)} bytes)")

            return {
                "success": True,
                "image": jpg_base64,
                "format": "jpeg",
                "camera_index": camera_index,
                "resolution": f"{width}x{height}",
                "width": width,
                "height": height,
                "size": len(jpg_bytes),
                "timestamp": datetime.utcnow().isoformat()
            }

        finally:
            # Always release camera
            cap.release()
            if CAMERA_VERBOSE:
                logger.debug("Camera released")

    def stop_camera(self) -> Dict[str, any]:
        """
        Stop camera and cleanup resources

        Returns:
            Status dictionary
        """
        with self._lock:
            if self.active_camera is None:
                if CAMERA_VERBOSE:
                    logger.debug("No active camera to stop")
                return {
                    "success": True,
                    "message": "No active camera to stop"
                }

            try:
                self.active_camera.release()
                self.active_camera = None
                self.is_streaming = False

                if CAMERA_VERBOSE:
                    logger.info("Camera stopped and released")

                return {
                    "success": True,
                    "message": "Camera stopped successfully"
                }
            except Exception as e:
                error_msg = f"Error stopping camera: {str(e)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }

    def is_camera_active(self) -> bool:
        """Check if camera is currently active"""
        return self.active_camera is not None and self.active_camera.isOpened()

    def __del__(self):
        """Cleanup on deletion"""
        if self.active_camera is not None:
            self.active_camera.release()


# Global camera handler instance
_camera_handler = None


def get_camera_handler() -> CameraHandler:
    """Get or create global camera handler instance"""
    global _camera_handler
    if _camera_handler is None:
        _camera_handler = CameraHandler()
    return _camera_handler


def list_cameras() -> List[Dict[str, any]]:
    """List available cameras"""
    handler = get_camera_handler()
    return handler.list_cameras()


def start_camera(camera_index: int = 0) -> Dict[str, any]:
    """Start camera streaming"""
    handler = get_camera_handler()
    return handler.start_camera(camera_index)


def capture_snapshot() -> Dict[str, any]:
    """Capture snapshot from active camera"""
    handler = get_camera_handler()
    return handler.capture_snapshot()


def stop_camera() -> Dict[str, any]:
    """Stop camera"""
    handler = get_camera_handler()
    return handler.stop_camera()


def quick_snapshot(camera_index: int = 0, quality: int = 95) -> Dict[str, any]:
    """
    Quick snapshot - opens camera, captures one frame, closes camera
    Simpler alternative to start_camera -> capture_snapshot -> stop_camera flow
    Default quality increased to 95 for better image quality
    """
    handler = get_camera_handler()
    return handler.quick_snapshot(camera_index, quality)
