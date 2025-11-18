#!/usr/bin/env python3
"""
Test script for Python Interpreter API (SandboxFusion)
Tests the availability of SANDBOX_FUSION_ENDPOINT and code execution functionality
"""
import os
import sys

def test_python_interpreter_api():
    """Test Python Interpreter (SandboxFusion) API"""
    print("\n=== Testing Python Interpreter API ===")
    
    # Check environment variable
    sandbox_endpoint = os.environ.get('SANDBOX_FUSION_ENDPOINT')
    if not sandbox_endpoint or sandbox_endpoint == 'your_sandbox_endpoint':
        print("❌ FAILED: SANDBOX_FUSION_ENDPOINT not configured in .env file")
        print("   Please set SANDBOX_FUSION_ENDPOINT in your .env file")
        print("   See: https://github.com/bytedance/SandboxFusion")
        return False
    
    print(f"✓ SANDBOX_FUSION_ENDPOINT is set")
    
    # Parse endpoints
    endpoints = sandbox_endpoint.split(',')
    print(f"  Found {len(endpoints)} endpoint(s)")
    
    # Test actual API call
    try:
        from sandbox_fusion import run_code, RunCodeRequest
        
        # Simple test code
        test_code = "print('Hello from sandbox')\nresult = 2 + 2\nprint(f'Result: {result}')"
        
        success_count = 0
        for i, endpoint in enumerate(endpoints, 1):
            endpoint = endpoint.strip()
            try:
                print(f"\n  Testing endpoint {i}/{len(endpoints)}: {endpoint}")
                code_result = run_code(
                    RunCodeRequest(code=test_code, language='python', run_timeout=10),
                    max_attempts=1,
                    client_timeout=10,
                    endpoint=endpoint
                )
                
                if code_result and code_result.run_result:
                    stdout = code_result.run_result.stdout or ""
                    stderr = code_result.run_result.stderr or ""
                    
                    if "Hello from sandbox" in stdout and "Result: 4" in stdout:
                        print(f"  ✓ Endpoint {i} is working")
                        success_count += 1
                    else:
                        print(f"  ⚠ Endpoint {i} returned unexpected output")
                        print(f"    stdout: {stdout[:100]}")
                        print(f"    stderr: {stderr[:100]}")
                else:
                    print(f"  ⚠ Endpoint {i} returned no result")
                    
            except Exception as e:
                print(f"  ⚠ Endpoint {i} failed: {str(e)[:100]}")
        
        if success_count > 0:
            print(f"\n✅ PASSED: {success_count}/{len(endpoints)} endpoint(s) working")
            return True
        else:
            print("\n❌ FAILED: No working endpoints found")
            return False
            
    except ImportError as e:
        print(f"❌ FAILED: sandbox_fusion module not installed: {str(e)}")
        print("   Please install: pip install sandbox-fusion")
        return False
    except Exception as e:
        print(f"❌ FAILED: Python Interpreter API error: {str(e)}")
        print("   Please check your SANDBOX_FUSION_ENDPOINT configuration")
        return False

if __name__ == "__main__":
    success = test_python_interpreter_api()
    sys.exit(0 if success else 1)
