#!/usr/bin/env python3
"""
Test script for Google Scholar API (via Serper)
Tests the availability of SERPER_KEY_ID and Google Scholar search functionality
"""
import os
import sys
import json
import http.client

def test_scholar_api():
    """Test Google Scholar API via Serper"""
    print("\n=== Testing Google Scholar API ===")
    
    # Check environment variable
    serper_key = os.environ.get('SERPER_KEY_ID')
    if not serper_key or serper_key == 'your_key':
        print("❌ FAILED: SERPER_KEY_ID not configured in .env file")
        print("   Please set SERPER_KEY_ID in your .env file")
        print("   Get your key from: https://serper.dev/")
        return False
    
    print(f"✓ SERPER_KEY_ID is set")
    
    # Test actual API call
    try:
        conn = http.client.HTTPSConnection("google.serper.dev", timeout=10)
        payload = json.dumps({
            "q": "machine learning"
        })
        headers = {
            'X-API-KEY': serper_key,
            'Content-Type': 'application/json'
        }
        
        conn.request("POST", "/scholar", payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            results = json.loads(data.decode("utf-8"))
            print("✓ Google Scholar API is accessible")
            print(f"  Response status: {res.status}")
            if 'organic' in results:
                print(f"  Found {len(results['organic'])} results")
            print("✅ PASSED: Google Scholar API test successful")
            return True
        else:
            print(f"❌ FAILED: Google Scholar API returned status {res.status}")
            print(f"   Response: {data.decode('utf-8')[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Google Scholar API connection error: {str(e)}")
        print("   Please check your internet connection and API key")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = test_scholar_api()
    sys.exit(0 if success else 1)
