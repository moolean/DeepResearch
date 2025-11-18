#!/usr/bin/env python3
"""
Test script for Visit API (Web page reading via Jina and summarization via OpenAI-compatible API)
Tests the availability of JINA_API_KEYS, API_KEY, API_BASE, and SUMMARY_MODEL_NAME
Also tests the new direct URL fetch functionality
"""
import os
import sys
import requests
from openai import OpenAI

# Add inference directory to path for testing direct fetch
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'inference'))

def test_jina_api():
    """Test Jina reader API"""
    print("\n=== Testing Jina Reader API ===")
    
    # Check environment variable
    jina_key = os.environ.get('JINA_API_KEYS')
    if not jina_key or jina_key == 'your_key':
        print("❌ FAILED: JINA_API_KEYS not configured in .env file")
        print("   Please set JINA_API_KEYS in your .env file")
        print("   Get your key from: https://jina.ai/")
        return False
    
    print(f"✓ JINA_API_KEYS is set")
    
    # Test actual API call
    try:
        headers = {
            "Authorization": f"Bearer {jina_key}",
        }
        # Test with a simple, reliable URL
        response = requests.get(
            "https://r.jina.ai/https://example.com",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200 and len(response.text) > 0:
            print("✓ Jina Reader API is accessible")
            print(f"  Response status: {response.status_code}")
            print(f"  Content length: {len(response.text)} characters")
            print("✅ PASSED: Jina Reader API test successful")
            return True
        else:
            print(f"❌ FAILED: Jina API returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Jina Reader API connection error: {str(e)}")
        print("   Please check your internet connection and API key")
        return False

def test_summary_api():
    """Test summary model API (OpenAI-compatible)"""
    print("\n=== Testing Summary Model API ===")
    
    # Check environment variables
    api_key = os.environ.get('API_KEY')
    api_base = os.environ.get('API_BASE')
    model_name = os.environ.get('SUMMARY_MODEL_NAME', '')
    
    if not api_key or api_key == 'your_key':
        print("❌ FAILED: API_KEY not configured in .env file")
        print("   Please set API_KEY in your .env file")
        return False
    
    if not api_base or api_base == 'your_api_base':
        print("❌ FAILED: API_BASE not configured in .env file")
        print("   Please set API_BASE in your .env file")
        return False
    
    print(f"✓ API_KEY is set")
    print(f"✓ API_BASE is set: {api_base}")
    if model_name:
        print(f"✓ SUMMARY_MODEL_NAME is set: {model_name}")
    
    # Test actual API call
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=api_base,
        )
        
        messages = [{"role": "user", "content": "Hello, this is a test message."}]
        
        response = client.chat.completions.create(
            model=model_name if model_name else "gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=50
        )
        
        if response and response.choices and len(response.choices) > 0:
            print("✓ Summary Model API is accessible")
            print(f"  Model: {response.model if hasattr(response, 'model') else 'N/A'}")
            print(f"  Response length: {len(response.choices[0].message.content)} characters")
            print("✅ PASSED: Summary Model API test successful")
            return True
        else:
            print("❌ FAILED: Summary Model API returned empty response")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Summary Model API error: {str(e)}")
        print("   Please check your API_KEY, API_BASE, and SUMMARY_MODEL_NAME configuration")
        return False

def test_direct_fetch():
    """Test direct URL fetch functionality"""
    print("\n=== Testing Direct URL Fetch ===")
    
    # Check if USE_DIRECT_FETCH is enabled
    use_direct = os.environ.get('USE_DIRECT_FETCH', 'false').lower() == 'true'
    print(f"ℹ USE_DIRECT_FETCH is set to: {use_direct}")
    
    # Test that the module can be imported and initialized
    try:
        import tool_visit
        visit = tool_visit.Visit()
        print("✓ Visit module imported and initialized successfully")
        
        # Check if trafilatura is available
        try:
            import trafilatura
            print("✓ trafilatura is installed")
        except ImportError:
            print("⚠ WARNING: trafilatura is not installed. Direct fetch will not work.")
            print("   Install with: pip install trafilatura")
            return False
        
        # Check if h2 is available for HTTP/2 support
        try:
            import h2
            print("✓ h2 is installed (HTTP/2 support available)")
        except ImportError:
            print("⚠ WARNING: h2 is not installed. HTTP/2 support is disabled.")
            print("   Install with: pip install h2")
            return False
        
        print("✅ PASSED: Direct fetch dependencies are available")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error testing direct fetch: {str(e)}")
        return False

def test_visit_api():
    """Test complete visit functionality"""
    print("\n=== Testing Complete Visit API ===")
    
    # Test Jina API (if not using direct fetch)
    use_direct = os.environ.get('USE_DIRECT_FETCH', 'false').lower() == 'true'
    
    if use_direct:
        print("\nℹ USE_DIRECT_FETCH is enabled, skipping Jina API test")
        jina_ok = True  # Skip Jina test if using direct fetch
        direct_ok = test_direct_fetch()
    else:
        print("\nℹ USE_DIRECT_FETCH is disabled, testing Jina API")
        jina_ok = test_jina_api()
        direct_ok = test_direct_fetch()  # Still check dependencies
    
    summary_ok = test_summary_api()
    
    if jina_ok and summary_ok and direct_ok:
        print("\n✅ PASSED: All Visit API components are working")
        return True
    else:
        print("\n❌ FAILED: Some Visit API components are not working")
        if not jina_ok:
            print("   - Jina API test failed")
        if not summary_ok:
            print("   - Summary API test failed")
        if not direct_ok:
            print("   - Direct fetch dependencies test failed")
        return False

if __name__ == "__main__":
    success = test_visit_api()
    sys.exit(0 if success else 1)
