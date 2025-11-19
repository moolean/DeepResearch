#!/usr/bin/env python3
"""
Integration test to verify the middleware works end-to-end.
Tests the complete flow from request to response.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
from unittest.mock import Mock, patch
from inference.openai_middleware import OpenAICompatibleClient, LightLLMClient


def test_openai_client_complete_flow():
    """Test complete flow with OpenAI-compatible client"""
    print("\n=== Testing OpenAI Client Complete Flow ===")
    
    client = OpenAICompatibleClient(
        api_key="test_key",
        base_url="http://test-api.com",
        timeout=30.0
    )
    
    # Mock response with all fields
    mock_response_data = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "test-model",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "Here is my response.",
                "reasoning_content": "Let me think about this...",
                "tool_calls": [{
                    "id": "call_abc123",
                    "type": "function",
                    "function": {
                        "name": "search",
                        "arguments": '{"query": "test query"}'
                    }
                }]
            },
            "finish_reason": "stop"
        }]
    }
    
    with patch('requests.post') as mock_post:
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the weather?"}
        ]
        
        tools = [{
            "type": "function",
            "function": {
                "name": "search",
                "description": "Search for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        }]
        
        # Test non-streaming
        response = client.chat.completions.create(
            model="test-model",
            messages=messages,
            tools=tools,
            stream=False
        )
        
        # Validate response structure
        assert response.choices, "Response should have choices"
        message = response.choices[0].message
        
        # Check field separation
        assert message.content == "Here is my response.", "Content should match"
        assert message.reasoning_content == "Let me think about this...", "Reasoning should match"
        assert message.tool_calls is not None, "Tool calls should be present"
        assert len(message.tool_calls) == 1, "Should have 1 tool call"
        assert message.tool_calls[0].function.name == "search", "Tool name should match"
        
        print("✓ Non-streaming request with all fields successful")
        
        # Test streaming
        stream_data = [
            b'data: {"choices": [{"delta": {"content": "Stream"}}]}\n',
            b'data: {"choices": [{"delta": {"content": "ed"}}]}\n',
            b'data: {"choices": [{"delta": {"reasoning_content": "thinking"}}]}\n',
            b'data: [DONE]\n'
        ]
        
        mock_resp.iter_lines.return_value = stream_data
        
        response = client.chat.completions.create(
            model="test-model",
            messages=messages,
            stream=True
        )
        
        assert "Streamed" in response.choices[0].message.content
        assert response.choices[0].message.reasoning_content == "thinking"
        
        print("✓ Streaming request successful")


def test_lightllm_client_complete_flow():
    """Test complete flow with LightLLM client"""
    print("\n=== Testing LightLLM Client Complete Flow ===")
    
    with patch('inference.openai_middleware.Environment') as mock_env:
        mock_template = Mock()
        mock_template.render.return_value = "rendered query"
        mock_env.return_value.get_template.return_value = mock_template
        
        client = LightLLMClient(
            api_key="test_key",
            base_url="http://test-lightllm.com/generate",
            timeout=30.0
        )
    
    # Mock response with thinking and tool call
    mock_response_data = {
        "generated_text": [
            "<think>\nI need to search for this\n</think>\n" +
            "Let me search for that.\n" +
            "<tool_call>\n{\"name\": \"search\", \"arguments\": {\"query\": \"weather\"}}\n</tool_call>"
        ]
    }
    
    with patch('requests.post') as mock_post:
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp
        
        messages = [
            {"role": "user", "content": "What is the weather?"}
        ]
        
        # Test non-streaming
        response = client.chat.completions.create(
            model="test-model",
            messages=messages,
            stream=False
        )
        
        # Validate response structure
        message = response.choices[0].message
        
        # Check field separation
        assert message.content, "Content should be present"
        assert "<think>" in message.content, "Content should contain original text"
        assert message.reasoning_content is not None, "Reasoning should be extracted"
        assert "I need to search for this" in message.reasoning_content
        assert message.tool_calls is not None, "Tool calls should be extracted"
        assert len(message.tool_calls) == 1
        assert message.tool_calls[0].function.name == "search"
        
        print("✓ LightLLM non-streaming with parsed fields successful")
        
        # Test streaming
        stream_data = [
            b'{"token": {"text": "<think>"}}\n',
            b'{"token": {"text": "thinking"}}\n',
            b'{"token": {"text": "</think>"}}\n',
            b'{"token": {"text": "response"}}\n',
        ]
        
        mock_resp.iter_lines.return_value = stream_data
        
        response = client.chat.completions.create(
            model="test-model",
            messages=messages,
            stream=True
        )
        
        assert response.choices[0].message.content
        print("✓ LightLLM streaming successful")


def test_error_handling():
    """Test error handling scenarios"""
    print("\n=== Testing Error Handling ===")
    
    client = OpenAICompatibleClient(
        api_key="test_key",
        base_url="http://test-api.com"
    )
    
    # Test invalid messages parameter
    try:
        client.chat.completions.create(
            model="test",
            messages=None
        )
        assert False, "Should raise ValueError for None messages"
    except ValueError as e:
        assert "Messages must be" in str(e)
        print("✓ Invalid messages handled correctly")
    
    # Test empty model
    try:
        client.chat.completions.create(
            model="",
            messages=[{"role": "user", "content": "test"}]
        )
        assert False, "Should raise ValueError for empty model"
    except ValueError as e:
        assert "Model parameter" in str(e)
        print("✓ Empty model handled correctly")
    
    # Test connection error
    with patch('requests.post') as mock_post:
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        try:
            client.chat.completions.create(
                model="test",
                messages=[{"role": "user", "content": "test"}]
            )
            assert False, "Should raise ConnectionError"
        except requests.exceptions.ConnectionError:
            print("✓ Connection error handled correctly")
    
    # Test timeout error
    with patch('requests.post') as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")
        
        try:
            client.chat.completions.create(
                model="test",
                messages=[{"role": "user", "content": "test"}]
            )
            assert False, "Should raise Timeout"
        except requests.exceptions.Timeout:
            print("✓ Timeout error handled correctly")


def test_backward_compatibility():
    """Test backward compatibility with embedded tool calls"""
    print("\n=== Testing Backward Compatibility ===")
    
    client = OpenAICompatibleClient(
        api_key="test_key",
        base_url="http://test-api.com"
    )
    
    # Mock response with only tool_calls (no content)
    mock_response_data = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "search",
                        "arguments": '{"q": "test"}'
                    }
                }]
            }
        }]
    }
    
    with patch('requests.post') as mock_post:
        mock_resp = Mock()
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = Mock()
        mock_post.return_value = mock_resp
        
        response = client.chat.completions.create(
            model="test",
            messages=[{"role": "user", "content": "test"}]
        )
        
        # Both fields should be accessible
        assert response.choices[0].message.content == ""
        assert response.choices[0].message.tool_calls is not None
        
        print("✓ Empty content with tool_calls handled correctly")


def run_all_tests():
    """Run all integration tests"""
    print("="*60)
    print("Running Integration Tests")
    print("="*60)
    
    try:
        test_openai_client_complete_flow()
        test_lightllm_client_complete_flow()
        test_error_handling()
        test_backward_compatibility()
        
        print("\n" + "="*60)
        print("✓ All integration tests passed!")
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
