#!/usr/bin/env python3
"""
RoboForm Test Script - Comprehensive form filling test with training data collection
"""
import time
import asyncio
from datetime import datetime
from seleniumbase import SB
from training_logger import TrainingLogger
import json
from pathlib import Path

class RoboFormTester:
    """Comprehensive tester for RoboForm using SeleniumBase CDP mode"""

    def __init__(self, use_stealth: bool = True, headless: bool = False):
        self.use_stealth = use_stealth
        self.headless = headless
        self.sb = None
        self.logger = TrainingLogger(f"roboform_test_{int(time.time())}")
        self.url = "https://www.roboform.com/filling-test-all-fields"

        # Test profile data
        self.test_profile = {
            "title": "Mr.",
            "first_name": "John",
            "middle_initial": "D",
            "last_name": "Smith",
            "full_name": "John D Smith",
            "company": "FormAI Technologies",
            "position": "Software Engineer",
            "address_line_1": "123 Main Street",
            "address_line_2": "Suite 456",
            "city": "San Francisco",
            "state": "California",
            "country": "United States",
            "zip": "94105",
            "home_phone": "(555) 123-4567",
            "work_phone": "(555) 987-6543",
            "fax": "(555) 111-2222",
            "cell_phone": "(555) 444-5555",
            "email": "john.smith@formai.test",
            "website": "https://www.formai.test",
            "user_id": "johnsmith123",
            "password": "SecurePass123!",
            "credit_card_type": "Visa (Preferred)",
            "credit_card_number": "4111111111111111",
            "card_verification_code": "123",
            "card_expiration_month": "12",
            "card_expiration_year": "2027",
            "card_user_name": "John D Smith",
            "card_issuing_bank": "Bank of America",
            "card_customer_service": "(800) 555-0199",
            "sex": "Male",
            "social_security": "123-45-6789",
            "driver_license": "D123456789",
            "birth_month": "Mar",
            "birth_day": "15",
            "birth_year": "1990",
            "age": "34",
            "birth_place": "New York",
            "income": "$75000",
            "custom_message": "This is a test automation message",
            "comments": "Automated form filling test using SeleniumBase CDP mode for stealth automation."
        }

        # Field mapping based on browser analysis
        self.field_mappings = {
            # Personal Information
            "title": "[ref=e23]",
            "first_name": "[ref=e27]",
            "middle_initial": "[ref=e31]",
            "last_name": "[ref=e35]",
            "full_name": "[ref=e39]",
            "company": "[ref=e43]",
            "position": "[ref=e47]",

            # Address
            "address_line_1": "[ref=e51]",
            "address_line_2": "[ref=e55]",
            "city": "[ref=e59]",
            "state": "[ref=e63]",
            "country": "[ref=e67]",
            "zip": "[ref=e71]",

            # Contact
            "home_phone": "[ref=e75]",
            "work_phone": "[ref=e79]",
            "fax": "[ref=e83]",
            "cell_phone": "[ref=e87]",
            "email": "[ref=e91]",
            "website": "[ref=e95]",

            # Security
            "user_id": "[ref=e100]",
            "password": "[ref=e104]",

            # Payment - Dropdowns
            "credit_card_type": "[ref=e108]",
            "card_expiration_month": "[ref=e120]",
            "card_expiration_year": "[ref=e121]",

            # Payment - Text fields
            "credit_card_number": "[ref=e112]",
            "card_verification_code": "[ref=e116]",
            "card_user_name": "[ref=e125]",
            "card_issuing_bank": "[ref=e129]",
            "card_customer_service": "[ref=e133]",

            # Demographics
            "sex": "[ref=e137]",
            "social_security": "[ref=e141]",
            "driver_license": "[ref=e145]",

            # Birth Date - Dropdowns
            "birth_month": "[ref=e149]",
            "birth_day": "[ref=e150]",
            "birth_year": "[ref=e151]",

            # Other
            "age": "[ref=e155]",
            "birth_place": "[ref=e159]",
            "income": "[ref=e163]",
            "custom_message": "[ref=e167]",
            "comments": "[ref=e171]"
        }

    def start_browser(self):
        """Initialize SeleniumBase with CDP mode"""
        try:
            print(f"\n🚀 Starting browser (stealth: {self.use_stealth})...")

            # Initialize SeleniumBase with optimized settings
            self.sb = SB(
                uc=self.use_stealth,  # Undetected Chrome mode
                headed=not self.headless,  # Show browser window
                incognito=True,  # Use incognito mode
                block_images=False,  # Load images (more human-like)
                do_not_track=True,  # Enable do not track
                disable_gpu=False  # Keep GPU for performance
            )

            self.sb.__enter__()

            # Navigate to RoboForm test page
            print(f"🌐 Navigating to {self.url}...")

            if self.use_stealth:
                # Activate CDP mode for maximum stealth
                self.sb.activate_cdp_mode(self.url)
                print("✓ CDP mode activated for stealth automation")
            else:
                self.sb.open(self.url)

            # Wait for page to fully load
            time.sleep(3)
            print("✓ Browser started and page loaded")
            return True

        except Exception as e:
            print(f"❌ Error starting browser: {e}")
            return False

    def fill_text_field(self, field_name: str, selector: str, value: str, field_type: str = "text") -> bool:
        """Fill a text field using CDP mode with logging"""
        start_time = time.time()

        try:
            print(f"  📝 Filling {field_name}: '{value}'")

            if self.use_stealth and hasattr(self.sb, 'cdp'):
                # Use CDP methods for stealth
                if self.sb.cdp.is_element_present(selector):
                    # Click field to focus
                    self.sb.cdp.click(selector)
                    time.sleep(0.2)  # Human-like pause

                    # Clear any existing content
                    self.sb.cdp.clear_input(selector)
                    time.sleep(0.1)

                    # Type with human-like speed
                    self.sb.cdp.type(selector, value)

                    interaction_time = (time.time() - start_time) * 1000

                    # Log successful interaction
                    self.logger.log_successful_fill(
                        url=self.url,
                        selector=selector,
                        field_type=field_type,
                        value=value,
                        method="cdp_type",
                        time_ms=interaction_time,
                        auto_detected=True,
                        confidence=1.0,
                        detection_method="manual_mapping"
                    )

                    print(f"    ✓ Success ({interaction_time:.1f}ms)")
                    time.sleep(0.3)  # Pause before next field
                    return True
                else:
                    raise Exception(f"Element not found: {selector}")
            else:
                # Fallback to standard Selenium
                element = self.sb.find_element(selector)
                element.clear()
                element.send_keys(value)

                interaction_time = (time.time() - start_time) * 1000
                self.logger.log_successful_fill(
                    url=self.url,
                    selector=selector,
                    field_type=field_type,
                    value=value,
                    method="selenium_type",
                    time_ms=interaction_time
                )

                print(f"    ✓ Success with fallback ({interaction_time:.1f}ms)")
                return True

        except Exception as e:
            interaction_time = (time.time() - start_time) * 1000
            error_msg = str(e)

            # Log failed interaction
            self.logger.log_failed_fill(
                url=self.url,
                selector=selector,
                field_type=field_type,
                error_msg=error_msg,
                method="cdp_type" if self.use_stealth else "selenium_type",
                time_ms=interaction_time
            )

            print(f"    ❌ Failed: {error_msg}")
            return False

    def fill_dropdown_field(self, field_name: str, selector: str, value: str, field_type: str = "select") -> bool:
        """Fill a dropdown field with logging"""
        start_time = time.time()

        try:
            print(f"  📋 Selecting {field_name}: '{value}'")

            if self.use_stealth and hasattr(self.sb, 'cdp'):
                # Use CDP for dropdown selection
                if self.sb.cdp.is_element_present(selector):
                    # Click dropdown to open
                    self.sb.cdp.click(selector)
                    time.sleep(0.5)  # Wait for dropdown to open

                    # Select option by text
                    self.sb.cdp.select_option_by_text(selector, value)

                    interaction_time = (time.time() - start_time) * 1000

                    self.logger.log_successful_fill(
                        url=self.url,
                        selector=selector,
                        field_type=field_type,
                        value=value,
                        method="cdp_select",
                        time_ms=interaction_time,
                        auto_detected=True,
                        confidence=1.0
                    )

                    print(f"    ✓ Success ({interaction_time:.1f}ms)")
                    time.sleep(0.3)
                    return True
                else:
                    raise Exception(f"Dropdown not found: {selector}")
            else:
                # Fallback to standard Selenium
                self.sb.select_option_by_text(selector, value)

                interaction_time = (time.time() - start_time) * 1000
                self.logger.log_successful_fill(
                    url=self.url,
                    selector=selector,
                    field_type=field_type,
                    value=value,
                    method="selenium_select",
                    time_ms=interaction_time
                )

                print(f"    ✓ Success with fallback ({interaction_time:.1f}ms)")
                return True

        except Exception as e:
            interaction_time = (time.time() - start_time) * 1000
            error_msg = str(e)

            self.logger.log_failed_fill(
                url=self.url,
                selector=selector,
                field_type=field_type,
                error_msg=error_msg,
                method="cdp_select" if self.use_stealth else "selenium_select",
                time_ms=interaction_time
            )

            print(f"    ❌ Failed: {error_msg}")
            return False

    def run_comprehensive_test(self) -> bool:
        """Run comprehensive form filling test"""
        print(f"\n{'='*60}")
        print(f"🧪 ROBOFORM COMPREHENSIVE TEST")
        print(f"{'='*60}")
        print(f"Stealth Mode: {self.use_stealth}")
        print(f"Test Profile: {self.test_profile['first_name']} {self.test_profile['last_name']}")
        print(f"URL: {self.url}")

        if not self.start_browser():
            return False

        try:
            total_fields = len(self.field_mappings)
            successful_fields = 0

            print(f"\n📋 Filling {total_fields} form fields...")

            # Text fields
            text_fields = [
                ("title", "title"), ("first_name", "first_name"), ("middle_initial", "middle_initial"),
                ("last_name", "last_name"), ("full_name", "full_name"), ("company", "company"),
                ("position", "position"), ("address_line_1", "address"), ("address_line_2", "address"),
                ("city", "city"), ("state", "state"), ("country", "country"), ("zip", "zip"),
                ("home_phone", "phone"), ("work_phone", "phone"), ("fax", "phone"), ("cell_phone", "phone"),
                ("email", "email"), ("website", "url"), ("user_id", "username"), ("password", "password"),
                ("credit_card_number", "credit_card"), ("card_verification_code", "cvv"),
                ("card_user_name", "name"), ("card_issuing_bank", "text"), ("card_customer_service", "phone"),
                ("sex", "text"), ("social_security", "ssn"), ("driver_license", "text"),
                ("age", "number"), ("birth_place", "text"), ("income", "text"),
                ("custom_message", "text"), ("comments", "textarea")
            ]

            # Fill text fields
            print(f"\n1️⃣ Filling text fields...")
            for field_key, field_type in text_fields:
                if field_key in self.field_mappings and field_key in self.test_profile:
                    selector = self.field_mappings[field_key]
                    value = self.test_profile[field_key]

                    if self.fill_text_field(field_key, selector, value, field_type):
                        successful_fields += 1

            # Fill dropdown fields
            print(f"\n2️⃣ Filling dropdown fields...")
            dropdown_fields = [
                ("credit_card_type", "credit_card_type"),
                ("card_expiration_month", "month"),
                ("card_expiration_year", "year"),
                ("birth_month", "month"),
                ("birth_day", "day"),
                ("birth_year", "year")
            ]

            for field_key, field_type in dropdown_fields:
                if field_key in self.field_mappings and field_key in self.test_profile:
                    selector = self.field_mappings[field_key]
                    value = self.test_profile[field_key]

                    if self.fill_dropdown_field(field_key, selector, value, field_type):
                        successful_fields += 1

            # Take screenshot for verification
            try:
                screenshot_path = f"training_data/roboform_test_{int(time.time())}.png"
                self.sb.save_screenshot(screenshot_path)
                print(f"📸 Screenshot saved: {screenshot_path}")
            except:
                pass

            # Print results
            success_rate = (successful_fields / total_fields) * 100

            print(f"\n{'='*60}")
            print(f"📊 TEST RESULTS")
            print(f"{'='*60}")
            print(f"Total Fields: {total_fields}")
            print(f"Successful: {successful_fields}")
            print(f"Failed: {total_fields - successful_fields}")
            print(f"Success Rate: {success_rate:.1f}%")

            return successful_fields > 0

        except Exception as e:
            print(f"❌ Test execution error: {e}")
            return False

        finally:
            self.close_browser()

    def close_browser(self):
        """Close browser and save training data"""
        try:
            if self.sb:
                self.sb.__exit__(None, None, None)
                print("✓ Browser closed")

            # Save training data and print summary
            self.logger.save_training_data()
            self.logger.print_summary()

        except Exception as e:
            print(f"Warning: Error closing browser: {e}")

def main():
    """Main test runner"""
    import argparse

    parser = argparse.ArgumentParser(description="RoboForm Comprehensive Test")
    parser.add_argument("--no-stealth", action="store_true", help="Disable stealth mode")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    args = parser.parse_args()

    tester = RoboFormTester(
        use_stealth=not args.no_stealth,
        headless=args.headless
    )

    success = tester.run_comprehensive_test()

    if success:
        print(f"\n✅ Test completed successfully!")
        print(f"Training data collected and saved.")
    else:
        print(f"\n❌ Test failed or no fields filled.")

    return 0 if success else 1

if __name__ == "__main__":
    exit(main())