"""
Data validation schema and utilities for Wingo scraper

Ensures all scraped data meets quality standards before storage.
"""

from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class WinGoDataValidator:
    """Validates scraped game results"""
    
    # Valid ranges and enums
    VALID_NUMBERS = set(range(0, 10))  # 0-9
    VALID_COLORS = {"Red", "Green", "Violet"}
    VALID_SIZES = {"Big", "Small"}
    
    # Mapping: number -> (color, size)
    NUMBER_MAPPINGS = {
        0: ("Violet", "Small"),
        1: ("Green", "Small"),
        2: ("Red", "Small"),
        3: ("Green", "Small"),
        4: ("Red", "Small"),
        5: ("Violet", "Big"),
        6: ("Red", "Big"),
        7: ("Green", "Big"),
        8: ("Red", "Big"),
        9: ("Green", "Big"),
    }
    
    @classmethod
    def validate(cls, result: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate a scraped result.
        
        Args:
            result: Dictionary with game data
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if "number" not in result:
            return False, "Missing 'number' field"
        
        if "timestamp" not in result:
            return False, "Missing 'timestamp' field"
        
        # Validate number
        number = result["number"]
        if not isinstance(number, int):
            return False, f"'number' must be int, got {type(number).__name__}"
        
        if number not in cls.VALID_NUMBERS:
            return False, f"'number' must be in 0-9, got {number}"
        
        # Validate timestamp
        timestamp = result["timestamp"]
        if not isinstance(timestamp, (int, float)):
            return False, f"'timestamp' must be numeric, got {type(timestamp).__name__}"
        
        if timestamp <= 0:
            return False, f"'timestamp' must be positive, got {timestamp}"
        
        # Validate color consistency if present
        if "color" in result:
            color = result["color"]
            if color not in cls.VALID_COLORS:
                return False, f"'color' must be in {cls.VALID_COLORS}, got {color}"
            
            # Check color matches number
            expected_color, _ = cls.NUMBER_MAPPINGS[number]
            if color != expected_color:
                logger.warning(f"Color mismatch: number {number} should be {expected_color}, got {color}")
                # Don't fail, just warn - might be display issue
        
        # Validate size consistency if present
        if "size" in result:
            size = result["size"]
            if size not in cls.VALID_SIZES:
                return False, f"'size' must be in {cls.VALID_SIZES}, got {size}"
            
            # Check size matches number
            _, expected_size = cls.NUMBER_MAPPINGS[number]
            if size != expected_size:
                logger.warning(f"Size mismatch: number {number} should be {expected_size}, got {size}")
                # Don't fail, just warn
        
        return True, ""
    
    @classmethod
    def complete_result(cls, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill in missing fields (color, size) based on number.
        
        Args:
            result: Partial result dictionary
            
        Returns:
            Complete result with all fields
        """
        if "number" not in result:
            raise ValueError("'number' field required to complete result")
        
        number = result["number"]
        color, size = cls.NUMBER_MAPPINGS[number]
        
        return {
            **result,
            "color": result.get("color", color),
            "size": result.get("size", size),
        }
    
    @classmethod
    def validate_batch(cls, results: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Tuple[Dict, str]]]:
        """
        Validate multiple results.
        
        Args:
            results: List of result dictionaries
            
        Returns:
            Tuple of (valid_results, failed_results_with_errors)
        """
        valid = []
        failed = []
        
        for result in results:
            is_valid, error = cls.validate(result)
            if is_valid:
                valid.append(result)
            else:
                failed.append((result, error))
        
        return valid, failed
    
    @classmethod
    def detect_duplicates(cls, new_result: Dict[str, Any], recent_results: List[Dict[str, Any]], 
                         time_window: int = 60) -> bool:
        """
        Check if result is likely a duplicate (same number within time window).
        
        Args:
            new_result: New result to check
            recent_results: List of recent results from MongoDB
            time_window: Time window in seconds to check for duplicates
            
        Returns:
            True if likely duplicate, False otherwise
        """
        if not recent_results:
            return False
        
        new_time = new_result.get("timestamp", 0)
        new_number = new_result.get("number")
        
        for result in recent_results:
            old_time = result.get("timestamp", 0)
            old_number = result.get("number")
            
            # Check if same number within time window
            if old_number == new_number and (new_time - old_time) < time_window:
                return True
        
        return False


# Test data
if __name__ == "__main__":
    validator = WinGoDataValidator()
    
    # Test valid result
    valid_result = {
        "number": 7,
        "color": "Green",
        "size": "Big",
        "timestamp": 1710764123.456
    }
    
    is_valid, error = validator.validate(valid_result)
    print(f"Valid result: {is_valid} ({error})")
    
    # Test invalid number
    invalid_result = {
        "number": 15,
        "timestamp": 1710764123.456
    }
    
    is_valid, error = validator.validate(invalid_result)
    print(f"Invalid number: {is_valid} ({error})")
    
    # Test complete result
    partial_result = {
        "number": 3,
        "timestamp": 1710764123.456
    }
    
    completed = validator.complete_result(partial_result)
    print(f"Completed: {completed}")
    
    # Test batch validation
    batch = [
        {"number": 5, "timestamp": 1710764123.0},
        {"number": 10, "timestamp": 1710764124.0},  # Invalid
        {"number": 0, "timestamp": 1710764125.0},
    ]
    
    valid, failed = validator.validate_batch(batch)
    print(f"\nBatch validation: {len(valid)} valid, {len(failed)} failed")
    for result, error in failed:
        print(f"  Failed: {result} -> {error}")
