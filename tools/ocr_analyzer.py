#!/usr/bin/env python3
"""
DeepSeek-OCR Analyzer - Vision-based form field detection
Uses DeepSeek-OCR for screenshot-based form analysis
"""
import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path


class DeepSeekOCRAnalyzer:
    """
    Vision-based form analyzer using DeepSeek-OCR
    Complements DOM-based analysis with visual understanding
    """

    def __init__(self):
        self.model = None
        self.enabled = os.getenv('DEEPSEEK_OCR_ENABLED', 'false').lower() == 'true'
        self.model_name = os.getenv('DEEPSEEK_OCR_MODEL', 'deepseek-ai/DeepSeek-OCR')
        self.device = os.getenv('DEEPSEEK_OCR_DEVICE', 'cuda')

    def _load_model(self):
        """Lazy load DeepSeek-OCR model"""
        if self.model is not None:
            return

        if not self.enabled:
            raise Exception("DeepSeek-OCR is not enabled. Set DEEPSEEK_OCR_ENABLED=true in .env")

        try:
            # Import here to avoid requiring these dependencies if not using OCR
            from transformers import AutoModelForCausalLM, AutoProcessor
            import torch

            print(f"[OCR] Loading DeepSeek-OCR model: {self.model_name}")
            print(f"[OCR] Device: {self.device}")

            # Load model and processor
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == 'cuda' else torch.float32,
                device_map=self.device if self.device == 'cuda' else None
            )

            print("[OCR] Model loaded successfully")

        except ImportError as e:
            raise Exception(
                f"Failed to import required libraries. Install with: "
                f"pip install transformers torch torchvision flash-attn\n"
                f"Error: {e}"
            )
        except Exception as e:
            raise Exception(f"Failed to load DeepSeek-OCR model: {e}")

    async def analyze_screenshot(
        self,
        screenshot_path: str,
        prompt: str = "<image>\nDetect all form fields, their labels, and positions. Return as JSON."
    ) -> Dict[str, Any]:
        """
        Analyze form screenshot using DeepSeek-OCR

        Args:
            screenshot_path: Path to screenshot image
            prompt: OCR prompt

        Returns:
            Field detection results with labels and positions
        """
        if not self.enabled:
            return {
                "error": "DeepSeek-OCR not enabled",
                "fields": []
            }

        try:
            self._load_model()

            from PIL import Image
            import torch

            # Load image
            image = Image.open(screenshot_path)

            # Prepare inputs
            inputs = self.processor(
                text=prompt,
                images=image,
                return_tensors="pt"
            )

            if self.device == 'cuda':
                inputs = {k: v.to('cuda') for k, v in inputs.items()}

            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=1000,
                    temperature=0.1
                )

            # Decode
            result_text = self.processor.decode(outputs[0], skip_special_tokens=True)

            # Parse OCR result
            parsed = self._parse_ocr_result(result_text)

            return {
                "success": True,
                "fields": parsed.get("fields", []),
                "layout": parsed.get("layout", "unknown"),
                "captcha_detected": parsed.get("captcha_detected", False)
            }

        except Exception as e:
            return {
                "error": f"OCR analysis failed: {str(e)}",
                "fields": []
            }

    def _parse_ocr_result(self, ocr_text: str) -> Dict[str, Any]:
        """
        Parse OCR result text into structured field data

        Args:
            ocr_text: Raw OCR output

        Returns:
            Structured field information
        """
        # Try to extract JSON from response
        try:
            # Look for JSON in response
            json_start = ocr_text.find('{')
            json_end = ocr_text.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = ocr_text[json_start:json_end]
                parsed = json.loads(json_str)
                return parsed
        except json.JSONDecodeError:
            pass

        # Fallback: Simple parsing
        fields = []
        lines = ocr_text.split('\n')

        for line in lines:
            # Look for field-like patterns
            if any(keyword in line.lower() for keyword in ['email', 'name', 'phone', 'address']):
                fields.append({
                    "label": line.strip(),
                    "type": "textbox",
                    "confidence": 0.7
                })

        return {
            "fields": fields,
            "layout": "unknown",
            "captcha_detected": "captcha" in ocr_text.lower()
        }

    async def detect_captcha(self, screenshot_path: str) -> Optional[str]:
        """
        Detect and read CAPTCHA from screenshot

        Args:
            screenshot_path: Path to screenshot

        Returns:
            CAPTCHA text if detected, None otherwise
        """
        if not self.enabled:
            return None

        try:
            result = await self.analyze_screenshot(
                screenshot_path,
                prompt="<image>\nRead the CAPTCHA text. Return only the text, no explanation."
            )

            if result.get("success"):
                # Extract text from result
                # This is simplified - actual implementation would be more sophisticated
                return result.get("text", None)

        except Exception as e:
            print(f"[OCR] CAPTCHA detection failed: {e}")

        return None

    async def analyze_pdf_form(self, pdf_path: str) -> Dict[str, Any]:
        """
        Analyze PDF form using OCR

        Args:
            pdf_path: Path to PDF file

        Returns:
            Detected form fields
        """
        if not self.enabled:
            return {
                "error": "DeepSeek-OCR not enabled",
                "fields": []
            }

        try:
            # Convert PDF to images
            from pdf2image import convert_from_path

            images = convert_from_path(pdf_path)

            all_fields = []

            # Analyze each page
            for i, image in enumerate(images):
                # Save temp image
                temp_path = f"/tmp/pdf_page_{i}.png"
                image.save(temp_path)

                # Analyze
                result = await self.analyze_screenshot(
                    temp_path,
                    prompt="<image>\nDetect all form fields in this PDF page. Return as JSON."
                )

                if result.get("success"):
                    page_fields = result.get("fields", [])
                    for field in page_fields:
                        field["page"] = i + 1
                    all_fields.extend(page_fields)

                # Clean up
                os.remove(temp_path)

            return {
                "success": True,
                "fields": all_fields,
                "pages": len(images)
            }

        except ImportError:
            return {
                "error": "pdf2image not installed. Install with: pip install pdf2image",
                "fields": []
            }
        except Exception as e:
            return {
                "error": f"PDF analysis failed: {str(e)}",
                "fields": []
            }

    def merge_with_dom_fields(
        self,
        dom_fields: List[Dict],
        ocr_fields: List[Dict]
    ) -> List[Dict]:
        """
        Merge DOM-based and OCR-based field detections

        Args:
            dom_fields: Fields from accessibility tree
            ocr_fields: Fields from OCR analysis

        Returns:
            Merged fields with confidence scores
        """
        merged = []
        matched_ocr_indices = set()

        # First pass: Match DOM fields with OCR fields
        for dom_field in dom_fields:
            dom_label = dom_field.get("label", "").lower()

            # Try to find matching OCR field
            best_match = None
            best_score = 0.0

            for i, ocr_field in enumerate(ocr_fields):
                if i in matched_ocr_indices:
                    continue

                ocr_label = ocr_field.get("label", "").lower()

                # Simple matching - could be improved with fuzzy matching
                if dom_label in ocr_label or ocr_label in dom_label:
                    score = 0.8
                    if score > best_score:
                        best_score = score
                        best_match = (i, ocr_field)

            if best_match:
                # Merge matched fields
                ocr_idx, ocr_field = best_match
                matched_ocr_indices.add(ocr_idx)

                merged_field = {
                    **dom_field,
                    "ocr_label": ocr_field.get("label"),
                    "confidence": (dom_field.get("confidence", 0.7) + ocr_field.get("confidence", 0.7)) / 2,
                    "source": "hybrid"
                }
                merged.append(merged_field)
            else:
                # DOM field only
                merged.append({
                    **dom_field,
                    "confidence": dom_field.get("confidence", 0.7) * 0.9,  # Slight penalty for no OCR match
                    "source": "dom"
                })

        # Second pass: Add unmatched OCR fields
        for i, ocr_field in enumerate(ocr_fields):
            if i not in matched_ocr_indices:
                merged.append({
                    **ocr_field,
                    "confidence": ocr_field.get("confidence", 0.7) * 0.8,  # Penalty for no DOM match
                    "source": "ocr"
                })

        # Sort by confidence
        merged.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return merged


# Singleton instance
_ocr_analyzer = None

def get_ocr_analyzer() -> DeepSeekOCRAnalyzer:
    """Get or create OCR analyzer instance"""
    global _ocr_analyzer
    if _ocr_analyzer is None:
        _ocr_analyzer = DeepSeekOCRAnalyzer()
    return _ocr_analyzer
