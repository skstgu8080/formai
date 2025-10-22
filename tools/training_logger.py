#!/usr/bin/env python3
"""
Training Data Logger - Collect successful form field interactions for ML training
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

class TrainingLogger:
    """Logs successful form field interactions for training data collection"""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"session_{int(time.time())}"
        self.training_data = []
        self.session_stats = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "total_fields": 0,
            "successful_fields": 0,
            "failed_fields": 0,
            "field_types": {},
            "interaction_methods": {},
            "avg_time_per_field": 0
        }

        # Create training data directory
        self.training_dir = Path("training_data")
        self.training_dir.mkdir(exist_ok=True)

    def log_field_interaction(self,
                             url: str,
                             field_info: Dict[str, Any],
                             success: bool,
                             interaction_time_ms: float,
                             error_msg: str = None):
        """Log a field interaction with all relevant metadata"""

        timestamp = datetime.now().isoformat()

        # Create unique field ID for tracking
        field_signature = f"{field_info.get('selector', '')}{field_info.get('type', '')}{field_info.get('name', '')}"
        field_id = hashlib.md5(field_signature.encode()).hexdigest()[:8]

        interaction_data = {
            "timestamp": timestamp,
            "session_id": self.session_id,
            "field_id": field_id,
            "url": url,
            "field": {
                "selector": field_info.get('selector'),
                "element_ref": field_info.get('element_ref'),
                "type": field_info.get('type'),
                "name": field_info.get('name'),
                "id": field_info.get('id'),
                "class": field_info.get('class'),
                "placeholder": field_info.get('placeholder'),
                "tag_name": field_info.get('tag_name', 'input'),
                "input_type": field_info.get('input_type', 'text')
            },
            "interaction": {
                "method": field_info.get('method', 'unknown'),
                "value": field_info.get('value'),
                "success": success,
                "time_ms": round(interaction_time_ms, 2),
                "error": error_msg
            },
            "detection": {
                "auto_detected": field_info.get('auto_detected', False),
                "confidence": field_info.get('confidence', 0.0),
                "detection_method": field_info.get('detection_method'),
                "fallback_used": field_info.get('fallback_used', False)
            }
        }

        self.training_data.append(interaction_data)
        self._update_session_stats(interaction_data)

        # Auto-save every 10 interactions
        if len(self.training_data) % 10 == 0:
            self.save_training_data()

    def _update_session_stats(self, interaction_data: Dict):
        """Update session statistics"""
        self.session_stats["total_fields"] += 1

        if interaction_data["interaction"]["success"]:
            self.session_stats["successful_fields"] += 1
        else:
            self.session_stats["failed_fields"] += 1

        # Track field types
        field_type = interaction_data["field"]["type"]
        if field_type:
            self.session_stats["field_types"][field_type] = \
                self.session_stats["field_types"].get(field_type, 0) + 1

        # Track interaction methods
        method = interaction_data["interaction"]["method"]
        self.session_stats["interaction_methods"][method] = \
            self.session_stats["interaction_methods"].get(method, 0) + 1

        # Calculate average time
        total_time = sum(item["interaction"]["time_ms"] for item in self.training_data)
        self.session_stats["avg_time_per_field"] = round(total_time / len(self.training_data), 2)

    def log_successful_fill(self, url: str, selector: str, field_type: str,
                           value: str, method: str = "cdp_type",
                           time_ms: float = 0, **kwargs):
        """Convenience method for logging successful field fills"""

        field_info = {
            "selector": selector,
            "type": field_type,
            "value": value,
            "method": method,
            "auto_detected": kwargs.get("auto_detected", True),
            "confidence": kwargs.get("confidence", 1.0),
            **kwargs
        }

        self.log_field_interaction(url, field_info, True, time_ms)

    def log_failed_fill(self, url: str, selector: str, field_type: str,
                       error_msg: str, method: str = "cdp_type",
                       time_ms: float = 0, **kwargs):
        """Convenience method for logging failed field fills"""

        field_info = {
            "selector": selector,
            "type": field_type,
            "method": method,
            "auto_detected": kwargs.get("auto_detected", False),
            **kwargs
        }

        self.log_field_interaction(url, field_info, False, time_ms, error_msg)

    def save_training_data(self):
        """Save training data to JSON file"""
        filename = f"training_session_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.training_dir / filename

        output_data = {
            "session_stats": self.session_stats,
            "training_data": self.training_data
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"✓ Training data saved to {filepath}")
        return str(filepath)

    def get_session_summary(self) -> Dict:
        """Get current session statistics"""
        self.session_stats["end_time"] = datetime.now().isoformat()
        success_rate = 0
        if self.session_stats["total_fields"] > 0:
            success_rate = round(
                (self.session_stats["successful_fields"] / self.session_stats["total_fields"]) * 100, 1
            )
        self.session_stats["success_rate"] = success_rate
        return self.session_stats.copy()

    def get_field_type_performance(self) -> Dict[str, Dict]:
        """Analyze performance by field type"""
        performance = {}

        for item in self.training_data:
            field_type = item["field"]["type"]
            if not field_type:
                continue

            if field_type not in performance:
                performance[field_type] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0,
                    "avg_time_ms": 0,
                    "success_rate": 0
                }

            perf = performance[field_type]
            perf["total"] += 1

            if item["interaction"]["success"]:
                perf["successful"] += 1
            else:
                perf["failed"] += 1

        # Calculate success rates and average times
        for field_type, perf in performance.items():
            if perf["total"] > 0:
                perf["success_rate"] = round((perf["successful"] / perf["total"]) * 100, 1)

                # Calculate average time for this field type
                times = [item["interaction"]["time_ms"] for item in self.training_data
                        if item["field"]["type"] == field_type and item["interaction"]["success"]]
                if times:
                    perf["avg_time_ms"] = round(sum(times) / len(times), 2)

        return performance

    def export_training_dataset(self, format: str = "json") -> str:
        """Export training data in various formats for ML training"""

        if format == "json":
            return self.save_training_data()

        elif format == "csv":
            import csv

            filename = f"training_dataset_{self.session_id}.csv"
            filepath = self.training_dir / filename

            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if self.training_data:
                    # Flatten the nested structure for CSV
                    fieldnames = [
                        'timestamp', 'session_id', 'field_id', 'url',
                        'selector', 'element_ref', 'field_type', 'field_name', 'field_id_attr',
                        'field_class', 'placeholder', 'tag_name', 'input_type',
                        'method', 'value', 'success', 'time_ms', 'error',
                        'auto_detected', 'confidence', 'detection_method', 'fallback_used'
                    ]

                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for item in self.training_data:
                        row = {
                            'timestamp': item['timestamp'],
                            'session_id': item['session_id'],
                            'field_id': item['field_id'],
                            'url': item['url'],
                            'selector': item['field']['selector'],
                            'element_ref': item['field']['element_ref'],
                            'field_type': item['field']['type'],
                            'field_name': item['field']['name'],
                            'field_id_attr': item['field']['id'],
                            'field_class': item['field']['class'],
                            'placeholder': item['field']['placeholder'],
                            'tag_name': item['field']['tag_name'],
                            'input_type': item['field']['input_type'],
                            'method': item['interaction']['method'],
                            'value': item['interaction']['value'],
                            'success': item['interaction']['success'],
                            'time_ms': item['interaction']['time_ms'],
                            'error': item['interaction']['error'],
                            'auto_detected': item['detection']['auto_detected'],
                            'confidence': item['detection']['confidence'],
                            'detection_method': item['detection']['detection_method'],
                            'fallback_used': item['detection']['fallback_used']
                        }
                        writer.writerow(row)

            print(f"✓ CSV dataset exported to {filepath}")
            return str(filepath)

    def print_summary(self):
        """Print a formatted summary of the training session"""
        summary = self.get_session_summary()

        print(f"\n{'='*50}")
        print(f"TRAINING SESSION SUMMARY")
        print(f"{'='*50}")
        print(f"Session ID: {summary['session_id']}")
        print(f"Total Fields: {summary['total_fields']}")
        print(f"Successful: {summary['successful_fields']}")
        print(f"Failed: {summary['failed_fields']}")
        print(f"Success Rate: {summary['success_rate']}%")
        print(f"Avg Time/Field: {summary['avg_time_per_field']}ms")

        print(f"\nField Types:")
        for field_type, count in summary['field_types'].items():
            print(f"  - {field_type}: {count}")

        print(f"\nInteraction Methods:")
        for method, count in summary['interaction_methods'].items():
            print(f"  - {method}: {count}")

        # Show detailed performance by field type
        performance = self.get_field_type_performance()
        if performance:
            print(f"\nPerformance by Field Type:")
            for field_type, perf in performance.items():
                print(f"  - {field_type}: {perf['success_rate']}% ({perf['successful']}/{perf['total']}) - {perf['avg_time_ms']}ms")

class FieldDetectionTrainer:
    """Analyzes training data to improve field detection algorithms"""

    def __init__(self, training_data_dir: str = "training_data"):
        self.training_data_dir = Path(training_data_dir)
        self.all_training_data = []
        self.load_all_training_data()

    def load_all_training_data(self):
        """Load all training data files"""
        for file in self.training_data_dir.glob("training_session_*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.all_training_data.extend(data.get("training_data", []))
            except Exception as e:
                print(f"Error loading {file}: {e}")

    def analyze_successful_patterns(self) -> Dict:
        """Analyze patterns in successful field detections"""
        successful_data = [item for item in self.all_training_data
                          if item["interaction"]["success"]]

        patterns = {
            "selectors": {},
            "field_types": {},
            "detection_methods": {},
            "best_practices": []
        }

        for item in successful_data:
            # Analyze successful selectors
            selector = item["field"]["selector"]
            if selector:
                patterns["selectors"][selector] = patterns["selectors"].get(selector, 0) + 1

            # Analyze field types
            field_type = item["field"]["type"]
            if field_type:
                patterns["field_types"][field_type] = patterns["field_types"].get(field_type, 0) + 1

            # Analyze detection methods
            detection_method = item["detection"]["detection_method"]
            if detection_method:
                patterns["detection_methods"][detection_method] = \
                    patterns["detection_methods"].get(detection_method, 0) + 1

        return patterns

    def generate_improved_selectors(self) -> Dict[str, List[str]]:
        """Generate improved selector strategies based on training data"""
        successful_data = [item for item in self.all_training_data
                          if item["interaction"]["success"]]

        field_selectors = {}

        for item in successful_data:
            field_type = item["field"]["type"]
            selector = item["field"]["selector"]

            if field_type and selector:
                if field_type not in field_selectors:
                    field_selectors[field_type] = []
                field_selectors[field_type].append(selector)

        # Remove duplicates and sort by frequency
        for field_type in field_selectors:
            unique_selectors = list(set(field_selectors[field_type]))
            field_selectors[field_type] = unique_selectors

        return field_selectors