#!/usr/bin/env python3
"""
Simple RoboForm Test - No Unicode characters to avoid encoding issues
"""
import time
import sys
import os

# Fix encoding issues
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

from seleniumbase import SB
from training_logger import TrainingLogger

def test_roboform_simple():
    """Simple test with manual field mappings"""
    print("\n" + "="*50)
    print("ROBOFORM TEST - Manual Field Mapping")
    print("="*50)

    # Initialize logger
    logger = TrainingLogger("roboform_manual_test")

    # Test data
    test_data = {
        "first_name": "John",
        "last_name": "Smith",
        "email": "john.smith@test.com",
        "company": "FormAI Technologies"
    }

    print("Starting browser...")

    try:
        with SB(uc=True, headed=True) as sb:
            print("Navigating to RoboForm test page...")
            sb.activate_cdp_mode("https://www.roboform.com/filling-test-all-fields")

            print("Page loaded, testing field filling...")

            # Test basic fields with known selectors
            fields_to_test = [
                ("first_name", "[ref=e27]", "John"),
                ("last_name", "[ref=e35]", "Smith"),
                ("email", "[ref=e91]", "john.smith@test.com"),
                ("company", "[ref=e43]", "FormAI Technologies")
            ]

            successful = 0
            total = len(fields_to_test)

            for field_name, selector, value in fields_to_test:
                start_time = time.time()

                try:
                    print(f"  Filling {field_name}: {value}")

                    if sb.cdp.is_element_present(selector):
                        sb.cdp.click(selector)
                        time.sleep(0.2)
                        sb.cdp.clear_input(selector)
                        time.sleep(0.1)
                        sb.cdp.type(selector, value)

                        interaction_time = (time.time() - start_time) * 1000

                        # Log success
                        logger.log_successful_fill(
                            url="https://www.roboform.com/filling-test-all-fields",
                            selector=selector,
                            field_type=field_name,
                            value=value,
                            method="cdp_type",
                            time_ms=interaction_time
                        )

                        print(f"    [OK] Success ({interaction_time:.1f}ms)")
                        successful += 1
                        time.sleep(0.5)  # Human-like pause
                    else:
                        print(f"    [ERROR] Element not found: {selector}")

                except Exception as e:
                    interaction_time = (time.time() - start_time) * 1000
                    logger.log_failed_fill(
                        url="https://www.roboform.com/filling-test-all-fields",
                        selector=selector,
                        field_type=field_name,
                        error_msg=str(e),
                        method="cdp_type",
                        time_ms=interaction_time
                    )
                    print(f"    [ERROR] Failed: {e}")

            # Take screenshot
            try:
                screenshot_path = f"training_data/roboform_simple_test_{int(time.time())}.png"
                sb.save_screenshot(screenshot_path)
                print(f"Screenshot saved: {screenshot_path}")
            except:
                pass

            print(f"\n" + "="*50)
            print("TEST RESULTS")
            print("="*50)
            print(f"Total Fields: {total}")
            print(f"Successful: {successful}")
            print(f"Failed: {total - successful}")
            print(f"Success Rate: {(successful/total)*100:.1f}%")

            # Save training data
            logger.save_training_data()
            logger.print_summary()

            return successful > 0

    except Exception as e:
        print(f"[ERROR] Browser error: {e}")
        return False

if __name__ == "__main__":
    success = test_roboform_simple()
    if success:
        print("\n[SUCCESS] Test completed!")
    else:
        print("\n[ERROR] Test failed!")

    exit(0 if success else 1)