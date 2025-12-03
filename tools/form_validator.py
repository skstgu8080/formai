"""
Form Validator Module

Validates form data before submission to prevent errors.
- Detects required fields
- Validates email format
- Validates phone number format
- Checks password requirements
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ValidationError:
    """Represents a validation error"""
    field_name: str
    field_selector: str
    error_type: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of form validation"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    validated_fields: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": [
                {
                    "field_name": e.field_name,
                    "field_selector": e.field_selector,
                    "error_type": e.error_type,
                    "message": e.message,
                    "suggestion": e.suggestion
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "field_name": w.field_name,
                    "field_selector": w.field_selector,
                    "error_type": w.error_type,
                    "message": w.message,
                    "suggestion": w.suggestion
                }
                for w in self.warnings
            ],
            "validated_fields": self.validated_fields
        }


class FormValidator:
    """Validates form data against common requirements"""

    # Email regex pattern (RFC 5322 simplified)
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )

    # Phone patterns (various formats)
    PHONE_PATTERNS = [
        re.compile(r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'),  # US
        re.compile(r'^\+?[0-9]{10,15}$'),  # International
        re.compile(r'^[0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$'),  # Simple format
    ]

    # Password strength requirements
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_PATTERNS = {
        'uppercase': re.compile(r'[A-Z]'),
        'lowercase': re.compile(r'[a-z]'),
        'digit': re.compile(r'[0-9]'),
        'special': re.compile(r'[!@#$%^&*(),.?":{}|<>]'),
    }

    # ZIP code patterns
    ZIP_PATTERNS = {
        'US': re.compile(r'^\d{5}(-\d{4})?$'),
        'UK': re.compile(r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$', re.IGNORECASE),
        'CA': re.compile(r'^[A-Z]\d[A-Z]\s*\d[A-Z]\d$', re.IGNORECASE),
    }

    # Credit card patterns (basic validation)
    CREDIT_CARD_PATTERN = re.compile(r'^[0-9]{13,19}$')

    # SSN pattern
    SSN_PATTERN = re.compile(r'^\d{3}-?\d{2}-?\d{4}$')

    def __init__(self):
        # Field types that require specific validation
        self.email_fields = ['email', 'e-mail', 'emailaddress', 'email_address']
        self.phone_fields = ['phone', 'telephone', 'tel', 'mobile', 'cell', 'cellphone', 'homephone', 'workphone']
        self.password_fields = ['password', 'pass', 'pwd', 'passwd']
        self.zip_fields = ['zip', 'zipcode', 'postal', 'postalcode', 'postcode']
        self.name_fields = ['firstname', 'lastname', 'name', 'fullname', 'first_name', 'last_name']

    def validate_recording_with_profile(
        self,
        recording: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a recording's field mappings against profile data.

        Args:
            recording: Recording with field_mappings
            profile: Profile data to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []
        validated = 0

        field_mappings = recording.get('field_mappings', [])

        for mapping in field_mappings:
            field_name = mapping.get('field_name', '').lower()
            field_selector = mapping.get('field_selector', '')
            profile_mapping = mapping.get('profile_mapping', '')
            field_type = mapping.get('field_type', 'text')

            if not profile_mapping:
                # Field not mapped - warning
                warnings.append(ValidationError(
                    field_name=mapping.get('field_name', 'Unknown'),
                    field_selector=field_selector,
                    error_type='unmapped',
                    message='Field is not mapped to profile data',
                    suggestion='Edit the recording to map this field'
                ))
                continue

            # Get value from profile
            value = self._get_profile_value(profile, profile_mapping)

            if value is None or value == '':
                # Check if this is likely a required field
                if self._is_likely_required(field_name, field_type):
                    errors.append(ValidationError(
                        field_name=mapping.get('field_name', 'Unknown'),
                        field_selector=field_selector,
                        error_type='missing_required',
                        message=f'Required field "{profile_mapping}" is empty in profile',
                        suggestion=f'Add {profile_mapping} to your profile'
                    ))
                else:
                    warnings.append(ValidationError(
                        field_name=mapping.get('field_name', 'Unknown'),
                        field_selector=field_selector,
                        error_type='missing_value',
                        message=f'Field "{profile_mapping}" is empty in profile',
                        suggestion=f'Consider adding {profile_mapping} to your profile'
                    ))
                continue

            validated += 1

            # Type-specific validation
            validation_error = self._validate_field_value(
                field_name=mapping.get('field_name', 'Unknown'),
                field_selector=field_selector,
                profile_mapping=profile_mapping,
                value=str(value),
                field_type=field_type
            )

            if validation_error:
                errors.append(validation_error)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            validated_fields=validated
        )

    def _get_profile_value(self, profile: Dict[str, Any], field_path: str) -> Optional[str]:
        """Get a value from profile using field path"""
        # Try direct access
        if field_path in profile:
            return profile[field_path]

        # Try nested data
        data = profile.get('data', {})
        if isinstance(data, dict) and field_path in data:
            return data[field_path]

        # Try case-insensitive match
        field_lower = field_path.lower()
        for key, value in profile.items():
            if key.lower() == field_lower:
                return value

        return None

    def _is_likely_required(self, field_name: str, field_type: str) -> bool:
        """Determine if a field is likely required based on name and type"""
        field_lower = field_name.lower().replace(' ', '').replace('-', '').replace('_', '')

        # Common required fields
        required_patterns = [
            'firstname', 'lastname', 'email', 'phone',
            'address', 'city', 'state', 'zip', 'country',
            'username', 'password'
        ]

        for pattern in required_patterns:
            if pattern in field_lower:
                return True

        # Email and password types are typically required
        if field_type in ['email', 'password']:
            return True

        return False

    def _validate_field_value(
        self,
        field_name: str,
        field_selector: str,
        profile_mapping: str,
        value: str,
        field_type: str
    ) -> Optional[ValidationError]:
        """Validate a field value based on its type"""

        profile_lower = profile_mapping.lower()

        # Email validation
        if profile_lower in self.email_fields or field_type == 'email':
            if not self.validate_email(value):
                return ValidationError(
                    field_name=field_name,
                    field_selector=field_selector,
                    error_type='invalid_email',
                    message=f'Invalid email format: "{value}"',
                    suggestion='Use format: example@domain.com'
                )

        # Phone validation
        elif profile_lower in self.phone_fields or field_type == 'tel':
            if not self.validate_phone(value):
                return ValidationError(
                    field_name=field_name,
                    field_selector=field_selector,
                    error_type='invalid_phone',
                    message=f'Invalid phone format: "{value}"',
                    suggestion='Use format: (123) 456-7890 or +1234567890'
                )

        # Password validation
        elif profile_lower in self.password_fields or field_type == 'password':
            password_errors = self.validate_password(value)
            if password_errors:
                return ValidationError(
                    field_name=field_name,
                    field_selector=field_selector,
                    error_type='weak_password',
                    message=f'Password does not meet requirements: {", ".join(password_errors)}',
                    suggestion='Use at least 8 characters with uppercase, lowercase, and numbers'
                )

        # ZIP code validation
        elif profile_lower in self.zip_fields:
            if not self.validate_zip(value):
                return ValidationError(
                    field_name=field_name,
                    field_selector=field_selector,
                    error_type='invalid_zip',
                    message=f'Invalid ZIP code format: "{value}"',
                    suggestion='US format: 12345 or 12345-6789'
                )

        # Name validation (basic - just check it's not empty or too short)
        elif profile_lower in self.name_fields:
            if len(value.strip()) < 2:
                return ValidationError(
                    field_name=field_name,
                    field_selector=field_selector,
                    error_type='invalid_name',
                    message=f'Name is too short: "{value}"',
                    suggestion='Enter a valid name with at least 2 characters'
                )

        return None

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email:
            return False
        return bool(self.EMAIL_PATTERN.match(email.strip()))

    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        if not phone:
            return False
        # Remove common formatting characters for validation
        cleaned = re.sub(r'[\s\-\.\(\)]', '', phone)
        return any(pattern.match(cleaned) for pattern in self.PHONE_PATTERNS)

    def validate_password(self, password: str) -> List[str]:
        """
        Validate password strength.
        Returns list of unmet requirements.
        """
        errors = []

        if len(password) < self.PASSWORD_MIN_LENGTH:
            errors.append(f'at least {self.PASSWORD_MIN_LENGTH} characters')

        if not self.PASSWORD_PATTERNS['uppercase'].search(password):
            errors.append('uppercase letter')

        if not self.PASSWORD_PATTERNS['lowercase'].search(password):
            errors.append('lowercase letter')

        if not self.PASSWORD_PATTERNS['digit'].search(password):
            errors.append('digit')

        return errors

    def validate_zip(self, zip_code: str, country: str = 'US') -> bool:
        """Validate ZIP/postal code format"""
        if not zip_code:
            return False

        cleaned = zip_code.strip()

        # Try specified country pattern
        if country.upper() in self.ZIP_PATTERNS:
            if self.ZIP_PATTERNS[country.upper()].match(cleaned):
                return True

        # Try all patterns
        for pattern in self.ZIP_PATTERNS.values():
            if pattern.match(cleaned):
                return True

        return False

    def validate_credit_card(self, card_number: str) -> bool:
        """Basic credit card number validation (Luhn algorithm)"""
        if not card_number:
            return False

        # Remove spaces and dashes
        cleaned = re.sub(r'[\s\-]', '', card_number)

        if not self.CREDIT_CARD_PATTERN.match(cleaned):
            return False

        # Luhn algorithm
        digits = [int(d) for d in cleaned]
        checksum = 0

        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def validate_ssn(self, ssn: str) -> bool:
        """Validate SSN format"""
        if not ssn:
            return False
        return bool(self.SSN_PATTERN.match(ssn.strip()))


# Global instance
_validator = None

def get_validator() -> FormValidator:
    """Get or create global FormValidator instance"""
    global _validator
    if _validator is None:
        _validator = FormValidator()
    return _validator
