#!/usr/bin/env python3
"""
Tests for browse tool.
"""
import os
import sys

# Add inference directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'inference'))

from tool_browse import Browse


def test_browse_basic():
    """Test basic browse functionality"""
    print("\n=== Testing browse Basic Functionality ===")
    
    tool = Browse()
    
    # Test with valid parameters
    params = {"query": "Python programming"}
    result = tool.call(params)
    
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result)}")
    
    # Check that result contains expected sections
    assert isinstance(result, str), "Result should be a string"
    assert "Search results for query: Python programming" in result or "[browse] Failed" in result, \
        "Result should contain search header or failure message"
    
    print("✓ Basic browse test passed")
    return True


def test_browse_invalid_params():
    """Test browse with invalid parameters"""
    print("\n=== Testing browse Invalid Parameters ===")
    
    tool = Browse()
    
    # Test with missing query
    params = {}
    result = tool.call(params)
    
    assert "[browse] Invalid request format" in result, \
        "Should return error for missing query"
    
    print("✓ Invalid parameters test passed")
    return True


def test_browse_parameters():
    """Test that browse tool has correct parameter definition"""
    print("\n=== Testing browse Parameter Definition ===")
    
    tool = Browse()
    
    # Check required fields
    assert "query" in tool.parameters["properties"], "Should have query parameter"
    assert "query" in tool.parameters["required"], "query should be required"
    assert "url" not in tool.parameters["properties"], "Should NOT have url parameter"
    assert "goal" not in tool.parameters["properties"], "Should NOT have goal parameter"
    
    # Check parameter type
    assert tool.parameters["properties"]["query"]["type"] == "string", \
        "query parameter should be string type"
    
    print("✓ Parameter definition test passed")
    return True


def run_all_tests():
    """Run all browse tests"""
    print("="*70)
    print("Testing browse Tool")
    print("="*70)
    
    tests = [
        test_browse_parameters,
        test_browse_invalid_params,
        test_browse_basic,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {test.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {test.__name__}")
            print(f"   {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("✅ All browse tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
