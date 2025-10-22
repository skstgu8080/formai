#!/usr/bin/env python3
"""
Enhanced Field Detector - Improved field detection based on training data and SeleniumBase best practices
"""
import re
from typing import Dict, List, Optional, Tuple, Any
from seleniumbase import SB
import time

class EnhancedFieldDetector:
    """Advanced field detection using multiple strategies and training data insights"""

    def __init__(self, sb_instance: SB):
        self.sb = sb_instance
        self.confidence_threshold = 0.7
        self.detection_strategies = [
            self._detect_by_reference,
            self._detect_by_id,
            self._detect_by_name,
            self._detect_by_placeholder,
            self._detect_by_label,
            self._detect_by_pattern_matching,
            self._detect_by_position_context
        ]

        # Enhanced field patterns based on real-world forms
        self.field_patterns = {
            'email': {
                'patterns': [
                    r'email', r'e-?mail', r'mail', r'@', r'username',
                    r'login', r'account', r'user'
                ],
                'input_types': ['email', 'text'],
                'selectors': [
                    'input[type="email"]',
                    'input[name*="email" i]',
                    'input[id*="email" i]',
                    'input[placeholder*="email" i]'
                ]
            },
            'first_name': {
                'patterns': [
                    r'first.?name', r'fname', r'given.?name', r'forename',
                    r'christian.?name', r'prenom'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="first" i]',
                    'input[id*="fname" i]',
                    'input[placeholder*="first" i]'
                ]
            },
            'last_name': {
                'patterns': [
                    r'last.?name', r'lname', r'surname', r'family.?name',
                    r'lastname', r'nom'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="last" i]',
                    'input[id*="lname" i]',
                    'input[placeholder*="last" i]'
                ]
            },
            'full_name': {
                'patterns': [
                    r'full.?name', r'name', r'your.?name', r'display.?name',
                    r'complete.?name', r'real.?name'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="name" i]:not([name*="first" i]):not([name*="last" i])',
                    'input[id*="fullname" i]'
                ]
            },
            'phone': {
                'patterns': [
                    r'phone', r'tel', r'mobile', r'cell', r'telephone',
                    r'contact', r'number'
                ],
                'input_types': ['tel', 'text'],
                'selectors': [
                    'input[type="tel"]',
                    'input[name*="phone" i]',
                    'input[id*="tel" i]'
                ]
            },
            'address': {
                'patterns': [
                    r'address', r'street', r'addr', r'location',
                    r'line.?1', r'address.?1'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="address" i]',
                    'input[id*="addr" i]',
                    'input[placeholder*="address" i]'
                ]
            },
            'city': {
                'patterns': [
                    r'city', r'town', r'locality', r'ville'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="city" i]',
                    'input[id*="city" i]'
                ]
            },
            'state': {
                'patterns': [
                    r'state', r'province', r'region', r'county'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="state" i]',
                    'select[name*="state" i]',
                    'input[id*="province" i]'
                ]
            },
            'zip': {
                'patterns': [
                    r'zip', r'postal', r'postcode', r'zipcode',
                    r'post.?code'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="zip" i]',
                    'input[name*="postal" i]',
                    'input[id*="postcode" i]'
                ]
            },
            'country': {
                'patterns': [
                    r'country', r'nation', r'pays'
                ],
                'input_types': ['text'],
                'selectors': [
                    'select[name*="country" i]',
                    'input[name*="country" i]'
                ]
            },
            'password': {
                'patterns': [
                    r'password', r'pass', r'pwd', r'secret',
                    r'mot.?de.?passe'
                ],
                'input_types': ['password'],
                'selectors': [
                    'input[type="password"]',
                    'input[name*="password" i]',
                    'input[id*="pwd" i]'
                ]
            },
            'username': {
                'patterns': [
                    r'username', r'user', r'login', r'account',
                    r'userid', r'user.?id'
                ],
                'input_types': ['text', 'email'],
                'selectors': [
                    'input[name*="user" i]',
                    'input[id*="login" i]',
                    'input[placeholder*="username" i]'
                ]
            },
            'company': {
                'patterns': [
                    r'company', r'organization', r'employer',
                    r'business', r'firm', r'corp'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="company" i]',
                    'input[id*="org" i]'
                ]
            },
            'position': {
                'patterns': [
                    r'position', r'title', r'job', r'role',
                    r'occupation', r'profession'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="position" i]',
                    'input[name*="title" i]',
                    'input[id*="job" i]'
                ]
            },
            'credit_card': {
                'patterns': [
                    r'card.?number', r'credit.?card', r'cc.?number',
                    r'card.?no', r'pan'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="card" i]',
                    'input[id*="credit" i]',
                    'input[placeholder*="card" i]'
                ]
            },
            'cvv': {
                'patterns': [
                    r'cvv', r'cvc', r'security.?code', r'card.?code',
                    r'verification'
                ],
                'input_types': ['text'],
                'selectors': [
                    'input[name*="cvv" i]',
                    'input[name*="cvc" i]',
                    'input[id*="security" i]'
                ]
            },
            'date_of_birth': {
                'patterns': [
                    r'birth', r'dob', r'birthday', r'born',
                    r'date.?of.?birth'
                ],
                'input_types': ['date', 'text'],
                'selectors': [
                    'input[type="date"]',
                    'select[name*="birth" i]',
                    'input[name*="dob" i]'
                ]
            }
        }

    def detect_form_fields(self, url: str) -> List[Dict[str, Any]]:
        """Detect all form fields on the current page with confidence scores"""
        detected_fields = []

        try:
            # Get all input elements
            inputs = self.sb.find_elements('input, textarea, select')

            for element in inputs:
                field_info = self._extract_element_info(element)

                # Try each detection strategy
                best_match = None
                highest_confidence = 0

                for strategy in self.detection_strategies:
                    try:
                        field_type, confidence = strategy(field_info)
                        if confidence > highest_confidence:
                            highest_confidence = confidence
                            best_match = field_type
                    except:
                        continue

                if best_match and highest_confidence >= self.confidence_threshold:
                    field_info.update({
                        'detected_type': best_match,
                        'confidence': highest_confidence,
                        'url': url
                    })
                    detected_fields.append(field_info)

            return detected_fields

        except Exception as e:
            print(f"Error detecting form fields: {e}")
            return []

    def _extract_element_info(self, element) -> Dict[str, Any]:
        """Extract comprehensive information about a form element"""
        try:
            return {
                'element': element,
                'tag_name': element.tag_name.lower(),
                'type': element.get_attribute('type') or 'text',
                'name': element.get_attribute('name') or '',
                'id': element.get_attribute('id') or '',
                'class': element.get_attribute('class') or '',
                'placeholder': element.get_attribute('placeholder') or '',
                'value': element.get_attribute('value') or '',
                'required': element.get_attribute('required') is not None,
                'visible': element.is_displayed(),
                'enabled': element.is_enabled(),
                'selector': self._generate_selector(element)
            }
        except:
            return {'element': element, 'tag_name': 'unknown'}

    def _generate_selector(self, element) -> str:
        """Generate a reliable CSS selector for an element"""
        try:
            # Try ID first (most reliable)
            elem_id = element.get_attribute('id')
            if elem_id:
                return f"#{elem_id}"

            # Try name attribute
            name = element.get_attribute('name')
            if name:
                return f"[name='{name}']"

            # Try class with tag
            class_name = element.get_attribute('class')
            if class_name:
                first_class = class_name.split()[0]
                return f"{element.tag_name.lower()}.{first_class}"

            # Fallback to tag with attributes
            tag = element.tag_name.lower()
            elem_type = element.get_attribute('type')
            if elem_type:
                return f"{tag}[type='{elem_type}']"

            return tag

        except:
            return 'input'

    def _detect_by_reference(self, field_info: Dict) -> Tuple[Optional[str], float]:
        """Detect field type by reference attribute (browser-specific)"""
        # This would be used for browser automation frameworks that provide ref attributes
        # For now, return low confidence
        return None, 0.0

    def _detect_by_id(self, field_info: Dict) -> Tuple[Optional[str], float]:
        """Detect field type by ID attribute"""
        element_id = field_info.get('id', '').lower()

        if not element_id:
            return None, 0.0

        for field_type, config in self.field_patterns.items():
            for pattern in config['patterns']:
                if re.search(pattern, element_id):
                    confidence = 0.9 if pattern in element_id else 0.7
                    return field_type, confidence

        return None, 0.0

    def _detect_by_name(self, field_info: Dict) -> Tuple[Optional[str], float]:
        """Detect field type by name attribute"""
        name = field_info.get('name', '').lower()

        if not name:
            return None, 0.0

        for field_type, config in self.field_patterns.items():
            for pattern in config['patterns']:
                if re.search(pattern, name):
                    confidence = 0.85 if pattern in name else 0.65
                    return field_type, confidence

        return None, 0.0

    def _detect_by_placeholder(self, field_info: Dict) -> Tuple[Optional[str], float]:
        """Detect field type by placeholder text"""
        placeholder = field_info.get('placeholder', '').lower()

        if not placeholder:
            return None, 0.0

        for field_type, config in self.field_patterns.items():
            for pattern in config['patterns']:
                if re.search(pattern, placeholder):
                    confidence = 0.8 if pattern in placeholder else 0.6
                    return field_type, confidence

        return None, 0.0

    def _detect_by_label(self, field_info: Dict) -> Tuple[Optional[str], float]:
        """Detect field type by associated label"""
        try:
            element = field_info.get('element')
            if not element:
                return None, 0.0

            # Find associated label
            label_text = ""

            # Try to find label by 'for' attribute
            element_id = field_info.get('id')
            if element_id:
                try:
                    label = self.sb.find_element(f'label[for="{element_id}"]')
                    label_text = label.text.lower()
                except:
                    pass

            # Try to find parent label
            if not label_text:
                try:
                    parent = element.find_element_by_xpath('..')
                    if parent.tag_name.lower() == 'label':
                        label_text = parent.text.lower()
                except:
                    pass

            # Try to find preceding text or label
            if not label_text:
                try:
                    preceding = element.find_element_by_xpath('./preceding-sibling::*[1]')
                    if preceding.tag_name.lower() in ['label', 'span', 'div']:
                        label_text = preceding.text.lower()
                except:
                    pass

            if label_text:
                for field_type, config in self.field_patterns.items():
                    for pattern in config['patterns']:
                        if re.search(pattern, label_text):
                            confidence = 0.75 if pattern in label_text else 0.55
                            return field_type, confidence

        except:
            pass

        return None, 0.0

    def _detect_by_pattern_matching(self, field_info: Dict) -> Tuple[Optional[str], float]:
        """Detect field type by combining multiple attributes with pattern matching"""
        # Combine all text attributes
        combined_text = " ".join([
            field_info.get('name', ''),
            field_info.get('id', ''),
            field_info.get('class', ''),
            field_info.get('placeholder', '')
        ]).lower()

        if not combined_text.strip():
            return None, 0.0

        best_match = None
        highest_score = 0

        for field_type, config in self.field_patterns.items():
            score = 0
            matches = 0

            for pattern in config['patterns']:
                if re.search(pattern, combined_text):
                    matches += 1
                    # Weight by pattern specificity
                    score += len(pattern) / 10

            if matches > 0:
                # Normalize score by number of patterns
                normalized_score = min(score / len(config['patterns']), 1.0)

                # Boost if input type matches expected types
                input_type = field_info.get('type', '')
                if input_type in config.get('input_types', []):
                    normalized_score += 0.2

                if normalized_score > highest_score:
                    highest_score = normalized_score
                    best_match = field_type

        return best_match, min(highest_score, 1.0) if best_match else (None, 0.0)

    def _detect_by_position_context(self, field_info: Dict) -> Tuple[Optional[str], float]:
        """Detect field type by position and context on the page"""
        # This is a simplified context detection
        # In practice, you'd analyze surrounding elements, form structure, etc.

        try:
            element = field_info.get('element')
            if not element:
                return None, 0.0

            # Get position information
            location = element.location
            size = element.size

            # Simple heuristics based on common form layouts
            # This could be enhanced with ML models trained on form layouts

            # If it's near the top, might be name/email
            if location['y'] < 200:
                if 'text' in field_info.get('type', ''):
                    return 'first_name', 0.3

            return None, 0.0

        except:
            return None, 0.0

    def create_field_mapping(self, detected_fields: List[Dict]) -> Dict[str, str]:
        """Create a mapping from field types to selectors"""
        mapping = {}

        for field in detected_fields:
            field_type = field.get('detected_type')
            selector = field.get('selector')

            if field_type and selector:
                # If multiple fields of same type, prefer higher confidence
                if field_type in mapping:
                    existing_confidence = next(
                        (f['confidence'] for f in detected_fields
                         if f.get('selector') == mapping[field_type]), 0
                    )
                    if field.get('confidence', 0) > existing_confidence:
                        mapping[field_type] = selector
                else:
                    mapping[field_type] = selector

        return mapping

    def validate_field_mapping(self, mapping: Dict[str, str]) -> Dict[str, bool]:
        """Validate that mapped selectors actually exist and are interactable"""
        validation_results = {}

        for field_type, selector in mapping.items():
            try:
                if hasattr(self.sb, 'cdp') and self.sb.cdp:
                    # Use CDP to check element presence
                    exists = self.sb.cdp.is_element_present(selector)
                    validation_results[field_type] = exists
                else:
                    # Use standard Selenium
                    element = self.sb.find_element(selector)
                    validation_results[field_type] = element.is_displayed() and element.is_enabled()
            except:
                validation_results[field_type] = False

        return validation_results

    def get_detection_report(self, detected_fields: List[Dict]) -> Dict:
        """Generate a comprehensive detection report"""
        report = {
            'total_fields': len(detected_fields),
            'detected_types': {},
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'field_details': detected_fields
        }

        for field in detected_fields:
            field_type = field.get('detected_type', 'unknown')
            confidence = field.get('confidence', 0)

            # Count by type
            report['detected_types'][field_type] = \
                report['detected_types'].get(field_type, 0) + 1

            # Count by confidence level
            if confidence >= 0.8:
                report['confidence_distribution']['high'] += 1
            elif confidence >= 0.5:
                report['confidence_distribution']['medium'] += 1
            else:
                report['confidence_distribution']['low'] += 1

        return report