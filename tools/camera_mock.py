"""
Mock Camera Handler for Testing Without Hardware
"""
import base64
import io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime


class MockCameraHandler:
    """Mock camera handler for testing without physical camera"""

    def __init__(self):
        self.is_active = False
        self.camera_index = 0

    def list_cameras(self):
        """Return mock camera list"""
        return [
            {
                "index": 0,
                "name": "Mock Camera 0 (Virtual)",
                "resolution": "1280x720",
                "width": 1280,
                "height": 720,
                "fps": 30,
                "available": True
            }
        ]

    def start_camera(self, camera_index=0):
        """Start mock camera"""
        self.is_active = True
        self.camera_index = camera_index
        return {
            "success": True,
            "camera_index": camera_index,
            "resolution": "1280x720",
            "width": 1280,
            "height": 720,
            "fps": 30,
            "message": f"Mock camera {camera_index} started (testing mode)"
        }

    def capture_snapshot(self):
        """Generate mock image"""
        if not self.is_active:
            return {
                "success": False,
                "error": "Camera not started"
            }

        # Create test image
        img = Image.new('RGB', (1280, 720), color='#2563eb')
        draw = ImageDraw.Draw(img)

        # Add text
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        except:
            font = ImageFont.load_default()

        # Draw test pattern
        draw.text((40, 40), "FormAI Mock Camera", fill='white', font=font)
        draw.text((40, 100), f"Camera {self.camera_index}", fill='white', font=font)
        draw.text((40, 160), timestamp, fill='yellow', font=font)
        draw.text((40, 220), "✓ Camera system working!", fill='lime', font=font)

        # Convert to JPEG bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=90)
        img_bytes = buffer.getvalue()

        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')

        return {
            "success": True,
            "image": img_base64,
            "format": "jpeg",
            "width": 1280,
            "height": 720,
            "size": len(img_bytes),
            "timestamp": timestamp,
            "mock": True
        }

    def stop_camera(self):
        """Stop mock camera"""
        self.is_active = False
        return {
            "success": True,
            "message": "Mock camera stopped"
        }

    def is_camera_active(self):
        """Check if camera is active"""
        return self.is_active


# Global instance
_mock_handler = MockCameraHandler()

# Export functions that match real camera_handler API
def list_cameras():
    return _mock_handler.list_cameras()

def start_camera(camera_index=0):
    return _mock_handler.start_camera(camera_index)

def capture_snapshot():
    return _mock_handler.capture_snapshot()

def stop_camera():
    return _mock_handler.stop_camera()

def is_camera_active():
    return _mock_handler.is_camera_active()
