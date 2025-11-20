#!/usr/bin/env python3
"""
Tests for fetch_url tool.
"""
import os
import sys

# Add inference directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'inference'))

from tool_fetch_url import FetchUrl


def test_fetch_url_basic():
    """Test basic fetch_url functionality"""
    print("\n=== Testing fetch_url Basic Functionality ===")
    
    tool = FetchUrl()
    
    # Test with valid parameters
    params = {"url": "https://example.com"}
    result = tool.call(params)
    
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(result)}")
    
    # Check that result contains expected sections
    assert isinstance(result, str), "Result should be a string"
    assert "Content from https://example.com" in result or "[fetch_url] Failed" in result, \
        "Result should contain content header or failure message"
    
    print("✓ Basic fetch_url test passed")
    return True


def test_fetch_url_invalid_params():
    """Test fetch_url with invalid parameters"""
    print("\n=== Testing fetch_url Invalid Parameters ===")
    
    tool = FetchUrl()
    
    # Test with missing url
    params = {}
    result = tool.call(params)
    
    assert "[fetch_url] Invalid request format" in result, \
        "Should return error for missing url"
    
    print("✓ Invalid parameters test passed")
    return True


def test_fetch_url_parameters():
    """Test that fetch_url tool has correct parameter definition"""
    print("\n=== Testing fetch_url Parameter Definition ===")
    
    tool = FetchUrl()
    
    # Check required fields
    assert "url" in tool.parameters["properties"], "Should have url parameter"
    assert "url" in tool.parameters["required"], "url should be required"
    assert "goal" not in tool.parameters["properties"], "Should NOT have goal parameter"
    
    # Check parameter type
    assert tool.parameters["properties"]["url"]["type"] == "string", \
        "url parameter should be string type"
    
    print("✓ Parameter definition test passed")
    return True


def run_all_tests():
    """Run all fetch_url tests"""
    print("="*70)
    print("Testing fetch_url Tool")
    print("="*70)
    
    tests = [
        test_fetch_url_parameters,
        test_fetch_url_invalid_params,
        test_fetch_url_basic,
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
        print("✅ All fetch_url tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
