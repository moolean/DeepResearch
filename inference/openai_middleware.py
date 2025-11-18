"""
OpenAI-compatible middleware that uses requests instead of the openai library.
This middleware mimics the OpenAI client interface while using requests for HTTP calls.
"""

import requests
import json
import time
import re
import base64
import logging
from typing import Dict, List, Optional, Any

# Setup logger
logger = logging.getLogger(__name__)


class ChatCompletionMessage:
    """Mimics OpenAI's ChatCompletionMessage structure"""
    def __init__(self, content: str, role: str = "assistant", tool_calls: Optional[List[Dict]] = None):
        self.content = content
        self.role = role
        self.tool_calls = tool_calls


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
        tools: Optional[List[Dict[str, Any]]] = None,
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

class lightllm_ChatCompletions(ChatCompletions):
    """Mimics OpenAI's chat.completions API for LightLLM"""
    def __init__(self, api_key, base_url, timeout = 600):
        self.USER_START = "<|im_start|>user\n"
        self.ASSISTANT_START = "<|im_start|>assistant\n"
        self.IM_END = "<|im_end|>\n"
        self.IMG_TAG = "<img></img>\n"
        self.AUDIO_TAG = "<audio></audio>\n"
        super().__init__(api_key, base_url, timeout)

    def handle_url_sync(self, url):
        """Synchronous version of handle_url for processing image URLs"""
        if url.startswith("file://"):
            with open(url[7:], "rb") as f:
                return base64.b64encode(f.read()).decode()
        else:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            content = response.content
            return base64.b64encode(content).decode()

    def create(self, model, 
                    messages, 
                    temperature = 0.6, 
                    top_p = 0.95, 
                    max_tokens = 10000, 
                    stop = None, 
                    presence_penalty = 1.1, 
                    logprobs = False, 
                    tools = None, 
                    top_k = 50,
                    repetition_penalty = 1.0,
                    **kwargs):
        """
        Create a chat completion using LightLLM API format.
        
        This implementation:
        - Does not use async/await (all synchronous)
        - Supports tools parameter for function calling
        - Parses tool_call responses from the model
        - Returns OpenAI-compatible format with tool_calls
        """
        
        # Build the prompt query in LightLLM format
        query = ""
        
        # Process system message and tools
        if len(messages) > 0 and messages[0]["role"] == "system":
            query += "<|im_start|>system\n" + messages[0]["content"]
            if tools:
                # Add tool definitions to system prompt
                tools_str = []
                for tool in tools:
                    tools_str.append(json.dumps(tool, ensure_ascii=False))
                tool_define = "\n".join(tools_str)
                tool_instruction = "\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n" + tool_define + "\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>"
                query += tool_instruction
            query += "<|im_end|>\n"
            messages = messages[1:]
        elif tools:
            # No system message but we have tools
            tools_str = []
            for tool in tools:
                tools_str.append(json.dumps(tool, ensure_ascii=False))
            tool_define = "\n".join(tools_str)
            tool_instruction = "# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n" + tool_define + "\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>"
            query += "<|im_start|>system\n" + tool_instruction + "<|im_end|>\n"

        images = []

        # Process messages
        for message in messages:
            if message["role"] == "user":
                query += self.USER_START
                if isinstance(message["content"], list):
                    # Multimodal content
                    query_content = ""
                    img_cnt = 0
                    for content in message["content"]:
                        if content["type"] == "image_url":
                            query += self.IMG_TAG
                            img_cnt += 1
                            # Handle image URL synchronously
                            image_url = content.get("image_url", {})
                            if isinstance(image_url, dict):
                                url = image_url.get("url", "")
                            else:
                                url = image_url
                            image_data = self.handle_url_sync(url)
                            images.append({"type": "base64", "data": image_data})
                        elif content["type"] == "text":
                            query_content = content["text"]
                        else:
                            raise ValueError("type must be text, image_url")
                    if img_cnt >= 2:
                        query += f"用户本轮上传了{img_cnt}张图\n"
                    query += query_content + self.IM_END
                else:
                    if isinstance(message["content"], dict):
                        logger.error(f"message content has found being dict: {message['content']}")
                    query += str(message["content"]) + self.IM_END
            elif message["role"] == "assistant":
                query += self.ASSISTANT_START
                query += message["content"] + self.IM_END
            elif message["role"] == "tool":
                query += self.USER_START
                query_content = f"<tool_response>\n{message['content']}\n</tool_response>"
                query += query_content + self.IM_END
            else:
                raise ValueError("role must be user, assistant, or tool")
        
        query += self.ASSISTANT_START

        # Construct the payload for LightLLM API
        payload = {
            "inputs": query,
            "parameters": {
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "repetition_penalty": repetition_penalty,
                "max_new_tokens": max_tokens,
                "do_sample": True,
                "stop_sequences": ["<|im_end|>"]
            },
        }

        # Add multimodal params if images exist
        if images:
            payload["multimodal_params"] = {"images": images}

        # Make synchronous HTTP request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        url = f"{self.base_url}/generate"  # LightLLM generate endpoint
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        response_data = response.json()

        # Parse the generated text
        if isinstance(response_data, list):
            response_text = response_data[0].get("generated_text", [""])[0]
        else:
            response_text = response_data.get("generated_text", [""])[0]
        
        # Parse tool calls from response
        toolcall_pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
        toolcalls_matches = toolcall_pattern.findall(response_text)
        
        # Build tool_calls list in OpenAI format
        tool_calls_list = None
        if toolcalls_matches:
            tool_calls_list = []
            for i, toolcall_str in enumerate(toolcalls_matches):
                try:
                    toolcall_json = json.loads(toolcall_str)
                    tool_call = {
                        "id": f"call_{i}_{int(time.time())}",
                        "type": "function",
                        "function": {
                            "name": toolcall_json.get("name", ""),
                            "arguments": json.dumps(toolcall_json.get("arguments", {}))
                        }
                    }
                    tool_calls_list.append(tool_call)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse tool call: {toolcall_str}")
        
        # Create OpenAI-compatible response
        message = ChatCompletionMessage(
            content=response_text,
            role="assistant",
            tool_calls=tool_calls_list
        )
        choice = ChatCompletionChoice(message=message, index=0)
        
        completion = ChatCompletion(choices=[choice])
        completion.model = model
        
        return completion
    

class Chat:
    """Mimics OpenAI's chat API"""
    def __init__(self, api_key: str, base_url: str, timeout: float = 600.0):
        self.completions = ChatCompletions(api_key, base_url, timeout)


class lightllm_Chat:
    """Mimics OpenAI's chat API for LightLLM"""
    def __init__(self, api_key: str, base_url: str, timeout: float = 600.0):
        self.completions = lightllm_ChatCompletions(api_key, base_url, timeout)


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


class LightLLMClient:
    """
    LightLLM-compatible client that uses requests instead of async libraries.
    
    This client is optimized for LightLLM API format:
    - No async/await (all synchronous)
    - Supports tools as function calling parameter
    - Returns OpenAI-compatible format with tool_calls
    
    Usage:
    client = LightLLMClient(api_key="...", base_url="...")
    response = client.chat.completions.create(model="...", messages=[...], tools=[...])
    """
    def __init__(self, api_key: str, base_url: str, timeout: float = 600.0):
        """
        Initialize the LightLLM client.
        
        Args:
            api_key: API key for authentication
            base_url: Base URL for the LightLLM API endpoint
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.chat = lightllm_Chat(api_key, base_url, timeout)


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
