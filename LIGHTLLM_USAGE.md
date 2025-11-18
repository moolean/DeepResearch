# LightLLM Client Usage Guide

## Overview

The optimized `LightLLMClient` provides a synchronous, OpenAI-compatible interface for LightLLM API with proper tool calling support.

## Key Features

✓ **No async/await** - All synchronous code  
✓ **Tools as function parameters** - Not concatenated in system prompt  
✓ **OpenAI-compatible format** - Returns standard `tool_calls` structure  
✓ **Clean separation** - Tools and prompts are managed separately  
✓ **Ready to run** - All imports and dependencies included  

## Installation

No additional dependencies needed beyond the standard `requirements.txt`:
```bash
pip install -r requirements.txt
```

## Basic Usage

### 1. Initialize the Client

```python
from inference.openai_middleware import LightLLMClient

client = LightLLMClient(
    api_key="your_api_key",
    base_url="http://localhost:8000",  # Your LightLLM server
    timeout=600.0
)
```

### 2. Simple Chat (No Tools)

```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is the capital of France?"}
]

response = client.chat.completions.create(
    model="your_model",
    messages=messages,
    temperature=0.6,
    top_p=0.95,
    max_tokens=10000
)

content = response.choices[0].message.content
print(content)
```

### 3. Chat with Tools

```python
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
                        "items": {"type": "string"}
                    },
                    "goal": {
                        "type": "string"
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

response = client.chat.completions.create(
    model="your_model",
    messages=messages,
    tools=tools,  # Tools passed as parameter, not in system prompt!
    temperature=0.6
)
```

### 4. Handling Tool Calls

```python
message = response.choices[0].message

# Check if the model wants to call tools
if message.tool_calls:
    for tool_call in message.tool_calls:
        # Extract tool information
        tool_name = tool_call["function"]["name"]
        tool_args = json.loads(tool_call["function"]["arguments"])
        
        # Execute the tool (your implementation)
        if tool_name == "search":
            result = execute_search(tool_args["query"])
        elif tool_name == "visit":
            result = visit_webpage(tool_args["url"], tool_args["goal"])
        
        # Add tool response to messages
        messages.append({
            "role": "assistant",
            "content": message.content
        })
        messages.append({
            "role": "tool",
            "content": f"<tool_response>\n{result}\n</tool_response>"
        })
        
        # Continue the conversation
        response = client.chat.completions.create(
            model="your_model",
            messages=messages,
            tools=tools
        )
```

## Response Format

### Without Tool Calls

```python
response = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "Paris is the capital of France.",
                "tool_calls": None
            }
        }
    ]
}
```

### With Tool Calls

```python
response = {
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "I'll search for that.\n<tool_call>\n{...}\n</tool_call>",
                "tool_calls": [
                    {
                        "id": "call_1_1234567890",
                        "type": "function",
                        "function": {
                            "name": "search",
                            "arguments": '{"query": ["quantum computing"]}'
                        }
                    }
                ]
            }
        }
    ]
}
```

## Configuration Parameters

### Client Initialization

- `api_key` (str): API key for authentication
- `base_url` (str): Base URL for LightLLM server
- `timeout` (float): Request timeout in seconds (default: 600.0)

### Create Completion

- `model` (str, required): Model name
- `messages` (list, required): List of message dicts
- `temperature` (float): Sampling temperature (default: 0.6)
- `top_p` (float): Top-p sampling (default: 0.95)
- `max_tokens` (int): Maximum tokens to generate (default: 10000)
- `stop` (list): Stop sequences (optional)
- `presence_penalty` (float): Presence penalty (default: 1.1)
- `logprobs` (bool): Return log probabilities (default: False)
- `tools` (list): Tool definitions in OpenAI format (optional)
- `top_k` (int): Top-k sampling (default: 50)
- `repetition_penalty` (float): Repetition penalty (default: 1.0)

## Differences from Old Implementation

### ❌ Old Approach (Problematic)

```python
# Tools concatenated in system prompt
system_prompt = base_prompt + tool_definitions_string

# Used async/await
async def call_llm():
    async with aiohttp.ClientSession() as session:
        async with session.post(...) as response:
            ...

# Undefined variables, missing imports
# Not runnable out of the box
```

### ✓ New Approach (Optimized)

```python
# Tools passed as parameter
client.chat.completions.create(
    model=model,
    messages=messages,
    tools=tools  # Separate from system prompt
)

# Synchronous, no async/await
def call_llm():
    response = requests.post(...)
    return parse_response(response)

# All imports included, ready to run
```

## Multimodal Support

The client supports image inputs:

```python
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": "file:///path/to/image.jpg"}
        ]
    }
]

response = client.chat.completions.create(
    model="your_model",
    messages=messages
)
```

## Error Handling

```python
from inference.openai_middleware import APIError, APIConnectionError, APITimeoutError

try:
    response = client.chat.completions.create(
        model="your_model",
        messages=messages,
        tools=tools
    )
except APIConnectionError as e:
    print(f"Connection error: {e}")
except APITimeoutError as e:
    print(f"Timeout error: {e}")
except APIError as e:
    print(f"API error: {e}")
```

## Integration with Existing Code

To integrate with existing code that uses OpenAI client:

```python
# Option 1: Direct replacement
from inference.openai_middleware import LightLLMClient as OpenAI

# Option 2: Conditional import
USE_LIGHTLLM = os.getenv('USE_LIGHTLLM', 'false').lower() == 'true'
if USE_LIGHTLLM:
    from inference.openai_middleware import LightLLMClient as OpenAI
else:
    from openai import OpenAI
```

## Testing

Run the test suite:

```bash
python test_lightllm.py
```

Run the example:

```bash
python example_lightllm_usage.py
```

## Troubleshooting

### Issue: "Connection refused"
**Solution**: Ensure your LightLLM server is running at the specified `base_url`.

### Issue: "Tool calls not parsed"
**Solution**: Ensure the model's response includes tool calls in the format:
```
<tool_call>
{"name": "tool_name", "arguments": {...}}
</tool_call>
```

### Issue: "Image loading fails"
**Solution**: Check that image URLs are accessible or file paths are correct.

## Best Practices

1. **Keep system prompts clean**: Don't concatenate tools into system prompts
2. **Use tools parameter**: Pass tools as a separate parameter
3. **Handle tool responses properly**: Always add tool results to message history
4. **Error handling**: Implement proper retry logic for network errors
5. **Timeout configuration**: Set appropriate timeouts for your use case

## Examples

See the following files for complete examples:
- `test_lightllm.py` - Unit tests
- `example_lightllm_usage.py` - Comprehensive usage examples

## Support

For issues or questions:
1. Check the examples in this repository
2. Review the implementation in `inference/openai_middleware.py`
3. Open an issue on GitHub
