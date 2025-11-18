"""
OpenAI-compatible middleware that uses requests instead of the openai library.
This middleware mimics the OpenAI client interface while using requests for HTTP calls.
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any


class ChatCompletionMessage:
    """Mimics OpenAI's ChatCompletionMessage structure"""
    def __init__(self, content: str, role: str = "assistant"):
        self.content = content
        self.role = role


class ChatCompletionChoice:
    """Mimics OpenAI's ChatCompletionChoice structure"""
    def __init__(self, message: ChatCompletionMessage, index: int = 0):
        self.message = message
        self.index = index
        self.finish_reason = "stop"


class ChatCompletion:
    """Mimics OpenAI's ChatCompletion structure"""
    def __init__(self, choices: List[ChatCompletionChoice]):
        self.choices = choices
        self.id = f"chatcmpl-{int(time.time())}"
        self.object = "chat.completion"
        self.created = int(time.time())
        self.model = "unknown"


class ChatCompletions:
    """Mimics OpenAI's chat.completions API"""
    def __init__(self, api_key: str, base_url: str, timeout: float = 600.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def create(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.6,
        top_p: float = 0.95,
        max_tokens: int = 10000,
        stop: Optional[List[str]] = None,
        presence_penalty: float = 1.1,
        logprobs: bool = False,
        **kwargs
    ) -> ChatCompletion:
        """
        Create a chat completion using requests instead of OpenAI library.
        
        Args:
            model: The model to use
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            presence_penalty: Presence penalty
            logprobs: Whether to return log probabilities
            **kwargs: Additional parameters
        
        Returns:
            ChatCompletion object with response
        """
        # Construct the request payload in OpenAI format
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "presence_penalty": presence_penalty,
        }
        
        if stop:
            payload["stop"] = stop
        
        if logprobs:
            payload["logprobs"] = True
        
        # Add any additional kwargs
        payload.update(kwargs)
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Make the request using requests library
        url = f"{self.base_url}/chat/completions"
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        
        # Raise exception for bad status codes
        response.raise_for_status()
        
        # Parse the response
        response_data = response.json()
        
        # Convert response to OpenAI-compatible format
        choices = []
        for choice_data in response_data.get("choices", []):
            message_data = choice_data.get("message", {})
            message = ChatCompletionMessage(
                content=message_data.get("content", ""),
                role=message_data.get("role", "assistant")
            )
            choice = ChatCompletionChoice(message=message, index=choice_data.get("index", 0))
            choices.append(choice)
        
        return ChatCompletion(choices=choices)


class Chat:
    """Mimics OpenAI's chat API"""
    def __init__(self, api_key: str, base_url: str, timeout: float = 600.0):
        self.completions = ChatCompletions(api_key, base_url, timeout)


class OpenAICompatibleClient:
    """
    OpenAI-compatible client that uses requests instead of the openai library.
    
    This client mimics the OpenAI client interface:
    client = OpenAICompatibleClient(api_key="...", base_url="...")
    response = client.chat.completions.create(...)
    """
    def __init__(self, api_key: str, base_url: str, timeout: float = 600.0):
        """
        Initialize the OpenAI-compatible client.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the API endpoint
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.chat = Chat(api_key, base_url, timeout)


# Exception classes to maintain compatibility
class APIError(Exception):
    """API Error exception"""
    pass


class APIConnectionError(Exception):
    """API Connection Error exception"""
    pass


class APITimeoutError(Exception):
    """API Timeout Error exception"""
    pass
