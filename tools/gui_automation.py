#!/usr/bin/env python3
"""
PyAutoGUI Helper Module - Enhanced GUI automation for form filling
"""
import time
import random
from typing import Tuple, Optional, List
import pyautogui
from PIL import Image
import numpy as np

# Configure PyAutoGUI
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1  # Add small pause between actions

class GUIHelper:
    """PyAutoGUI helper for advanced browser interaction"""

    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        self.last_position = None

    @staticmethod
    def human_like_movement(start_pos: Tuple[int, int], end_pos: Tuple[int, int], duration: float = 1.0):
        """Move mouse with human-like curve instead of straight line"""
        # Add some randomness to duration
        duration = duration + random.uniform(-0.2, 0.2)
        duration = max(0.5, duration)  # Minimum 0.5 seconds

        # Create control points for bezier curve
        control_x = (start_pos[0] + end_pos[0]) / 2 + random.randint(-50, 50)
        control_y = (start_pos[1] + end_pos[1]) / 2 + random.randint(-50, 50)

        # Move with curve
        pyautogui.moveTo(end_pos[0], end_pos[1], duration, pyautogui.easeInOutQuad)

    @staticmethod
    def human_like_typing(text: str, min_delay: float = 0.05, max_delay: float = 0.15):
        """Type text with human-like variable speed"""
        for char in text:
            pyautogui.write(char)
            time.sleep(random.uniform(min_delay, max_delay))

            # Occasionally pause longer (thinking)
            if random.random() < 0.1:
                time.sleep(random.uniform(0.3, 0.6))

    @staticmethod
    def find_and_click(image_path: str, confidence: float = 0.8, click_offset: Tuple[int, int] = (0, 0)) -> bool:
        """Find an image on screen and click it"""
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)

            if location:
                center = pyautogui.center(location)
                click_x = center.x + click_offset[0] + random.randint(-2, 2)
                click_y = center.y + click_offset[1] + random.randint(-2, 2)

                # Move to position with human-like movement
                current_pos = pyautogui.position()
                GUIHelper.human_like_movement(current_pos, (click_x, click_y))

                # Click with slight randomness in timing
                time.sleep(random.uniform(0.1, 0.3))
                pyautogui.click()
                return True
        except Exception as e:
            print(f"Error finding/clicking image: {e}")

        return False

    @staticmethod
    def scroll_smoothly(clicks: int = 3, direction: str = 'down'):
        """Scroll the page smoothly"""
        scroll_amount = clicks if direction == 'down' else -clicks

        for _ in range(abs(clicks)):
            pyautogui.scroll(scroll_amount / abs(clicks) * 3)
            time.sleep(random.uniform(0.1, 0.2))

    @staticmethod
    def click_at_position(x: int, y: int, human_like: bool = True):
        """Click at specific coordinates"""
        if human_like:
            current_pos = pyautogui.position()
            GUIHelper.human_like_movement(current_pos, (x, y))
            time.sleep(random.uniform(0.1, 0.3))

        pyautogui.click(x, y)

    @staticmethod
    def triple_click(x: int = None, y: int = None):
        """Triple click to select all text in a field"""
        if x is not None and y is not None:
            pyautogui.click(x, y)

        # Perform triple click
        pyautogui.click(clicks=3, interval=0.1)

    @staticmethod
    def select_all_and_type(text: str):
        """Select all text and replace with new text"""
        # Select all (Ctrl+A)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)

        # Type new text
        GUIHelper.human_like_typing(text)

    @staticmethod
    def handle_dropdown_gui(options: List[str], target_value: str) -> bool:
        """Handle dropdown selection using GUI automation"""
        try:
            # Click to open dropdown (assuming it's already focused)
            pyautogui.click()
            time.sleep(0.5)

            # Try to find and select the option
            # First, try typing to search
            pyautogui.write(target_value[:3])  # Type first 3 chars
            time.sleep(0.3)

            # Press Enter to select
            pyautogui.press('enter')
            return True
        except:
            return False

    @staticmethod
    def capture_element_screenshot(x: int, y: int, width: int, height: int, filename: str = None) -> str:
        """Capture screenshot of specific element"""
        try:
            # Take screenshot of region
            screenshot = pyautogui.screenshot(region=(x, y, width, height))

            if filename:
                screenshot.save(filename)
                return filename
            else:
                # Return as base64 or PIL Image
                return screenshot
        except Exception as e:
            print(f"Error capturing element screenshot: {e}")
            return None

    @staticmethod
    def wait_for_element(image_path: str, timeout: int = 10, confidence: float = 0.8) -> bool:
        """Wait for an element to appear on screen"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if pyautogui.locateOnScreen(image_path, confidence=confidence):
                    return True
            except:
                pass

            time.sleep(0.5)

        return False

    @staticmethod
    def handle_alert():
        """Handle browser alerts/popups"""
        # Press Escape to close popup
        pyautogui.press('escape')
        time.sleep(0.2)

        # Alternative: Press Enter to accept
        # pyautogui.press('enter')

    @staticmethod
    def paste_text(text: str):
        """Copy text to clipboard and paste (faster than typing)"""
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')

    @staticmethod
    def move_mouse_randomly():
        """Move mouse randomly to appear more human"""
        current_x, current_y = pyautogui.position()

        # Random movement within small area
        new_x = current_x + random.randint(-50, 50)
        new_y = current_y + random.randint(-50, 50)

        # Keep within screen bounds
        new_x = max(0, min(new_x, pyautogui.size()[0]))
        new_y = max(0, min(new_y, pyautogui.size()[1]))

        pyautogui.moveTo(new_x, new_y, duration=random.uniform(0.2, 0.5))

class CAPTCHAHelper:
    """Helper for CAPTCHA interaction (manual solving assistance)"""

    @staticmethod
    def highlight_captcha_area():
        """Highlight CAPTCHA area for manual solving"""
        print("CAPTCHA detected! Please solve it manually.")
        print("Moving mouse to likely CAPTCHA area...")

        # Common CAPTCHA positions (can be customized)
        likely_positions = [
            (400, 400),  # Center-ish
            (300, 500),  # Lower center
            (500, 350),  # Upper center
        ]

        for pos in likely_positions:
            pyautogui.moveTo(pos[0], pos[1], duration=1)
            time.sleep(0.5)

        # Flash notification
        for _ in range(3):
            pyautogui.alert("Please solve the CAPTCHA", "CAPTCHA Detected", button='OK')
            break  # Only show once

    @staticmethod
    def wait_for_captcha_solved(timeout: int = 60) -> bool:
        """Wait for user to manually solve CAPTCHA"""
        print(f"Waiting up to {timeout} seconds for CAPTCHA to be solved...")

        start_time = time.time()
        last_screenshot = pyautogui.screenshot()

        while time.time() - start_time < timeout:
            time.sleep(2)
            current_screenshot = pyautogui.screenshot()

            # Check if screen changed significantly (CAPTCHA solved)
            if not GUIHelper._images_similar(last_screenshot, current_screenshot):
                print("Screen changed, CAPTCHA might be solved!")
                return True

            last_screenshot = current_screenshot

        return False

    @staticmethod
    def _images_similar(img1: Image.Image, img2: Image.Image, threshold: float = 0.95) -> bool:
        """Check if two images are similar"""
        try:
            # Resize for faster comparison
            img1_small = img1.resize((100, 100))
            img2_small = img2.resize((100, 100))

            # Convert to arrays
            arr1 = np.array(img1_small)
            arr2 = np.array(img2_small)

            # Calculate similarity
            diff = np.sum(np.abs(arr1 - arr2))
            max_diff = arr1.size * 255
            similarity = 1 - (diff / max_diff)

            return similarity > threshold
        except:
            return False

class FormFillerGUI:
    """GUI-based form filler using PyAutoGUI"""

    def __init__(self):
        self.gui_helper = GUIHelper()
        self.captcha_helper = CAPTCHAHelper()

    def fill_field_at_position(self, x: int, y: int, value: str, clear_first: bool = True):
        """Fill a field at specific screen coordinates"""
        # Click on field
        GUIHelper.click_at_position(x, y, human_like=True)
        time.sleep(0.2)

        if clear_first:
            # Select all and delete
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('delete')
            time.sleep(0.1)

        # Type value with human-like speed
        GUIHelper.human_like_typing(value)

    def fill_form_with_tab_navigation(self, field_values: List[str]):
        """Fill form by tabbing through fields"""
        for value in field_values:
            if value:
                # Clear field
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.1)

                # Type value
                GUIHelper.human_like_typing(value)
                time.sleep(0.2)

            # Tab to next field
            pyautogui.press('tab')
            time.sleep(0.3)

    def submit_form(self):
        """Submit form using Enter or by clicking submit button"""
        # Try pressing Enter
        pyautogui.press('enter')

        # Alternative: Look for submit button image
        # GUIHelper.find_and_click("submit_button.png")

    def handle_popups(self):
        """Handle various popups that might appear"""
        # Close popups with Escape
        pyautogui.press('escape')
        time.sleep(0.2)

        # Try clicking X button if visible
        # GUIHelper.find_and_click("close_button.png")

# Utility functions
def demonstrate_human_behavior():
    """Demonstrate human-like behavior for anti-bot systems"""
    # Random mouse movements
    for _ in range(3):
        GUIHelper.move_mouse_randomly()
        time.sleep(random.uniform(0.5, 1.5))

    # Random scrolling
    GUIHelper.scroll_smoothly(random.randint(1, 3))
    time.sleep(random.uniform(0.5, 1.0))
    GUIHelper.scroll_smoothly(random.randint(1, 3), direction='up')

def get_mouse_position_for_element():
    """Helper to get mouse position for configuring automation"""
    print("Move mouse to the element and press Ctrl+C to capture position...")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"Mouse position: X={x}, Y={y}", end='\r')
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\nCaptured position: X={x}, Y={y}")
        return x, y