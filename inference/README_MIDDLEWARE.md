# OpenAI Middleware Implementation

This directory contains an OpenAI-compatible middleware that uses the `requests` library instead of the official `openai` Python SDK.

## Overview

The middleware (`openai_middleware.py`) provides a drop-in replacement for the OpenAI client that:

1. **Mimics the OpenAI API structure** - Uses the same interface (`client.chat.completions.create`)
2. **Uses requests library** - Makes HTTP calls with `requests` instead of the openai SDK
3. **Maintains full compatibility** - Works as a direct replacement without code changes
4. **Supports all parameters** - Temperature, top_p, max_tokens, stop sequences, etc.

## Quick Start

### Enable the Middleware

Add to your `.env` file:

```bash
USE_OPENAI_MIDDLEWARE=true
```

That's it! The `react_agent.py` will automatically use the middleware.

### How It Works

The middleware is conditionally imported in `react_agent.py`:

```python
USE_MIDDLEWARE = os.getenv('USE_OPENAI_MIDDLEWARE', 'false').lower() == 'true'
if USE_MIDDLEWARE:
    from openai_middleware import OpenAICompatibleClient as OpenAI
    from openai_middleware import APIError, APIConnectionError, APITimeoutError
else:
    from openai import OpenAI, APIError, APIConnectionError, APITimeoutError
```

All subsequent code uses `OpenAI` the same way, regardless of which implementation is imported.

## Architecture

### Class Structure

```
OpenAICompatibleClient
├── chat: Chat
│   └── completions: ChatCompletions
│       └── create() -> ChatCompletion
└── api_key, base_url, timeout
```

### Request Flow

1. **Input**: OpenAI-format parameters (model, messages, temperature, etc.)
2. **Transform**: Convert to JSON payload
3. **HTTP Call**: Use `requests.post()` with proper headers
4. **Response**: Parse JSON response
5. **Output**: Return OpenAI-compatible `ChatCompletion` object

### Example Usage

```python
from openai_middleware import OpenAICompatibleClient

client = OpenAICompatibleClient(
    api_key="your_api_key",
    base_url="https://api.example.com/v1",
    timeout=60.0
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.7,
    max_tokens=100
)

content = response.choices[0].message.content
print(content)
```

## Benefits

### 1. Flexibility
- Use any HTTP debugging tools (e.g., mitmproxy)
- Add custom headers or authentication
- Implement retry logic easily
- Mock responses for testing

### 2. Simplicity
- Only depends on `requests` library
- No heavy SDK dependencies
- Easier to understand and debug
- Full control over HTTP layer

### 3. Compatibility
- Works with any OpenAI-compatible API
- No vendor lock-in
- Easy to switch between providers
- Supports custom endpoints

## Configuration Options

The middleware respects the same environment variables as the regular OpenAI integration:

| Variable | Description | Example |
|----------|-------------|---------|
| `USE_OPENAI_MIDDLEWARE` | Enable the middleware | `true` |
| `INFERENCE_API_BASE` | API endpoint URL | `https://api.openai.com/v1` |
| `INFERENCE_API_KEY` | API authentication key | `sk-...` |

## Supported Parameters

The `create()` method supports all standard OpenAI parameters:

- `model` (required) - Model identifier
- `messages` (required) - List of message dictionaries
- `temperature` - Sampling temperature (0.0-2.0)
- `top_p` - Nucleus sampling parameter
- `max_tokens` - Maximum tokens to generate
- `stop` - List of stop sequences
- `presence_penalty` - Presence penalty
- `frequency_penalty` - Frequency penalty
- `logprobs` - Return log probabilities
- `n` - Number of completions
- `stream` - Stream responses (not yet implemented)

## Error Handling

The middleware includes compatible exception classes:

```python
from openai_middleware import APIError, APIConnectionError, APITimeoutError

try:
    response = client.chat.completions.create(...)
except APIConnectionError as e:
    print(f"Connection failed: {e}")
except APITimeoutError as e:
    print(f"Request timed out: {e}")
except APIError as e:
    print(f"API error: {e}")
```

These exceptions maintain compatibility with code that handles OpenAI SDK exceptions.

## Testing

Run the example script to see the middleware in action:

```bash
cd inference
python example_middleware_usage.py
```

Run unit tests:

```bash
python /tmp/test_middleware.py  # After test files are copied
```

## Comparison: OpenAI SDK vs Middleware

| Feature | OpenAI SDK | Middleware |
|---------|-----------|-----------|
| Installation | `pip install openai` | Built-in (uses `requests`) |
| Interface | `client.chat.completions.create()` | Same |
| HTTP Library | Internal | `requests` |
| Dependencies | Many | Only `requests` |
| Debugging | Opaque | Transparent |
| Customization | Limited | Full control |
| Response Format | OpenAI objects | Same (compatible) |

## Limitations

Current limitations of the middleware:

1. **Streaming not supported** - The `stream=True` parameter is not yet implemented
2. **Advanced features** - Some advanced OpenAI SDK features may not be available
3. **Response parsing** - Assumes standard OpenAI response format

These limitations don't affect typical usage in this project.

## When to Use

**Use the middleware when:**
- You want to reduce dependencies
- You need to debug HTTP requests
- You're using a custom OpenAI-compatible API
- You want full control over the HTTP layer

**Use the OpenAI SDK when:**
- You need streaming responses
- You want automatic retries and error handling
- You're using OpenAI's official API exclusively
- You need the latest OpenAI features

## Future Enhancements

Potential improvements:

- [ ] Add streaming support
- [ ] Implement automatic retries with exponential backoff
- [ ] Add request/response logging
- [ ] Support more OpenAI API endpoints (embeddings, etc.)
- [ ] Add type hints for better IDE support
- [ ] Add async/await support

## Troubleshooting

### Issue: Module not found

**Solution**: Ensure you're in the `inference` directory or add it to PYTHONPATH:

```bash
export PYTHONPATH="/path/to/DeepResearch/inference:$PYTHONPATH"
```

### Issue: Connection errors

**Solution**: Check your API endpoint and key:

```bash
# Test the endpoint manually
curl -X POST https://api.example.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'
```

### Issue: Response format mismatch

**Solution**: The middleware expects OpenAI-compatible response format. Verify your API returns:

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Response text"
      },
      "index": 0
    }
  ]
}
```

## Contributing

When modifying the middleware:

1. Maintain OpenAI API compatibility
2. Add tests for new features
3. Update this documentation
4. Test with both OpenAI and custom endpoints

## Related Files

- `openai_middleware.py` - Middleware implementation
- `react_agent.py` - Uses the middleware conditionally
- `example_middleware_usage.py` - Usage examples and demonstrations
- `CONFIGURATION_GUIDE.md` - Overall configuration documentation

## Support

For issues or questions:
- Check the [FAQ](../FAQ.md)
- Review the [Configuration Guide](../CONFIGURATION_GUIDE.md)
- Open an issue on GitHub

---

**Note**: This middleware is designed for flexibility and control. For production use with OpenAI's official API, the official SDK is recommended.
