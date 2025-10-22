#!/usr/bin/env python3
"""
Enhanced Field Mapper - Advanced field detection and mapping for recordings
"""
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import difflib

class EnhancedFieldMapper:
    """Enhanced field detection and mapping with ML-like intelligence"""

    def __init__(self):
        # Load existing field detection patterns from enhanced_field_detector.py
        self.field_patterns = {
            'firstName': {
                'patterns': ['first_name', 'fname', 'firstname', 'given_name', 'first-name', 'prenom'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['john', 'jane', 'mike', 'sarah', 'alex']
            },
            'lastName': {
                'patterns': ['last_name', 'lname', 'lastname', 'family_name', 'last-name', 'surname', 'nom'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['smith', 'johnson', 'brown', 'davis', 'wilson']
            },
            'fullName': {
                'patterns': ['full_name', 'fullname', 'name', 'full-name', 'display_name', 'nom_complet'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['john smith', 'jane doe', 'full name']
            },
            'email': {
                'patterns': ['email', 'e_mail', 'e-mail', 'email_address', 'emailaddress', 'mail', 'courriel'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5, 'type': 3.0},
                'types': ['input[type=email]', 'input[type=text]'],
                'common_values': ['test@example.com', 'user@domain.com', 'email@test.com']
            },
            'phone': {
                'patterns': ['phone', 'telephone', 'mobile', 'cell', 'phone_number', 'tel', 'telefone'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5, 'type': 3.0},
                'types': ['input[type=tel]', 'input[type=text]'],
                'common_values': ['(555) 123-4567', '+1 555 123 4567', '555-123-4567']
            },
            'address1': {
                'patterns': ['address', 'address1', 'street', 'address_line_1', 'street_address', 'adresse'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['123 main street', '456 oak ave', 'street address']
            },
            'address2': {
                'patterns': ['address2', 'address_line_2', 'apt', 'apartment', 'suite', 'unit'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['apt 4b', 'suite 100', 'unit 5']
            },
            'city': {
                'patterns': ['city', 'town', 'locality', 'ville'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['new york', 'san francisco', 'chicago', 'boston']
            },
            'state': {
                'patterns': ['state', 'province', 'region', 'state_province', 'etat'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['select', 'input[type=text]'],
                'common_values': ['california', 'ny', 'texas', 'florida']
            },
            'zip': {
                'patterns': ['zip', 'postal', 'postcode', 'postal_code', 'zipcode', 'code_postal'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['12345', '90210', '10001', '94105']
            },
            'country': {
                'patterns': ['country', 'nation', 'pays'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['select', 'input[type=text]'],
                'common_values': ['united states', 'usa', 'canada', 'france']
            },
            'company': {
                'patterns': ['company', 'organization', 'employer', 'business', 'entreprise'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['acme corp', 'tech solutions', 'example inc']
            },
            'username': {
                'patterns': ['username', 'user_name', 'login', 'userid', 'user_id', 'utilisateur'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['john123', 'user_name', 'testuser']
            },
            'password': {
                'patterns': ['password', 'pass', 'pwd', 'passphrase', 'mot_de_passe'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'type': 3.0},
                'types': ['input[type=password]'],
                'common_values': ['password123', 'secretpass', 'mypassword']
            },
            'creditCardNumber': {
                'patterns': ['cc_number', 'card_number', 'credit_card', 'cardnumber', 'carte_credit'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'placeholder': 1.5},
                'types': ['input[type=text]', 'input:not([type])'],
                'common_values': ['4111111111111111', '1234 5678 9012 3456']
            },
            'birthDate': {
                'patterns': ['birth_date', 'dob', 'birthday', 'date_birth', 'date_naissance'],
                'weights': {'name': 3.0, 'id': 2.5, 'class': 2.0, 'label': 2.5, 'type': 2.0},
                'types': ['input[type=date]', 'select'],
                'common_values': ['1990-01-15', 'jan 15 1990']
            }
        }

        # Context clues for better field detection
        self.context_patterns = {
            'shipping': ['shipping', 'delivery', 'ship_to', 'livraison'],
            'billing': ['billing', 'bill_to', 'payment', 'facturation'],
            'personal': ['personal', 'profile', 'account', 'personnel'],
            'contact': ['contact', 'communication'],
            'emergency': ['emergency', 'urgence'],
            'work': ['work', 'business', 'office', 'travail'],
            'home': ['home', 'personal', 'maison']
        }

        # Field validation patterns
        self.validation_patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^[\+]?[1-9]?[\d\s\-\(\)\.]{7,15}$',
            'zip': r'^[\d\-\s]{3,10}$',
            'creditCardNumber': r'^[\d\s\-]{13,19}$',
            'ssn': r'^\d{3}-?\d{2}-?\d{4}$'
        }

    def analyze_field_mapping(self, field_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze and enhance a single field mapping with confidence scoring

        Args:
            field_mapping: Original field mapping from recording

        Returns:
            Enhanced field mapping with confidence scores and alternatives
        """
        enhanced_mapping = field_mapping.copy()

        selector = field_mapping.get("field_selector", "")
        field_name = field_mapping.get("field_name", "")
        sample_value = field_mapping.get("sample_value", "")

        # Analyze selector components
        selector_analysis = self._analyze_selector(selector)

        # Get profile mapping suggestions
        mapping_suggestions = self._get_profile_mapping_suggestions(
            selector_analysis, field_name, sample_value
        )

        # Calculate confidence scores
        confidence_scores = self._calculate_confidence_scores(
            selector_analysis, field_name, sample_value, mapping_suggestions
        )

        # Enhance the mapping
        enhanced_mapping.update({
            "selector_analysis": selector_analysis,
            "mapping_suggestions": mapping_suggestions,
            "confidence_scores": confidence_scores,
            "recommended_mapping": mapping_suggestions[0] if mapping_suggestions else enhanced_mapping.get("profile_mapping"),
            "alternatives": mapping_suggestions[1:3] if len(mapping_suggestions) > 1 else [],
            "field_type_analysis": self._analyze_field_type(selector_analysis, sample_value),
            "validation_pattern": self._get_validation_pattern(mapping_suggestions[0] if mapping_suggestions else ""),
            "enhanced_confidence": max(confidence_scores.values()) if confidence_scores else 0.5
        })

        return enhanced_mapping

    def _analyze_selector(self, selector: str) -> Dict[str, Any]:
        """Analyze a CSS selector to extract meaningful information"""
        analysis = {
            "original_selector": selector,
            "element_type": "",
            "attributes": {},
            "hierarchy": [],
            "specificity": 0
        }

        # Extract element type
        element_match = re.search(r'^([a-zA-Z]+)', selector)
        if element_match:
            analysis["element_type"] = element_match.group(1)

        # Extract attributes
        attr_patterns = [
            (r'\[name=["\']([^"\']+)["\']', 'name'),
            (r'#([a-zA-Z0-9_-]+)', 'id'),
            (r'\.([a-zA-Z0-9_-]+)', 'class'),
            (r'\[id=["\']([^"\']+)["\']', 'id'),
            (r'\[class=["\']([^"\']+)["\']', 'class'),
            (r'\[type=["\']([^"\']+)["\']', 'type'),
            (r'\[placeholder=["\']([^"\']+)["\']', 'placeholder')
        ]

        for pattern, attr_name in attr_patterns:
            matches = re.findall(pattern, selector)
            if matches:
                analysis["attributes"][attr_name] = matches[0] if len(matches) == 1 else matches

        # Calculate specificity
        analysis["specificity"] = self._calculate_selector_specificity(selector)

        return analysis

    def _calculate_selector_specificity(self, selector: str) -> int:
        """Calculate CSS selector specificity score"""
        specificity = 0

        # ID selectors
        specificity += len(re.findall(r'#[a-zA-Z0-9_-]+', selector)) * 100

        # Class selectors and attribute selectors
        specificity += len(re.findall(r'\.[a-zA-Z0-9_-]+', selector)) * 10
        specificity += len(re.findall(r'\[[^\]]+\]', selector)) * 10

        # Element selectors
        specificity += len(re.findall(r'[a-zA-Z]+(?![a-zA-Z0-9_-])', selector)) * 1

        return specificity

    def _get_profile_mapping_suggestions(self, selector_analysis: Dict[str, Any],
                                       field_name: str, sample_value: str) -> List[str]:
        """Get profile mapping suggestions based on analysis"""
        suggestions = []
        scores = {}

        # Analyze each potential profile field
        for profile_field, config in self.field_patterns.items():
            score = 0

            # Check selector attributes against patterns
            for attr_name, attr_value in selector_analysis["attributes"].items():
                if attr_name in config["weights"]:
                    weight = config["weights"][attr_name]

                    # Check if any pattern matches the attribute value
                    attr_text = str(attr_value).lower()
                    for pattern in config["patterns"]:
                        if pattern in attr_text:
                            score += weight * self._calculate_pattern_match_score(pattern, attr_text)

            # Check field name against patterns
            field_name_lower = field_name.lower()
            for pattern in config["patterns"]:
                if pattern in field_name_lower:
                    score += 2.0 * self._calculate_pattern_match_score(pattern, field_name_lower)

            # Check sample value against common values
            sample_value_lower = sample_value.lower()
            for common_value in config.get("common_values", []):
                similarity = difflib.SequenceMatcher(None, sample_value_lower, common_value).ratio()
                if similarity > 0.6:
                    score += 1.0 * similarity

            # Check element type compatibility
            element_type = selector_analysis.get("element_type", "")
            if element_type and self._is_element_type_compatible(element_type, config["types"]):
                score += 1.0

            if score > 0:
                scores[profile_field] = score

        # Sort by score and return top suggestions
        sorted_suggestions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        suggestions = [field for field, score in sorted_suggestions if score > 0.5]

        return suggestions[:5]  # Return top 5 suggestions

    def _calculate_pattern_match_score(self, pattern: str, text: str) -> float:
        """Calculate how well a pattern matches text"""
        if pattern == text:
            return 1.0
        elif pattern in text:
            return 0.8
        else:
            # Use sequence matching for partial similarity
            return difflib.SequenceMatcher(None, pattern, text).ratio()

    def _is_element_type_compatible(self, element_type: str, compatible_types: List[str]) -> bool:
        """Check if element type is compatible with field type"""
        for compatible_type in compatible_types:
            if element_type in compatible_type:
                return True
        return False

    def _calculate_confidence_scores(self, selector_analysis: Dict[str, Any],
                                   field_name: str, sample_value: str,
                                   suggestions: List[str]) -> Dict[str, float]:
        """Calculate confidence scores for different aspects of field mapping"""
        scores = {}

        # Selector quality score
        scores["selector_quality"] = min(selector_analysis["specificity"] / 100.0, 1.0)

        # Name attribute presence (high confidence indicator)
        if "name" in selector_analysis["attributes"]:
            scores["name_attribute"] = 0.9
        else:
            scores["name_attribute"] = 0.1

        # Field name clarity
        if field_name and len(field_name) > 2:
            scores["field_name_clarity"] = min(len(field_name) / 20.0, 1.0)
        else:
            scores["field_name_clarity"] = 0.2

        # Mapping suggestion confidence
        if suggestions:
            # Higher confidence if we have clear suggestions
            scores["mapping_confidence"] = 0.8 if len(suggestions) >= 2 else 0.6
        else:
            scores["mapping_confidence"] = 0.3

        # Sample value validity
        if sample_value:
            scores["sample_value"] = self._validate_sample_value(sample_value, suggestions[0] if suggestions else "")
        else:
            scores["sample_value"] = 0.1

        return scores

    def _validate_sample_value(self, sample_value: str, field_type: str) -> float:
        """Validate sample value against expected patterns"""
        if not sample_value or not field_type:
            return 0.1

        pattern = self.validation_patterns.get(field_type)
        if pattern and re.match(pattern, sample_value):
            return 0.9
        elif field_type in self.field_patterns:
            # Check against common values
            common_values = self.field_patterns[field_type].get("common_values", [])
            for common_value in common_values:
                similarity = difflib.SequenceMatcher(None, sample_value.lower(), common_value.lower()).ratio()
                if similarity > 0.7:
                    return 0.7 + (similarity * 0.2)

        return 0.3

    def _analyze_field_type(self, selector_analysis: Dict[str, Any], sample_value: str) -> Dict[str, Any]:
        """Analyze the field type based on selector and value"""
        element_type = selector_analysis.get("element_type", "")
        attributes = selector_analysis.get("attributes", {})

        analysis = {
            "detected_type": "textbox",
            "html_element": element_type,
            "input_type": attributes.get("type", "text"),
            "is_select": element_type.lower() == "select",
            "is_textarea": element_type.lower() == "textarea",
            "likely_multiline": False,
            "expected_format": None
        }

        # Determine field type
        if element_type.lower() == "select":
            analysis["detected_type"] = "select"
        elif element_type.lower() == "textarea":
            analysis["detected_type"] = "textarea"
            analysis["likely_multiline"] = True
        elif attributes.get("type") == "checkbox":
            analysis["detected_type"] = "checkbox"
        elif attributes.get("type") == "radio":
            analysis["detected_type"] = "radio"
        elif attributes.get("type") == "password":
            analysis["detected_type"] = "password"
        elif attributes.get("type") == "email":
            analysis["detected_type"] = "email"
            analysis["expected_format"] = "email"
        elif attributes.get("type") == "tel":
            analysis["detected_type"] = "phone"
            analysis["expected_format"] = "phone"
        elif attributes.get("type") == "date":
            analysis["detected_type"] = "date"
            analysis["expected_format"] = "date"

        # Infer format from sample value
        if sample_value and not analysis["expected_format"]:
            analysis["expected_format"] = self._infer_format_from_value(sample_value)

        return analysis

    def _infer_format_from_value(self, value: str) -> Optional[str]:
        """Infer expected format from sample value"""
        value = value.strip()

        # Email pattern
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            return "email"

        # Phone pattern
        if re.match(r'^[\+]?[1-9]?[\d\s\-\(\)\.]{7,15}$', value):
            return "phone"

        # Date patterns
        if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
            return "date_iso"
        elif re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', value):
            return "date_us"

        # Credit card pattern
        if re.match(r'^[\d\s\-]{13,19}$', value.replace(" ", "").replace("-", "")):
            return "credit_card"

        # ZIP code pattern
        if re.match(r'^\d{5}(-\d{4})?$', value):
            return "zip_code"

        return None

    def _get_validation_pattern(self, field_type: str) -> Optional[str]:
        """Get validation regex pattern for a field type"""
        return self.validation_patterns.get(field_type)

    def enhance_recording_field_mappings(self, recording: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance all field mappings in a recording

        Args:
            recording: Recording data with field mappings

        Returns:
            Enhanced recording with improved field mappings
        """
        enhanced_recording = recording.copy()
        enhanced_mappings = []

        original_mappings = recording.get("field_mappings", [])

        for mapping in original_mappings:
            enhanced_mapping = self.analyze_field_mapping(mapping)
            enhanced_mappings.append(enhanced_mapping)

        enhanced_recording["field_mappings"] = enhanced_mappings
        enhanced_recording["enhancement_metadata"] = {
            "enhanced_at": self._get_current_timestamp(),
            "total_fields": len(enhanced_mappings),
            "high_confidence_fields": len([m for m in enhanced_mappings if m.get("enhanced_confidence", 0) > 0.7]),
            "low_confidence_fields": len([m for m in enhanced_mappings if m.get("enhanced_confidence", 0) < 0.4]),
            "enhancement_version": "1.0"
        }

        return enhanced_recording

    def suggest_field_mapping_corrections(self, recording: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Suggest corrections for field mappings with low confidence

        Args:
            recording: Recording with enhanced field mappings

        Returns:
            List of suggested corrections
        """
        suggestions = []

        field_mappings = recording.get("field_mappings", [])

        for i, mapping in enumerate(field_mappings):
            confidence = mapping.get("enhanced_confidence", 0.5)

            if confidence < 0.6:  # Low confidence threshold
                suggestion = {
                    "field_index": i,
                    "current_mapping": mapping.get("profile_mapping", ""),
                    "recommended_mapping": mapping.get("recommended_mapping", ""),
                    "alternatives": mapping.get("alternatives", []),
                    "confidence": confidence,
                    "reasons": self._analyze_low_confidence_reasons(mapping),
                    "suggested_actions": self._suggest_improvement_actions(mapping)
                }
                suggestions.append(suggestion)

        return suggestions

    def _analyze_low_confidence_reasons(self, mapping: Dict[str, Any]) -> List[str]:
        """Analyze why a mapping has low confidence"""
        reasons = []

        confidence_scores = mapping.get("confidence_scores", {})

        if confidence_scores.get("selector_quality", 0) < 0.5:
            reasons.append("Weak CSS selector (low specificity)")

        if confidence_scores.get("name_attribute", 0) < 0.5:
            reasons.append("No name attribute in selector")

        if confidence_scores.get("field_name_clarity", 0) < 0.5:
            reasons.append("Unclear or generic field name")

        if confidence_scores.get("mapping_confidence", 0) < 0.5:
            reasons.append("No clear profile field match found")

        if confidence_scores.get("sample_value", 0) < 0.5:
            reasons.append("Sample value doesn't match expected format")

        return reasons

    def _suggest_improvement_actions(self, mapping: Dict[str, Any]) -> List[str]:
        """Suggest actions to improve field mapping"""
        actions = []

        confidence_scores = mapping.get("confidence_scores", {})
        selector_analysis = mapping.get("selector_analysis", {})

        # Suggest selector improvements
        if not selector_analysis.get("attributes", {}).get("name"):
            actions.append("Try to find a selector with a name attribute")

        if confidence_scores.get("selector_quality", 0) < 0.5:
            actions.append("Use a more specific CSS selector")

        # Suggest mapping improvements
        alternatives = mapping.get("alternatives", [])
        if alternatives:
            actions.append(f"Consider alternative mappings: {', '.join(alternatives[:2])}")

        # Suggest validation improvements
        if confidence_scores.get("sample_value", 0) < 0.5:
            actions.append("Verify the sample value format matches the field type")

        return actions

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()

    def generate_field_mapping_report(self, recording: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive report on field mapping quality

        Args:
            recording: Recording with enhanced field mappings

        Returns:
            Detailed quality report
        """
        field_mappings = recording.get("field_mappings", [])

        # Calculate overall statistics
        total_fields = len(field_mappings)
        high_confidence = len([m for m in field_mappings if m.get("enhanced_confidence", 0) > 0.7])
        medium_confidence = len([m for m in field_mappings if 0.4 <= m.get("enhanced_confidence", 0) <= 0.7])
        low_confidence = len([m for m in field_mappings if m.get("enhanced_confidence", 0) < 0.4])

        # Analyze field type distribution
        field_type_distribution = {}
        for mapping in field_mappings:
            field_type = mapping.get("field_type", "unknown")
            field_type_distribution[field_type] = field_type_distribution.get(field_type, 0) + 1

        # Calculate average confidence
        avg_confidence = sum(m.get("enhanced_confidence", 0) for m in field_mappings) / max(total_fields, 1)

        # Get improvement suggestions
        suggestions = self.suggest_field_mapping_corrections(recording)

        report = {
            "recording_name": recording.get("recording_name", "Unknown"),
            "total_fields": total_fields,
            "confidence_distribution": {
                "high_confidence": high_confidence,
                "medium_confidence": medium_confidence,
                "low_confidence": low_confidence
            },
            "confidence_percentages": {
                "high_confidence": (high_confidence / max(total_fields, 1)) * 100,
                "medium_confidence": (medium_confidence / max(total_fields, 1)) * 100,
                "low_confidence": (low_confidence / max(total_fields, 1)) * 100
            },
            "average_confidence": avg_confidence,
            "field_type_distribution": field_type_distribution,
            "improvement_suggestions": len(suggestions),
            "suggestions_summary": suggestions[:3],  # Top 3 suggestions
            "overall_quality": self._calculate_overall_quality(avg_confidence, high_confidence, total_fields),
            "generated_at": self._get_current_timestamp()
        }

        return report

    def _calculate_overall_quality(self, avg_confidence: float, high_confidence: int, total_fields: int) -> str:
        """Calculate overall quality rating"""
        if avg_confidence > 0.8 and (high_confidence / max(total_fields, 1)) > 0.8:
            return "excellent"
        elif avg_confidence > 0.6 and (high_confidence / max(total_fields, 1)) > 0.6:
            return "good"
        elif avg_confidence > 0.4:
            return "fair"
        else:
            return "poor"

def main():
    """Test the Enhanced Field Mapper"""
    mapper = EnhancedFieldMapper()

    # Test field mapping
    test_mapping = {
        "field_name": "First Name",
        "field_selector": "input[name='first_name']",
        "field_type": "textbox",
        "profile_mapping": "firstName",
        "sample_value": "John"
    }

    enhanced = mapper.analyze_field_mapping(test_mapping)
    print(f"Enhanced mapping confidence: {enhanced.get('enhanced_confidence', 0):.2f}")
    print(f"Recommended mapping: {enhanced.get('recommended_mapping', 'unknown')}")
    print(f"Alternatives: {enhanced.get('alternatives', [])}")

if __name__ == "__main__":
    main()