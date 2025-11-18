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
    def handle_url(self, url):
        if url.startswith("file://"):
            with open(url[7:], "rb") as f:
                return base64.b64encode(f.read()).decode()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    content = await response.read()
                    return base64.b64encode(content).decode()
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

    def create(self, model, 
                    messages, 
                    temperature = 0.6, 
                    top_p = 0.95, 
                    max_tokens = 10000, 
                    stop = None, 
                    presence_penalty = 1.1, 
                    logprobs = False, 
                    tools = None, **kwargs):
        if tools:
            tools_str = []
            for tool in tools:
                tools_str.append(json.dumps(tool,ensure_ascii=False))
            tool_define = "\n".join(tools_str)
            tool_sysprompt = "\n\n# Tools\n\nYou may call one or more functions to assist with the user query.\n\nYou are provided with function signatures within <tools></tools> XML tags:\n<tools>\n<<<tool_define>>>\n</tools>\n\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\n<tool_call>\n{\"name\": <function-name>, \"arguments\": <args-json-object>}\n</tool_call>"
            tool_sysprompt = tool_sysprompt.replace("<<<tool_define>>>", tool_define)
        else:
            tool_sysprompt = ""
        
        query = ""
        if messages[0]["role"] == "system":
            if messages[0]["content"] != "":
                query += "<|im_start|>system\n" + messages[0]["content"] + tool_sysprompt + "<|im_end|>\n"
            messages = messages[1:]
        elif tools:
            query += "<|im_start|>system\n" + tool_sysprompt + "<|im_end|>\n"
        else:
            query += ""

        images = []

        for message in messages:
            if message["role"] == "user":
                query += self.USER_START
                if isinstance(message["content"], list):
                    query_content = ""
                    img_cnt = 0
                    tasks = []
                    for content in message["content"]:
                        if content["type"] == "image_url":
                            query += self.IMG_TAG
                            img_cnt += 1
                            tasks.append(self.handle_url(content["image_url"]))
                        elif content["type"] == "text":
                            query_content = content["text"]
                        else:
                            raise ValueError("type must be text, image_url")
                    image_data = await asyncio.gather(*tasks)
                    for data in image_data:
                        images.append({"type": "base64", "data": data})
                    if img_cnt >= 2:
                        query += f"用户本轮上传了{img_cnt}张图\n"
                    query += query_content + self.IM_END
                else:
                    if isinstance(message["content"], dict):
                        logger.error(f"message content has found being dict: {message["content"]}")
                    query += str(message["content"]) + self.IM_END
            elif message["role"] == "assistant":
                query += self.ASSISTANT_START
                query += message["content"] + self.IM_END
            elif message["role"] == "tool":
                query += self.USER_START
                query_content = f"<tool_response>\n{message["content"]}\n</tool_response>"
                query += query_content + self.IM_END
            else:
                raise ValueError("role must be user or assistant")
        query += self.ASSISTANT_START

        # print(query)
        # print("=" * 50)

        play_load = {
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

        multimodal_params = {}
        if images:
            multimodal_params["images"] = images
        if multimodal_params:
            play_load["multimodal_params"] = multimodal_params

        headers = {"Content-Type": "application/json"}
        timeout = aiohttp.ClientTimeout(total=30*60)  # 单位是秒，超时时间30 分钟
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, data=json.dumps(play_load)) as response:
                response.raise_for_status()
                # aiohttp 在尝试解析 JSON 时，会检查响应的 Content-Type 头是否为 application/json。如果 Content-Type 不是 application/json，即使内容是有效的 JSON，aiohttp 也会抛出错误
                response_data = await response.json(content_type=None) 

        if isinstance(response_data, list):
            response_text = response_data[0]["generated_text"][0]
        else:
            response_text = response_data["generated_text"][0]
        
        # 解析 Toolcall
        toolcall_pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
        toolcalls = toolcall_pattern.findall(response_text)


        
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
    
        return
    

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
