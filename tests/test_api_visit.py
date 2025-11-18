#!/usr/bin/env python3
"""
Test script for Visit API (Web page reading via Jina and summarization via OpenAI-compatible API)
Tests the availability of JINA_API_KEYS, API_KEY, API_BASE, and SUMMARY_MODEL_NAME
"""
import os
import sys
import requests
from openai import OpenAI

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

def test_visit_api():
    """Test complete visit functionality"""
    print("\n=== Testing Complete Visit API ===")
    
    jina_ok = test_jina_api()
    summary_ok = test_summary_api()
    
    if jina_ok and summary_ok:
        print("\n✅ PASSED: All Visit API components are working")
        return True
    else:
        print("\n❌ FAILED: Some Visit API components are not working")
        return False

if __name__ == "__main__":
    success = test_visit_api()
    sys.exit(0 if success else 1)
