#!/usr/bin/env python3
"""
Test script for validating the optimized OpenAI middleware.
Tests streaming support, field separation, and error handling.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
from unittest.mock import Mock, patch, MagicMock
from inference.openai_middleware import (
    ChatCompletions, 
    lightllm_ChatCompletions,
    OpenAICompatibleClient,
    LightLLMClient,
    ChatCompletionMessage,
    ToolCall,
    ToolCallFunction
)


def test_parse_tool_calls():
    """Test tool call parsing with various formats"""
    print("\n=== Testing tool call parsing ===")
    
    client = ChatCompletions(api_key="test", base_url="http://test.com")
    
    # Test valid tool calls
    tool_calls_data = [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "search",
                "arguments": '{"query": "test"}'
            }
        }
    ]
    
    result = client._parse_tool_calls_from_response(tool_calls_data)
    assert result is not None, "Should parse valid tool calls"
    assert len(result) == 1, "Should have one tool call"
    assert result[0].function.name == "search", "Tool name should match"
    print("✓ Valid tool calls parsed successfully")
    
    # Test empty tool calls
    result = client._parse_tool_calls_from_response([])
    assert result is None, "Should return None for empty list"
    print("✓ Empty tool calls handled correctly")
    
    # Test malformed tool calls (should not crash)
    malformed = [{"invalid": "data"}]
    result = client._parse_tool_calls_from_response(malformed)
    # Should handle gracefully
    print("✓ Malformed tool calls handled gracefully")


def test_create_completion_helper():
    """Test the helper method for creating completions"""
    print("\n=== Testing completion creation helper ===")
    
    client = ChatCompletions(api_key="test", base_url="http://test.com")
    
    # Test with all fields
    tool_call = ToolCall(
        id="call_1",
        type="function",
        function=ToolCallFunction(name="test", arguments="{}")
    )
    
    completion = client._create_completion_from_data(
        model="test-model",
        content="Test content",
        reasoning_content="Test reasoning",
        tool_calls=[tool_call]
    )
    
    assert completion.choices[0].message.content == "Test content"
    assert completion.choices[0].message.reasoning_content == "Test reasoning"
    assert completion.choices[0].message.tool_calls is not None
    assert len(completion.choices[0].message.tool_calls) == 1
    print("✓ Completion created with all fields")
    
    # Test with minimal fields
    completion = client._create_completion_from_data(
        model="test-model",
        content="Minimal"
    )
    assert completion.choices[0].message.content == "Minimal"
    assert completion.choices[0].message.reasoning_content is None
    assert completion.choices[0].message.tool_calls is None
    print("✓ Completion created with minimal fields")


def test_aggregate_stream_response():
    """Test streaming response aggregation"""
    print("\n=== Testing stream aggregation ===")
    
    client = ChatCompletions(api_key="test", base_url="http://test.com")
    
    # Mock streaming response
    stream_data = [
        b'data: {"choices": [{"delta": {"content": "Hello"}}]}\n',
        b'data: {"choices": [{"delta": {"content": " world"}}]}\n',
        b'data: {"choices": [{"delta": {"reasoning_content": "thinking"}}]}\n',
        b'data: [DONE]\n'
    ]
    
    mock_response = Mock()
    mock_response.iter_lines.return_value = stream_data
    
    result = client._aggregate_stream_response(mock_response)
    
    assert result['content'] == "Hello world", f"Content should be aggregated, got: {result['content']}"
    assert result['reasoning_content'] == "thinking", "Reasoning should be aggregated"
    print("✓ Stream response aggregated correctly")


def test_lightllm_parse_response():
    """Test LightLLM response parsing"""
    print("\n=== Testing LightLLM response parsing ===")
    
    # Create a mock template
    with patch('inference.openai_middleware.Environment') as mock_env:
        mock_template = Mock()
        mock_template.render.return_value = "test query"
        mock_env.return_value.get_template.return_value = mock_template
        
        client = lightllm_ChatCompletions(api_key="test", base_url="http://test.com")
    
    # Test with reasoning and tool call
    response_text = """<think>
Some reasoning here
</think>
Here is the content
<tool_call>
{"name": "search", "arguments": {"query": "test"}}
</tool_call>"""
    
    parsed = client._parse_lightllm_response(response_text)
    
    assert parsed['reasoning_content'] is not None, "Should extract reasoning"
    assert "Some reasoning here" in parsed['reasoning_content']
    assert parsed['tool_calls'] is not None, "Should extract tool calls"
    assert len(parsed['tool_calls']) == 1
    print("✓ LightLLM response parsed correctly")
    
    # Test without special tags
    simple_response = "Just a simple response"
    parsed = client._parse_lightllm_response(simple_response)
    assert parsed['content'] == simple_response
    assert parsed['reasoning_content'] is None
    assert parsed['tool_calls'] is None
    print("✓ Simple response handled correctly")


def test_non_streaming_create():
    """Test non-streaming create method"""
    print("\n=== Testing non-streaming create ===")
    
    client = ChatCompletions(api_key="test", base_url="http://test.com")
    
    # Mock response
    mock_response_data = {
        "choices": [{
            "message": {
                "content": "Test response",
                "reasoning_content": "Test reasoning",
                "role": "assistant",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "test_function",
                        "arguments": '{"arg": "value"}'
                    }
                }]
            },
            "index": 0
        }]
    }
    
    with patch('requests.post') as mock_post:
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp
        
        completion = client.create(
            model="test-model",
            messages=[{"role": "user", "content": "test"}],
            stream=False
        )
        
        assert completion.choices[0].message.content == "Test response"
        assert completion.choices[0].message.reasoning_content == "Test reasoning"
        assert completion.choices[0].message.tool_calls is not None
        assert len(completion.choices[0].message.tool_calls) == 1
        print("✓ Non-streaming create works correctly")


def test_streaming_create():
    """Test streaming create method"""
    print("\n=== Testing streaming create ===")
    
    client = ChatCompletions(api_key="test", base_url="http://test.com")
    
    # Mock streaming response
    stream_data = [
        b'data: {"choices": [{"delta": {"content": "Streamed"}}]}\n',
        b'data: {"choices": [{"delta": {"content": " response"}}]}\n',
        b'data: [DONE]\n'
    ]
    
    with patch('requests.post') as mock_post:
        mock_resp = Mock()
        mock_resp.iter_lines.return_value = stream_data
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp
        
        completion = client.create(
            model="test-model",
            messages=[{"role": "user", "content": "test"}],
            stream=True
        )
        
        assert "Streamed response" in completion.choices[0].message.content
        print("✓ Streaming create works correctly")


def test_field_separation():
    """Test that fields are properly separated"""
    print("\n=== Testing field separation ===")
    
    # Test ChatCompletionMessage
    msg = ChatCompletionMessage(
        content="content",
        reasoning_content="reasoning",
        tool_calls=[ToolCall("id", "function", ToolCallFunction("name", "args"))]
    )
    
    assert msg.content == "content", "Content should be separate"
    assert msg.reasoning_content == "reasoning", "Reasoning should be separate"
    assert msg.tool_calls is not None, "Tool calls should be separate"
    assert len(msg.tool_calls) == 1
    print("✓ Fields are properly separated in message structure")


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("Running OpenAI Middleware Tests")
    print("="*60)
    
    try:
        test_parse_tool_calls()
        test_create_completion_helper()
        test_aggregate_stream_response()
        test_lightllm_parse_response()
        test_non_streaming_create()
        test_streaming_create()
        test_field_separation()
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)
        return 0
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
