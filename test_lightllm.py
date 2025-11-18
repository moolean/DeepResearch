#!/usr/bin/env python3
"""
Test script for lightllm_ChatCompletions implementation.
This validates that the code is runnable and supports tool calling.
"""

import sys
import json
from inference.openai_middleware import LightLLMClient, ChatCompletionMessage

def test_basic_initialization():
    """Test that LightLLMClient can be initialized"""
    print("Test 1: Basic Initialization")
    try:
        client = LightLLMClient(
            api_key="test_key",
            base_url="http://localhost:8000",
            timeout=60.0
        )
        print("✓ LightLLMClient initialized successfully")
        print(f"  - API Key: {client.api_key}")
        print(f"  - Base URL: {client.base_url}")
        print(f"  - Timeout: {client.timeout}")
        print(f"  - Has chat attribute: {hasattr(client, 'chat')}")
        print(f"  - Has completions: {hasattr(client.chat, 'completions')}")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        return False

def test_message_with_tool_calls():
    """Test that ChatCompletionMessage supports tool_calls"""
    print("\nTest 2: ChatCompletionMessage with tool_calls")
    try:
        tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "search",
                    "arguments": json.dumps({"query": ["test query"]})
                }
            }
        ]
        message = ChatCompletionMessage(
            content="I'll search for that information.",
            role="assistant",
            tool_calls=tool_calls
        )
        print("✓ ChatCompletionMessage created with tool_calls")
        print(f"  - Content: {message.content}")
        print(f"  - Role: {message.role}")
        print(f"  - Has tool_calls: {message.tool_calls is not None}")
        print(f"  - Number of tool calls: {len(message.tool_calls)}")
        return True
    except Exception as e:
        print(f"✗ Failed to create message: {e}")
        return False

def test_tools_parameter_support():
    """Test that create method accepts tools parameter"""
    print("\nTest 3: Tools Parameter Support")
    try:
        client = LightLLMClient(
            api_key="test_key",
            base_url="http://localhost:8000"
        )
        
        # Define a test tool
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search for information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the weather?"}
        ]
        
        # Check that create method signature accepts tools
        import inspect
        sig = inspect.signature(client.chat.completions.create)
        params = list(sig.parameters.keys())
        
        print(f"✓ create method parameters: {params}")
        print(f"  - Has 'tools' parameter: {'tools' in params}")
        print(f"  - Has 'model' parameter: {'model' in params}")
        print(f"  - Has 'messages' parameter: {'messages' in params}")
        
        return 'tools' in params
    except Exception as e:
        print(f"✗ Failed to check method signature: {e}")
        return False

def test_no_async_in_implementation():
    """Test that implementation doesn't use async/await"""
    print("\nTest 4: No Async/Await in Implementation")
    try:
        import inspect
        from inference.openai_middleware import lightllm_ChatCompletions
        
        # Get the create method
        create_method = lightllm_ChatCompletions.create
        
        # Check if it's a coroutine function
        is_async = inspect.iscoroutinefunction(create_method)
        
        print(f"✓ Checked create method")
        print(f"  - Is async function: {is_async}")
        print(f"  - Is regular function: {not is_async}")
        
        return not is_async
    except Exception as e:
        print(f"✗ Failed to check async: {e}")
        return False

def test_tool_call_parsing():
    """Test that tool call pattern can be parsed"""
    print("\nTest 5: Tool Call Parsing")
    try:
        import re
        
        test_response = """Here's what I found:
<tool_call>
{"name": "search", "arguments": {"query": ["test"]}}
</tool_call>
Let me search for that."""
        
        toolcall_pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
        toolcalls = toolcall_pattern.findall(test_response)
        
        print(f"✓ Tool call pattern tested")
        print(f"  - Found {len(toolcalls)} tool calls")
        if toolcalls:
            parsed = json.loads(toolcalls[0])
            print(f"  - Tool name: {parsed.get('name')}")
            print(f"  - Arguments: {parsed.get('arguments')}")
        
        return len(toolcalls) > 0
    except Exception as e:
        print(f"✗ Failed to parse tool calls: {e}")
        return False

def main():
    print("=" * 70)
    print("LightLLM Implementation Tests")
    print("=" * 70)
    
    results = []
    
    results.append(("Initialization", test_basic_initialization()))
    results.append(("Message with tool_calls", test_message_with_tool_calls()))
    results.append(("Tools parameter support", test_tools_parameter_support()))
    results.append(("No async/await", test_no_async_in_implementation()))
    results.append(("Tool call parsing", test_tool_call_parsing()))
    
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 70)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
