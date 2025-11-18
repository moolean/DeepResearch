#!/usr/bin/env python3
"""
Test script for lightllm_ChatCompletions implementation.
This validates that the code is runnable and supports tool calling.
"""

import sys
sys.path.insert(0, "/mnt/afs/yaotiankuo/agents/fc_workspace/DeepResearch")
import json
from inference.openai_middleware import LightLLMClient, ChatCompletionMessage

client = LightLLMClient(
            api_key="test_key",
            base_url="http://10.119.26.119:8080/generate",
            timeout=60.0
        )

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
    {"role": "user", "content": "What is the weather in shanghai?"}
]
for i in range(100):
    response = client.chat.completions.create(
        model="qwen3-235b-a22b-instruct-2507",
        messages=messages,
        tools=tools,
        stop=["\n<tool_response>", "<tool_response>"],
        temperature=0.6,
        top_p=0.95,
        max_tokens=1024,
    )

    print("Response:", repr(response.choices[0].message.content))