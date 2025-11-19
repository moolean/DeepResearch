# call_server Method Updates

## Overview

The `call_server` method in `inference/tool_visit.py` has been updated to follow standard OpenAI API format, returning a structured response with `content`, `reasoning_content`, and `tool_calls` fields.

## Changes Made

### 1. Updated `call_server` Method Signature and Return Value

**Before:**
```python
def call_server(self, msgs, max_retries=2):
    # ... API call logic ...
    return content  # Returns string
```

**After:**
```python
def call_server(self, msgs, max_retries=2):
    """
    Standard OpenAI API call with retry and error handling.
    
    Args:
        msgs: List of message dicts in OpenAI format (with role, content, reasoning_content, tool_calls)
        max_retries: Maximum number of retry attempts
        
    Returns:
        dict: Response with 'content', 'reasoning_content', and 'tool_calls' fields
    """
    # ... API call logic ...
    return {
        'content': content,
        'reasoning_content': reasoning_content,
        'tool_calls': tool_calls
    }
```

### 2. Enhanced OpenAI Middleware

#### ChatCompletionMessage Class
Added `reasoning_content` field support:

```python
class ChatCompletionMessage:
    def __init__(self, content: str, role: str = "assistant", 
                 tool_calls: Optional[List[Dict]] = None, 
                 reasoning_content: Optional[str] = None):
        self.content = content
        self.role = role
        self.tool_calls = tool_calls
        self.reasoning_content = reasoning_content  # NEW
```

#### Tool Call Parsing from Content
The middleware now:

1. **Parses tool_calls from content** if `tool_calls` field is not present:
```python
if not tool_calls and "<tool_call>" in content:
    # Parse tool_calls from <tool_call>...</tool_call> tags
    toolcall_pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
    toolcalls_matches = toolcall_pattern.findall(content)
    # Convert to OpenAI format...
```

2. **Removes tool_call tags from content** when `tool_calls` field exists:
```python
if tool_calls:
    content = re.sub(r"<tool_call>\s*\{.*?\}\s*</tool_call>", "", content, flags=re.DOTALL)
    content = content.strip()
```

### 3. Updated Usage in `readpage_jina`

All calls to `call_server` now extract the content field:

**Before:**
```python
raw = summary_page_func(messages, max_retries=max_retries)
```

**After:**
```python
response = summary_page_func(messages, max_retries=max_retries)
raw = response.get('content', '') if isinstance(response, dict) else response
```

## Usage Examples

### Basic Usage

```python
# Call the server
response = self.call_server(messages, max_retries=2)

# Extract fields
content = response.get('content', '')
reasoning_content = response.get('reasoning_content', '')
tool_calls = response.get('tool_calls')
```

### With Full Message History

```python
# Prepare messages with full context
messages = [
    {
        "role": "user",
        "content": "User question"
    },
    {
        "role": "assistant",
        "content": "Assistant response",
        "reasoning_content": "Thinking process...",
        "tool_calls": [...]  # Previous tool calls
    },
    {
        "role": "user",
        "content": "Follow-up question"
    }
]

# Call server preserves full history
response = self.call_server(messages)
```

### Error Handling

```python
response = self.call_server(messages, max_retries=3)

if not response.get('content'):
    # Handle empty response
    print("Failed to get response from server")
else:
    content = response['content']
    # Process content...
```

## Response Format

The `call_server` method now returns a dictionary with three fields:

```python
{
    'content': str,           # Main response content
    'reasoning_content': str, # Reasoning/thinking process (may be empty)
    'tool_calls': list|None   # List of tool calls in OpenAI format, or None
}
```

### Tool Calls Format

When present, `tool_calls` follows OpenAI format:

```python
[
    {
        "id": "call_0_1234567890",
        "type": "function",
        "function": {
            "name": "search",
            "arguments": "{\"query\": \"test\"}"
        }
    }
]
```

## Middleware Behavior

### Case 1: Response with tool_calls field

**Input:**
```json
{
  "choices": [{
    "message": {
      "content": "I will search for that.",
      "tool_calls": [{"id": "call_1", "type": "function", ...}]
    }
  }]
}
```

**Output:**
- `content`: "I will search for that."
- `tool_calls`: [{"id": "call_1", ...}]
- No modification to content

### Case 2: Response with tool_call tags in content

**Input:**
```json
{
  "choices": [{
    "message": {
      "content": "Let me search.\n<tool_call>{\"name\": \"search\", \"arguments\": {\"query\": \"test\"}}</tool_call>"
    }
  }]
}
```

**Output:**
- `content`: "Let me search." (tool_call tags removed)
- `tool_calls`: [{"id": "call_0_...", "type": "function", "function": {"name": "search", ...}}]

### Case 3: Response without tool_calls

**Input:**
```json
{
  "choices": [{
    "message": {
      "content": "Here is the answer.",
      "reasoning_content": "I thought about..."
    }
  }]
}
```

**Output:**
- `content`: "Here is the answer."
- `reasoning_content`: "I thought about..."
- `tool_calls`: None

## Benefits

1. **Standardization**: Follows OpenAI API format consistently
2. **Full Context**: Preserves reasoning_content and tool_calls across conversation history
3. **Flexibility**: Handles both tool_calls field and tool_call tags in content
4. **Clean Content**: Automatically removes tool_call tags when appropriate
5. **Error Handling**: Returns empty dict on failure, preventing downstream errors

## Backward Compatibility

The changes maintain backward compatibility by:
- Checking if response is dict before extracting fields
- Providing fallback to original string format: `response.get('content', '') if isinstance(response, dict) else response`
- Returning empty strings/None on failure instead of raising exceptions

## Testing

All changes have been tested with:
- ✅ Unit tests for response format
- ✅ Unit tests for tool_call parsing
- ✅ Syntax validation
- ✅ Security scan (CodeQL - no vulnerabilities)

## Migration Guide

If you have code that uses `call_server` directly:

**Old Code:**
```python
result = visit.call_server(messages)
# result is a string
```

**New Code:**
```python
response = visit.call_server(messages)
result = response.get('content', '')  # Extract content field
reasoning = response.get('reasoning_content', '')  # Optional
tool_calls = response.get('tool_calls')  # Optional
```

## Related Files

- `inference/tool_visit.py`: Updated `call_server` method and its usage
- `inference/openai_middleware.py`: Enhanced to support reasoning_content and tool_call parsing
- `tests/test_call_server.py`: Unit tests for the changes (in /tmp)
