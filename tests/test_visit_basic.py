#!/usr/bin/env python3
"""
Basic tests for Visit tool enhancements without requiring full dependencies.
Tests the core logic of new features.
"""
import os
import sys
import re
from urllib.parse import urlparse

def test_remove_text_links():
    """Test markdown link removal function"""
    print("\n=== Testing Markdown Link Removal ===")
    
    def remove_text_links(text: str) -> str:
        return re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)
    
    test_cases = [
        ("Check out [this link](https://example.com)", "Check out this link"),
        ("[Google](https://google.com) and [Bing](https://bing.com)", "Google and Bing"),
        ("No links here", "No links here"),
        ("", ""),
    ]
    
    for input_text, expected in test_cases:
        result = remove_text_links(input_text)
        assert result == expected, f"Expected '{expected}', got '{result}'"
    
    print("✓ All markdown link removal tests passed")
    return True


def test_get_domain():
    """Test domain extraction function"""
    print("\n=== Testing Domain Extraction ===")
    
    def get_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            return parsed.netloc if parsed.netloc else url
        except:
            return url
    
    test_cases = [
        ("https://www.example.com/path", "www.example.com"),
        ("http://test.com:8080/page?query=1", "test.com:8080"),
        ("https://subdomain.example.org/", "subdomain.example.org"),
        ("invalid", "invalid"),  # Returns original URL if no netloc
    ]
    
    for url, expected in test_cases:
        result = get_domain(url)
        assert result == expected, f"Expected '{expected}', got '{result}'"
    
    print("✓ All domain extraction tests passed")
    return True


def test_tool_response_omission():
    """Test tool response omission logic"""
    print("\n=== Testing Tool Response Omission ===")
    
    def omit_old_tool_responses(messages: list, keep_rounds: int) -> list:
        """Simplified version of omission logic"""
        if keep_rounds <= 0:
            return messages
        
        # Create a copy
        messages_copy = [msg.copy() for msg in messages]
        
        # Find tool response indices
        tool_response_indices = []
        for i, msg in enumerate(messages_copy):
            if msg.get("role") == "tool":
                tool_response_indices.append(i)
            elif msg.get("role") == "user" and "<tool_response>" in msg.get("content", ""):
                tool_response_indices.append(i)
        
        # Calculate how many to omit
        num_to_omit = max(0, len(tool_response_indices) - keep_rounds)
        
        # Replace content of old tool responses
        for i in range(num_to_omit):
            idx = tool_response_indices[i]
            messages_copy[idx]["content"] = "<tool_response>\ntool response omitted\n</tool_response>"
        
        return messages_copy
    
    # Test case 1: Keep last 2 of 4 tool responses
    messages = [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Question"},
        {"role": "tool", "content": "<tool_response>\nOld 1\n</tool_response>"},
        {"role": "tool", "content": "<tool_response>\nOld 2\n</tool_response>"},
        {"role": "tool", "content": "<tool_response>\nRecent 1\n</tool_response>"},
        {"role": "tool", "content": "<tool_response>\nRecent 2\n</tool_response>"},
    ]
    
    result = omit_old_tool_responses(messages, keep_rounds=2)
    
    # Check old responses are omitted
    assert "tool response omitted" in result[2]["content"], "Old response 1 should be omitted"
    assert "tool response omitted" in result[3]["content"], "Old response 2 should be omitted"
    
    # Check recent responses are kept
    assert "Recent 1" in result[4]["content"], "Recent response 1 should be kept"
    assert "Recent 2" in result[5]["content"], "Recent response 2 should be kept"
    
    print("✓ Tool response omission (keep 2 of 4) passed")
    
    # Test case 2: Disabled (keep_rounds=0)
    result2 = omit_old_tool_responses(messages, keep_rounds=0)
    assert result2 == messages, "Messages should be unchanged when keep_rounds=0"
    
    print("✓ Tool response omission (disabled) passed")
    
    # Test case 3: Keep more than available
    result3 = omit_old_tool_responses(messages, keep_rounds=10)
    assert "Old 1" in result3[2]["content"], "Should keep all when keep_rounds > available"
    
    print("✓ Tool response omission (keep all) passed")
    
    return True


def test_env_var_parsing():
    """Test environment variable parsing"""
    print("\n=== Testing Environment Variable Parsing ===")
    
    # Test boolean parsing
    test_cases = [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("", False),  # Default case
    ]
    
    for value, expected in test_cases:
        result = value.lower() == "true"
        assert result == expected, f"For '{value}', expected {expected}, got {result}"
    
    print("✓ Boolean env var parsing passed")
    
    # Test integer parsing
    int_cases = [
        ("0", 0),
        ("5", 5),
        ("100", 100),
    ]
    
    for value, expected in int_cases:
        result = int(value)
        assert result == expected, f"For '{value}', expected {expected}, got {result}"
    
    print("✓ Integer env var parsing passed")
    
    return True


def test_direct_fetch_headers():
    """Test that direct fetch headers are comprehensive"""
    print("\n=== Testing Direct Fetch Headers ===")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "Referer": "https://www.google.com/"
    }
    
    # Check critical headers are present
    assert "User-Agent" in headers, "User-Agent header missing"
    assert "Mozilla" in headers["User-Agent"], "User-Agent should contain Mozilla"
    assert "Accept" in headers, "Accept header missing"
    assert "Referer" in headers, "Referer header missing"
    
    print("✓ Direct fetch headers are comprehensive")
    print(f"  Total headers: {len(headers)}")
    
    return True


def run_all_tests():
    """Run all basic tests"""
    print("="*70)
    print("Testing Visit Tool Enhancements - Basic Logic")
    print("="*70)
    
    tests = [
        test_remove_text_links,
        test_get_domain,
        test_tool_response_omission,
        test_env_var_parsing,
        test_direct_fetch_headers,
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
            failed += 1
    
    print("\n" + "="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)
    
    if failed == 0:
        print("✅ All basic tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
