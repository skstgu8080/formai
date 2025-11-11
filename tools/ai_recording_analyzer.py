#!/usr/bin/env python3
"""
AI Recording Analyzer - Use Ollama to intelligently analyze Chrome recordings
and automatically map fields to profile data
"""
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import os
import httpx

class AIRecordingAnalyzer:
    """
    Analyzes Chrome DevTools recordings using AI to:
    1. Identify field types (email, name, phone, etc.)
    2. Map fields to profile fields automatically
    3. Build training data for continuous improvement
    4. Categorize forms by type (signup, checkout, contact, etc.)
    """

    def __init__(self, ollama_base_url: str = None, model: str = None):
        """Initialize the AI analyzer with Ollama configuration"""
        self.ollama_base_url = ollama_base_url or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = model or os.getenv('OLLAMA_MODEL', 'llama3.2')

        # Profile field reference for AI
        self.profile_fields = {
            'personal': ['firstName', 'lastName', 'fullName', 'email', 'phone', 'age', 'sex', 'birthMonth', 'birthDay', 'birthYear'],
            'address': ['address1', 'address2', 'city', 'state', 'zip', 'country'],
            'business': ['company', 'title', 'workPhone', 'workEmail'],
            'auth': ['username', 'password'],
            'payment': ['creditCardNumber', 'creditCardExpMonth', 'creditCardExpYear', 'creditCardCVC'],
            'other': ['ssn', 'website', 'notes']
        }

    async def analyze_recording(
        self,
        recording_data: Dict[str, Any],
        profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a Chrome DevTools recording and generate AI-powered field mappings

        Args:
            recording_data: The parsed Chrome recording (from ChromeRecorderParser)
            profile: Optional user profile to validate mappings against

        Returns:
            Enhanced recording with AI analysis
        """
        try:
            # Extract field mappings from recording
            field_mappings = recording_data.get('field_mappings', [])
            url = recording_data.get('url', 'unknown')

            if not field_mappings:
                return {
                    **recording_data,
                    'ai_analysis': {
                        'status': 'no_fields',
                        'message': 'No form fields detected in recording',
                        'confidence': 0.0
                    }
                }

            # Analyze fields with AI
            ai_field_analysis = await self._analyze_fields_with_ai(field_mappings, url)

            # Categorize the form
            form_category = await self._categorize_form(recording_data, ai_field_analysis)

            # Calculate overall confidence
            confidence_scores = [field.get('ai_confidence', 0.5) for field in ai_field_analysis]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5

            # Build enhanced recording
            enhanced_recording = {
                **recording_data,
                'ai_analysis': {
                    'status': 'analyzed',
                    'timestamp': datetime.now().isoformat(),
                    'model_used': self.model,
                    'form_category': form_category,
                    'field_count': len(ai_field_analysis),
                    'avg_confidence': round(avg_confidence, 2),
                    'fields': ai_field_analysis,
                    'requires_review': avg_confidence < 0.8,
                    'training_value': self._calculate_training_value(ai_field_analysis, avg_confidence)
                }
            }

            # Validate against profile if provided
            if profile:
                validation = self._validate_against_profile(ai_field_analysis, profile)
                enhanced_recording['ai_analysis']['profile_validation'] = validation

            return enhanced_recording

        except Exception as e:
            return {
                **recording_data,
                'ai_analysis': {
                    'status': 'error',
                    'error': str(e),
                    'confidence': 0.0
                }
            }

    async def _analyze_fields_with_ai(
        self,
        field_mappings: List[Dict[str, Any]],
        url: str
    ) -> List[Dict[str, Any]]:
        """Use Ollama to analyze field mappings and improve detection"""

        # Build prompt for AI analysis
        prompt = self._build_field_analysis_prompt(field_mappings, url)

        try:
            # Call Ollama API
            ai_response = await self._call_ollama(prompt)

            # Parse AI response
            ai_field_data = self._parse_ai_field_response(ai_response)

            # Merge AI analysis with existing field mappings
            enhanced_fields = []
            for i, field in enumerate(field_mappings):
                ai_data = ai_field_data.get(i, {})

                enhanced_field = {
                    **field,
                    'ai_field_type': ai_data.get('field_type', field.get('field_type', 'textbox')),
                    'ai_profile_mapping': ai_data.get('profile_field', field.get('profile_mapping', '')),
                    'ai_confidence': ai_data.get('confidence', 0.7),
                    'ai_reasoning': ai_data.get('reasoning', ''),
                    'suggested_value_from_profile': ai_data.get('profile_field', '')
                }

                enhanced_fields.append(enhanced_field)

            return enhanced_fields

        except Exception as e:
            print(f"AI analysis failed, using fallback: {e}")
            # Fallback to rule-based analysis
            return [
                {
                    **field,
                    'ai_field_type': field.get('field_type', 'textbox'),
                    'ai_profile_mapping': field.get('profile_mapping', ''),
                    'ai_confidence': field.get('confidence', 0.5),
                    'ai_reasoning': 'Fallback to rule-based detection',
                    'suggested_value_from_profile': field.get('profile_mapping', '')
                }
                for field in field_mappings
            ]

    def _build_field_analysis_prompt(
        self,
        field_mappings: List[Dict[str, Any]],
        url: str
    ) -> str:
        """Build a prompt for Ollama to analyze form fields"""

        # Available profile fields for mapping
        all_profile_fields = []
        for category, fields in self.profile_fields.items():
            all_profile_fields.extend(fields)

        # Build field descriptions
        field_descriptions = []
        for i, field in enumerate(field_mappings):
            field_desc = f"""
Field {i}:
  Name: {field.get('field_name', 'Unknown')}
  Selector: {field.get('field_selector', '')}
  Type: {field.get('field_type', 'textbox')}
  Sample Value: {field.get('sample_value', '')}
  Current Mapping: {field.get('profile_mapping', 'none')}
"""
            field_descriptions.append(field_desc)

        prompt = f"""Analyze these form fields from a web form at {url}.

For each field, identify:
1. The actual field type (email, firstName, lastName, phone, address, city, state, zip, etc.)
2. The best profile field mapping from this list: {', '.join(all_profile_fields)}
3. Confidence score (0.0-1.0)
4. Brief reasoning

Available profile fields by category:
{json.dumps(self.profile_fields, indent=2)}

Form fields to analyze:
{''.join(field_descriptions)}

Return ONLY valid JSON in this exact format:
{{
  "0": {{"field_type": "email", "profile_field": "email", "confidence": 0.95, "reasoning": "Email input detected"}},
  "1": {{"field_type": "firstName", "profile_field": "firstName", "confidence": 0.90, "reasoning": "First name field"}}
}}

JSON response:"""

        return prompt

    async def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API for AI analysis"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent output
                        "top_p": 0.9
                    }
                }
            )

            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code}")

            result = response.json()
            return result.get('response', '')

    def _parse_ai_field_response(self, ai_response: str) -> Dict[int, Dict[str, Any]]:
        """Parse the AI's JSON response into structured field data"""
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = ai_response

            # Parse JSON
            parsed = json.loads(json_str)

            # Convert string keys to int keys
            result = {}
            for key, value in parsed.items():
                try:
                    int_key = int(key)
                    result[int_key] = value
                except (ValueError, TypeError):
                    continue

            return result

        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            print(f"Response was: {ai_response[:500]}")
            return {}

    async def _categorize_form(
        self,
        recording_data: Dict[str, Any],
        field_analysis: List[Dict[str, Any]]
    ) -> str:
        """Determine the form category (signup, checkout, contact, etc.)"""

        url = recording_data.get('url', '')
        title = recording_data.get('recording_name', '')

        # Extract field types present
        field_types = set()
        for field in field_analysis:
            field_type = field.get('ai_profile_mapping', field.get('profile_mapping', ''))
            if field_type:
                field_types.add(field_type)

        # Category detection rules
        if 'password' in field_types and 'email' in field_types:
            if 'firstName' in field_types or 'lastName' in field_types:
                return 'user_registration'
            return 'login'

        if 'creditCardNumber' in field_types:
            return 'checkout'

        if any(addr in field_types for addr in ['address1', 'city', 'state', 'zip']):
            if 'creditCardNumber' in field_types:
                return 'checkout'
            return 'shipping_address'

        if 'company' in field_types or 'title' in field_types:
            return 'business_contact'

        if 'email' in field_types or 'phone' in field_types:
            return 'contact_form'

        # Check URL/title for hints
        url_lower = url.lower()
        title_lower = title.lower()

        if any(keyword in url_lower or keyword in title_lower for keyword in ['signup', 'register', 'join']):
            return 'user_registration'

        if any(keyword in url_lower or keyword in title_lower for keyword in ['checkout', 'payment', 'order']):
            return 'checkout'

        if any(keyword in url_lower or keyword in title_lower for keyword in ['contact', 'support', 'message']):
            return 'contact_form'

        return 'general_form'

    def _validate_against_profile(
        self,
        field_analysis: List[Dict[str, Any]],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate field mappings against actual profile data"""

        validation = {
            'total_fields': len(field_analysis),
            'mappable_fields': 0,
            'unmappable_fields': 0,
            'missing_profile_data': [],
            'ready_for_replay': False
        }

        for field in field_analysis:
            profile_field = field.get('ai_profile_mapping', field.get('profile_mapping', ''))

            if not profile_field or profile_field == 'none':
                validation['unmappable_fields'] += 1
                continue

            # Check if profile has this field
            if profile_field in profile and profile[profile_field]:
                validation['mappable_fields'] += 1
            else:
                validation['unmappable_fields'] += 1
                validation['missing_profile_data'].append(profile_field)

        # Ready if at least 80% of fields are mappable
        if validation['total_fields'] > 0:
            mappable_ratio = validation['mappable_fields'] / validation['total_fields']
            validation['ready_for_replay'] = mappable_ratio >= 0.8
            validation['mappable_percentage'] = round(mappable_ratio * 100, 1)

        return validation

    def _calculate_training_value(
        self,
        field_analysis: List[Dict[str, Any]],
        avg_confidence: float
    ) -> str:
        """
        Calculate how valuable this recording is for training

        Returns: 'high', 'medium', 'low'
        """
        # High value if:
        # - Many fields (5+)
        # - High confidence (>0.85)
        # - Diverse field types

        field_count = len(field_analysis)
        unique_field_types = len(set(
            field.get('ai_profile_mapping', '')
            for field in field_analysis
        ))

        if field_count >= 5 and avg_confidence > 0.85 and unique_field_types >= 4:
            return 'high'
        elif field_count >= 3 and avg_confidence > 0.7:
            return 'medium'
        else:
            return 'low'

    def generate_few_shot_examples(
        self,
        analyzed_recordings: List[Dict[str, Any]],
        limit: int = 5
    ) -> str:
        """
        Generate few-shot learning examples from previously analyzed recordings
        This can be used to improve future analyses
        """

        examples = []

        for recording in analyzed_recordings[:limit]:
            ai_analysis = recording.get('ai_analysis', {})
            if ai_analysis.get('status') != 'analyzed':
                continue

            fields = ai_analysis.get('fields', [])
            if not fields:
                continue

            example = f"""
Example: {recording.get('recording_name', 'Recording')}
URL: {recording.get('url', 'unknown')}
Category: {ai_analysis.get('form_category', 'general_form')}

Field Mappings:
"""
            for field in fields[:5]:  # Show first 5 fields as example
                example += f"- {field.get('field_name', 'Field')}: {field.get('ai_profile_mapping', 'none')} (confidence: {field.get('ai_confidence', 0.5):.2f})\n"

            examples.append(example)

        return '\n\n'.join(examples)


def main():
    """Test the AI Recording Analyzer"""
    import asyncio

    analyzer = AIRecordingAnalyzer()

    # Sample recording data
    sample_recording = {
        "recording_id": "test123",
        "recording_name": "Test Signup Form",
        "url": "https://example.com/signup",
        "field_mappings": [
            {
                "field_name": "Email Address",
                "field_selector": "input[name='email']",
                "field_type": "textbox",
                "sample_value": "test@example.com",
                "profile_mapping": "email",
                "confidence": 0.8
            },
            {
                "field_name": "First Name",
                "field_selector": "input[name='fname']",
                "field_type": "textbox",
                "sample_value": "John",
                "profile_mapping": "firstName",
                "confidence": 0.9
            }
        ]
    }

    sample_profile = {
        "email": "john.doe@example.com",
        "firstName": "John",
        "lastName": "Doe",
        "phone": "555-1234"
    }

    async def test_analysis():
        print("Testing AI Recording Analyzer...")
        result = await analyzer.analyze_recording(sample_recording, sample_profile)

        print("\nAnalysis Result:")
        print(json.dumps(result.get('ai_analysis', {}), indent=2))

        if result['ai_analysis'].get('status') == 'analyzed':
            print(f"\n✓ Analysis successful!")
            print(f"Form Category: {result['ai_analysis']['form_category']}")
            print(f"Confidence: {result['ai_analysis']['avg_confidence']}")
            print(f"Training Value: {result['ai_analysis']['training_value']}")

    asyncio.run(test_analysis())


if __name__ == "__main__":
    main()
