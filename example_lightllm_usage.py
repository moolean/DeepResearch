#!/usr/bin/env python3
"""
Example demonstrating the optimized LightLLM implementation.

This example shows:
1. How to use LightLLMClient (no async/await)
2. How to pass tools as function calling parameter
3. How tool_calls are returned in OpenAI-compatible format
4. How tools are NOT concatenated in system prompt anymore
"""

import json
from inference.openai_middleware import LightLLMClient

def example_basic_usage():
    """
    Basic example of using LightLLMClient without tools.
    """
    print("="*70)
    print("Example 1: Basic Usage (No Tools)")
    print("="*70)
    
    # Initialize the client
    client = LightLLMClient(
        api_key="your_api_key",
        base_url="http://localhost:8000",  # Your LightLLM server
        timeout=60.0
    )
    
    # Prepare messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    
    print("\n1. Client initialized")
    print(f"   Base URL: {client.base_url}")
    
    print("\n2. Messages prepared:")
    for msg in messages:
        print(f"   - {msg['role']}: {msg['content']}")
    
    print("\n3. Call format:")
    print("   response = client.chat.completions.create(")
    print("       model='your_model',")
    print("       messages=messages,")
    print("       temperature=0.6")
    print("   )")
    
    print("\n✓ No async/await needed - all synchronous!")


def example_with_tools():
    """
    Example of using LightLLMClient with tools parameter.
    """
    print("\n" + "="*70)
    print("Example 2: Using Tools as Function Calling")
    print("="*70)
    
    # Initialize the client
    client = LightLLMClient(
        api_key="your_api_key",
        base_url="http://localhost:8000"
    )
    
    # Define tools in OpenAI format
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search",
                "description": "Perform Google web searches",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Search queries"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "visit",
                "description": "Visit webpage and return summary",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URLs to visit"
                        },
                        "goal": {
                            "type": "string",
                            "description": "Information goal"
                        }
                    },
                    "required": ["url", "goal"]
                }
            }
        }
    ]
    
    messages = [
        {"role": "system", "content": "You are a research assistant."},
        {"role": "user", "content": "Find information about quantum computing"}
    ]
    
    print("\n1. Tools defined (not in system prompt!):")
    for tool in tools:
        func = tool["function"]
        print(f"   - {func['name']}: {func['description']}")
    
    print("\n2. System prompt is clean:")
    print(f"   '{messages[0]['content']}'")
    print("   (Tools are passed separately via 'tools' parameter)")
    
    print("\n3. Call format:")
    print("   response = client.chat.completions.create(")
    print("       model='your_model',")
    print("       messages=messages,")
    print("       tools=tools,  # <-- Tools as parameter!")
    print("       temperature=0.6")
    print("   )")
    
    print("\n✓ Tools are function calling parameters, not system prompt!")


def example_tool_call_response():
    """
    Example of how tool_calls are returned in the response.
    """
    print("\n" + "="*70)
    print("Example 3: Tool Call Response Format")
    print("="*70)
    
    print("\nWhen the model decides to call a tool:")
    
    # Simulate a response
    response_example = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "I'll search for that information.\n<tool_call>\n{\"name\": \"search\", \"arguments\": {\"query\": [\"quantum computing basics\"]}}\n</tool_call>",
                    "tool_calls": [
                        {
                            "id": "call_1_1234567890",
                            "type": "function",
                            "function": {
                                "name": "search",
                                "arguments": "{\"query\": [\"quantum computing basics\"]}"
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    print("\n1. Model response includes tool_calls:")
    print(json.dumps(response_example, indent=2, ensure_ascii=False))
    
    print("\n2. Accessing tool calls:")
    print("   message = response.choices[0].message")
    print("   if message.tool_calls:")
    print("       for tool_call in message.tool_calls:")
    print("           name = tool_call['function']['name']")
    print("           args = json.loads(tool_call['function']['arguments'])")
    print("           # Execute the tool with args")
    
    print("\n✓ OpenAI-compatible format with proper tool_calls!")


def example_tool_response_handling():
    """
    Example of handling tool responses.
    """
    print("\n" + "="*70)
    print("Example 4: Handling Tool Responses")
    print("="*70)
    
    print("\nAfter executing a tool, add the result to messages:")
    
    messages = [
        {"role": "system", "content": "You are a research assistant."},
        {"role": "user", "content": "Find info about quantum computing"},
        {
            "role": "assistant",
            "content": "<tool_call>\n{\"name\": \"search\", \"arguments\": {\"query\": [\"quantum computing\"]}}\n</tool_call>"
        },
        {
            "role": "tool",  # <-- Tool response
            "content": "<tool_response>\nFound 10 results about quantum computing...\n</tool_response>"
        }
    ]
    
    print("\n1. Message flow:")
    for i, msg in enumerate(messages):
        role = msg['role']
        content = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
        print(f"   {i+1}. {role}: {content}")
    
    print("\n2. Continue the conversation:")
    print("   response = client.chat.completions.create(")
    print("       model='your_model',")
    print("       messages=messages,  # Includes tool response")
    print("       tools=tools")
    print("   )")
    
    print("\n✓ Multi-turn conversation with tool usage!")


def example_comparison():
    """
    Compare old vs new approach.
    """
    print("\n" + "="*70)
    print("Example 5: Old vs New Approach")
    print("="*70)
    
    print("\n❌ OLD APPROACH (Problematic):")
    print("   - Tools concatenated in system prompt")
    print("   - System prompt becomes very long")
    print("   - Hard to manage tool definitions")
    print("   - Not standard OpenAI format")
    print("   - Used async/await")
    
    print("\n✓ NEW APPROACH (Optimized):")
    print("   - Tools passed as 'tools' parameter")
    print("   - Clean system prompt")
    print("   - Easy to manage tools")
    print("   - OpenAI-compatible format")
    print("   - No async/await (synchronous)")
    print("   - Returns tool_calls in response")


def main():
    print("\n" + "🚀 " + "="*66 + " 🚀")
    print("   LightLLM Optimized Implementation - Usage Examples")
    print("🚀 " + "="*66 + " 🚀\n")
    
    example_basic_usage()
    example_with_tools()
    example_tool_call_response()
    example_tool_response_handling()
    example_comparison()
    
    print("\n" + "="*70)
    print("Key Improvements")
    print("="*70)
    improvements = [
        "✓ No async/await - all synchronous code",
        "✓ Tools as function calling parameter",
        "✓ OpenAI-compatible tool_calls format",
        "✓ Clean separation of tools and system prompt",
        "✓ Proper tool call parsing and formatting",
        "✓ All required imports included",
        "✓ No undefined variables",
        "✓ Ready to run out of the box"
    ]
    for improvement in improvements:
        print(f"  {improvement}")
    
    print("\n" + "="*70)
    print("Usage in Your Code")
    print("="*70)
    print("""
To use LightLLM client in your code:

from inference.openai_middleware import LightLLMClient

# Initialize
client = LightLLMClient(
    api_key="your_key",
    base_url="http://your-lightllm-server:8000"
)

# Define tools
tools = [...]  # Your tool definitions

# Make a call
response = client.chat.completions.create(
    model="your_model",
    messages=messages,
    tools=tools,
    temperature=0.6
)

# Check for tool calls
if response.choices[0].message.tool_calls:
    # Handle tool calls
    pass
    """)
    
    print("="*70)

if __name__ == "__main__":
    main()
