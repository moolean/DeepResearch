#!/usr/bin/env python3
"""
Test backwards compatibility - ensure OpenAICompatibleClient still works.
"""

import sys
from inference.openai_middleware import OpenAICompatibleClient, ChatCompletionMessage

def test_openai_compatible_client():
    """Test that OpenAICompatibleClient still works"""
    print("Testing OpenAICompatibleClient (backwards compatibility)")
    print("=" * 70)
    
    try:
        # Initialize the client
        client = OpenAICompatibleClient(
            api_key="test_key",
            base_url="http://localhost:8000"
        )
        
        print("✓ OpenAICompatibleClient initialized")
        print(f"  - Has chat: {hasattr(client, 'chat')}")
        print(f"  - Has completions: {hasattr(client.chat, 'completions')}")
        print(f"  - Has create method: {hasattr(client.chat.completions, 'create')}")
        
        # Check method signature
        import inspect
        sig = inspect.signature(client.chat.completions.create)
        params = list(sig.parameters.keys())
        
        print(f"  - Create parameters: {params}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def test_chatcompletion_message():
    """Test ChatCompletionMessage still works without tool_calls"""
    print("\nTesting ChatCompletionMessage (backwards compatibility)")
    print("=" * 70)
    
    try:
        # Old usage without tool_calls
        message = ChatCompletionMessage(
            content="Test message",
            role="assistant"
        )
        
        print("✓ ChatCompletionMessage created without tool_calls")
        print(f"  - Content: {message.content}")
        print(f"  - Role: {message.role}")
        print(f"  - tool_calls is None: {message.tool_calls is None}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

def main():
    print("\n" + "🔄 " + "="*66 + " 🔄")
    print("   Backwards Compatibility Tests")
    print("🔄 " + "="*66 + " 🔄\n")
    
    results = []
    results.append(test_openai_compatible_client())
    results.append(test_chatcompletion_message())
    
    print("\n" + "="*70)
    print("Summary")
    print("="*70)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ All {total} backwards compatibility tests passed")
        print("\nExisting code using OpenAICompatibleClient will continue to work!")
    else:
        print(f"✗ {total - passed} tests failed")
    
    print("="*70)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
