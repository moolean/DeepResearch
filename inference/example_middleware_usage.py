#!/usr/bin/env python3
"""
Example demonstrating the use of the OpenAI-compatible middleware.

This script shows how to:
1. Use the middleware instead of the openai library
2. Make API calls with OpenAI-style syntax
3. Handle responses in the same way as the openai library
"""

import os
import sys

# Set environment variable to use middleware
os.environ['USE_OPENAI_MIDDLEWARE'] = 'true'

from openai_middleware import OpenAICompatibleClient

def example_basic_usage():
    """
    Basic example of using the middleware.
    This mimics exactly how you would use the OpenAI client.
    """
    print("="*70)
    print("Example 1: Basic Middleware Usage")
    print("="*70)
    
    # Initialize the client (same API as OpenAI)
    client = OpenAICompatibleClient(
        api_key="your_api_key",
        base_url="https://api.example.com/v1",
        timeout=60.0
    )
    
    # Prepare messages (same format as OpenAI)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    
    print("\n1. Client initialized")
    print(f"   API Base: {client.base_url}")
    print(f"   Timeout: {client.timeout}s")
    
    print("\n2. Messages prepared:")
    for msg in messages:
        print(f"   - {msg['role']}: {msg['content'][:50]}...")
    
    print("\n3. Making API call...")
    print("   client.chat.completions.create(...)")
    
    # Note: This would make an actual HTTP request if the endpoint exists
    # For demonstration, we just show the interface
    print("\n✓ Middleware maintains exact same interface as OpenAI client")
    print("  - Same initialization: OpenAI(api_key=..., base_url=...)")
    print("  - Same API call: client.chat.completions.create(...)")
    print("  - Same parameters: model, messages, temperature, max_tokens, etc.")


def example_react_agent_usage():
    """
    Example of how the middleware is used in react_agent.py.
    """
    print("\n" + "="*70)
    print("Example 2: Usage in react_agent.py")
    print("="*70)
    
    print("\nIn react_agent.py, the import changes based on environment:")
    print("""
    # Import middleware or OpenAI based on configuration
    USE_MIDDLEWARE = os.getenv('USE_OPENAI_MIDDLEWARE', 'false').lower() == 'true'
    if USE_MIDDLEWARE:
        from openai_middleware import OpenAICompatibleClient as OpenAI
        from openai_middleware import APIError, APIConnectionError, APITimeoutError
    else:
        from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
    """)
    
    print("\nThen the code uses it exactly the same way:")
    print("""
    client = OpenAI(
        api_key=openai_api_key,
        base_url=openai_api_base,
        timeout=600.0,
    )
    
    response = client.chat.completions.create(
        model=self.model,
        messages=msgs,
        temperature=0.6,
        top_p=0.95,
        max_tokens=10000,
    )
    
    content = response.choices[0].message.content
    """)
    
    print("\n✓ No changes needed to existing code!")
    print("  - Just set USE_OPENAI_MIDDLEWARE=true in .env")
    print("  - All API calls work exactly the same")


def example_tools_dict_in_results():
    """
    Example of how tools dict appears in result files.
    """
    print("\n" + "="*70)
    print("Example 3: Tools Dict in Results")
    print("="*70)
    
    import json
    
    # Example result structure
    result = {
        "question": "What is machine learning?",
        "answer": "Machine learning is...",
        "prediction": "Machine learning is a subset of AI...",
        "termination": "answer",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is machine learning?"}
        ],
        "tools": {
            "search": {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Perform Google web searches",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "visit": {
                "type": "function",
                "function": {
                    "name": "visit",
                    "description": "Visit webpage(s) and return summary",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "array"},
                            "goal": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
    
    print("\nExample result entry in JSONL file:")
    print(json.dumps(result, indent=2, ensure_ascii=False)[:500] + "...")
    
    print("\n✓ Every result now includes 'tools' field")
    print(f"  - Tools used in this example: {list(result['tools'].keys())}")
    print("  - Contains full OpenAI-format definitions")
    print("  - Enables tool usage analysis")


def example_benefits():
    """
    Explain the benefits of these changes.
    """
    print("\n" + "="*70)
    print("Benefits of These Changes")
    print("="*70)
    
    benefits = [
        ("Middleware Option", [
            "✓ No dependency on openai library if not needed",
            "✓ Full control over HTTP requests",
            "✓ Easier debugging of network issues",
            "✓ Works with any OpenAI-compatible API",
            "✓ Lightweight alternative using only requests library"
        ]),
        ("Tools Dict in Results", [
            "✓ Track which tools were actually used",
            "✓ Analyze tool usage patterns",
            "✓ Reproduce exact tool configurations",
            "✓ Debug tool-related issues",
            "✓ Understand agent behavior better"
        ]),
        ("Backward Compatibility", [
            "✓ Existing code works without changes",
            "✓ Optional feature - enable when needed",
            "✓ Can switch between openai and middleware",
            "✓ No breaking changes"
        ])
    ]
    
    for title, items in benefits:
        print(f"\n{title}:")
        for item in items:
            print(f"  {item}")


if __name__ == "__main__":
    print("\n" + "🚀 " + "="*66 + " 🚀")
    print("   OpenAI Middleware & Tools Dict - Usage Examples")
    print("🚀 " + "="*66 + " 🚀\n")
    
    example_basic_usage()
    example_react_agent_usage()
    example_tools_dict_in_results()
    example_benefits()
    
    print("\n" + "="*70)
    print("Configuration")
    print("="*70)
    print("""
To enable the middleware, add to your .env file:
    USE_OPENAI_MIDDLEWARE=true

The tools dict is automatically included in all results.
No configuration needed!
    """)
    
    print("="*70)
    print("For more information, see:")
    print("  - CONFIGURATION_GUIDE.md")
    print("  - inference/openai_middleware.py")
    print("  - inference/react_agent.py")
    print("="*70)
