"""
OpenAI-compatible middleware that uses requests instead of the openai library.
This middleware mimics the OpenAI client interface while using requests for HTTP calls.
Supports both streaming and non-streaming modes, with proper field separation for
tool_calls, content, and reasoning_content.
"""

import requests
import json
import time
import re
import base64
import logging
from typing import Dict, List, Optional, Any, Generator
import datetime
from jinja2 import Environment, FileSystemLoader


# Setup logger
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class ChatCompletionMessage:
    """Mimics OpenAI's ChatCompletionMessage structure"""
    def __init__(self, content: str, 
                 reasoning_content: Optional[str] = None,
                 role: str = "assistant", 
                 tool_calls: Optional[List[Dict]] = None):
        self.content = content
        self.reasoning_content = reasoning_content
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

class ToolCallFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments
                
class ToolCall:
    def __init__(self, id: str, type: str, function: ToolCallFunction):
        self.id = id
        self.type = type
        self.function = function



class ChatCompletions:
    """Mimics OpenAI's chat.completions API with streaming support"""
    def __init__(self, api_key: str, base_url: str, timeout: float = 600.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        logger.info(f"ChatCompletions initialized with base_url: {self.base_url}")
    
    def today_date(self):
        return datetime.date.today().strftime("%Y-%m-%d")
    
    def _parse_tool_calls_from_response(self, tool_calls_data: List[Dict]) -> Optional[List]:
        """
        Parse tool calls from API response into ToolCall objects.
        Handles various API response formats.
        """
        if not tool_calls_data:
            return None
        
        if not isinstance(tool_calls_data, list):
            logger.warning(f"tool_calls_data is not a list: {type(tool_calls_data)}")
            return None
        
        tool_calls = []
        for idx, tc in enumerate(tool_calls_data):
            if not isinstance(tc, dict):
                logger.warning(f"Tool call at index {idx} is not a dict: {type(tc)}")
                continue
            try:
                # Handle different API formats
                function_data = tc.get("function", {})
                if not isinstance(function_data, dict):
                    logger.warning(f"Function data is not a dict at index {idx}")
                    continue
                
                tool_call = ToolCall(
                    id=tc.get("id", f"call_{idx}_{int(time.time())}"),
                    type=tc.get("type", "function"),
                    function=ToolCallFunction(
                        name=function_data.get("name", ""),
                        arguments=function_data.get("arguments", "{}")
                    )
                )
                tool_calls.append(tool_call)
                logger.debug(f"Parsed tool call {idx}: {function_data.get('name', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to parse tool call at index {idx}: {tc}, error: {e}")
        
        return tool_calls if tool_calls else None
    
    def _extract_tool_calls_from_content(self, content: str) -> tuple[str, Optional[List]]:
        """
        Extract tool calls from content if they exist as <tool_call> tags.
        Returns tuple of (cleaned_content, tool_calls_list).
        """
        import re
        
        # Pattern to find tool calls in content
        toolcall_pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
        toolcalls_matches = toolcall_pattern.findall(content)
        
        if not toolcalls_matches:
            return content, None
        
        # Parse tool calls
        tool_calls_list = []
        for i, toolcall_str in enumerate(toolcalls_matches):
            try:
                toolcall_json = json.loads(toolcall_str)
                function = ToolCallFunction(
                    name=toolcall_json.get("name", ""),
                    arguments=json.dumps(toolcall_json.get("arguments", {}))
                )
                tool_call = ToolCall(
                    id=f"call_{i}_{int(time.time())}",
                    type="function",
                    function=function
                )
                tool_calls_list.append(tool_call)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse tool call from content: {toolcall_str}, error: {e}")
        
        # Remove tool call tags from content
        cleaned_content = toolcall_pattern.sub('', content).strip()
        
        return cleaned_content, (tool_calls_list if tool_calls_list else None)
    
    def _create_completion_from_data(self, model: str, content: str, 
                                     reasoning_content: Optional[str] = None,
                                     tool_calls: Optional[List] = None,
                                     index: int = 0) -> ChatCompletion:
        """
        Helper method to create ChatCompletion from parsed data.
        Reduces code duplication.
        
        Handles tool_call detection in content:
        - If tool_calls field is provided, remove <tool_call> tags from content
        - If content has <tool_call> tags but no tool_calls field, parse them
        """
        # Check if content has tool call tags
        if '<tool_call>' in content:
            if tool_calls:
                # Tool calls field exists, remove tags from content
                import re
                cleaned_content = re.sub(r"<tool_call>\s*\{.*?\}\s*</tool_call>", '', content, flags=re.DOTALL).strip()
                logger.debug(f"Removed tool_call tags from content (tool_calls field present)")
                content = cleaned_content
            else:
                # No tool_calls field, parse from content
                content, tool_calls = self._extract_tool_calls_from_content(content)
                logger.debug(f"Extracted {len(tool_calls) if tool_calls else 0} tool_calls from content")
        
        message = ChatCompletionMessage(
            reasoning_content=reasoning_content,
            content=content,
            role="assistant",
            tool_calls=tool_calls
        )
        choice = ChatCompletionChoice(message=message, index=index)
        completion = ChatCompletion(choices=[choice])
        completion.model = model
        return completion
    
    def _aggregate_stream_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Aggregate streaming response chunks into a complete response.
        Returns a dict with aggregated content, tool_calls, and reasoning_content.
        
        Handles OpenAI's Server-Sent Events (SSE) format.
        """
        logger.info("Processing streaming response")
        aggregated_content = ""
        aggregated_reasoning = None
        aggregated_tool_calls = []
        tool_call_buffer = {}  # Buffer to accumulate tool call deltas
        chunk_count = 0
        
        try:
            for line in response.iter_lines():
                if not line:
                    continue
                
                try:
                    line = line.decode('utf-8').strip()
                except UnicodeDecodeError as e:
                    logger.warning(f"Failed to decode line: {e}")
                    continue
                
                if not line.startswith('data: '):
                    # Skip non-data lines (e.g., event: message)
                    continue
                
                data_str = line[6:]  # Remove 'data: ' prefix
                if data_str == '[DONE]':
                    logger.debug("Received [DONE] signal")
                    break
                
                chunk_count += 1
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get('choices', [])
                    if not choices:
                        logger.debug(f"Chunk {chunk_count}: No choices in chunk")
                        continue
                    
                    delta = choices[0].get('delta', {})
                    if not delta:
                        logger.debug(f"Chunk {chunk_count}: Empty delta")
                        continue
                    
                    # Aggregate content
                    if 'content' in delta and delta['content']:
                        aggregated_content += delta['content']
                    
                    # Aggregate reasoning_content
                    if 'reasoning_content' in delta and delta['reasoning_content']:
                        if aggregated_reasoning is None:
                            aggregated_reasoning = ""
                        aggregated_reasoning += delta['reasoning_content']
                    
                    # Aggregate tool_calls
                    if 'tool_calls' in delta:
                        for tool_call_delta in delta['tool_calls']:
                            index = tool_call_delta.get('index', 0)
                            
                            if index not in tool_call_buffer:
                                tool_call_buffer[index] = {
                                    'id': tool_call_delta.get('id', ''),
                                    'type': tool_call_delta.get('type', 'function'),
                                    'function': {
                                        'name': '',
                                        'arguments': ''
                                    }
                                }
                            
                            if 'id' in tool_call_delta:
                                tool_call_buffer[index]['id'] = tool_call_delta['id']
                            if 'type' in tool_call_delta:
                                tool_call_buffer[index]['type'] = tool_call_delta['type']
                            
                            if 'function' in tool_call_delta:
                                func_delta = tool_call_delta['function']
                                if 'name' in func_delta:
                                    tool_call_buffer[index]['function']['name'] += func_delta['name']
                                if 'arguments' in func_delta:
                                    tool_call_buffer[index]['function']['arguments'] += func_delta['arguments']
                
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse streaming chunk: {data_str}, error: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error processing stream: {e}")
            raise
        
        # Convert tool_call_buffer to list
        if tool_call_buffer:
            aggregated_tool_calls = [tool_call_buffer[i] for i in sorted(tool_call_buffer.keys())]
        
        logger.info(f"Stream aggregation complete - chunks: {chunk_count}, content_len: {len(aggregated_content)}, "
                   f"tool_calls: {len(aggregated_tool_calls)}, has_reasoning: {aggregated_reasoning is not None}")
        
        # Validate we got some content
        if not aggregated_content and not aggregated_tool_calls:
            logger.warning("Stream aggregation resulted in empty content and no tool calls")
        
        return {
            'content': aggregated_content,
            'reasoning_content': aggregated_reasoning,
            'tool_calls': aggregated_tool_calls if aggregated_tool_calls else None
        }

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
        stream: bool = False,
        **kwargs
    ) -> ChatCompletion:
        """
        Create a chat completion using requests instead of OpenAI library.
        Supports both streaming and non-streaming modes. Always returns complete response.
        
        Args:
            model: The model to use
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            presence_penalty: Presence penalty
            logprobs: Whether to return log probabilities
            tools: Tools available for function calling
            stream: Whether to use streaming mode (response still aggregated)
            **kwargs: Additional parameters
        
        Returns:
            ChatCompletion object with complete response (aggregated if streaming)
        """
        # Validate inputs
        if not model:
            logger.error("Model parameter is required")
            raise ValueError("Model parameter cannot be empty")
        
        if not messages or not isinstance(messages, list):
            logger.error(f"Invalid messages parameter: {type(messages)}")
            raise ValueError("Messages must be a non-empty list")
        
        logger.info(f"Creating chat completion - model: {model}, stream: {stream}, "
                   f"has_tools: {tools is not None}, messages_count: {len(messages)}")
        
        # Construct the request payload in OpenAI format
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            "presence_penalty": presence_penalty,
            "stream": stream
        }
        
        if stop:
            payload["stop"] = stop
            logger.debug(f"Added stop sequences: {stop}")
        
        if logprobs:
            payload["logprobs"] = logprobs
        
        if tools:
            payload["tools"] = tools
            logger.debug(f"Added {len(tools)} tools to request")
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Make the request using requests library
        url = f"{self.base_url}/chat/completions"
        logger.debug(f"Sending request to: {url}")
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=stream
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout after {self.timeout}s: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to {url}: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {response.status_code}: {e}")
            # Try to log response body for debugging
            try:
                error_body = response.text[:500]  # First 500 chars
                logger.error(f"Error response body: {error_body}")
            except:
                pass
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
        
        # Handle streaming vs non-streaming response
        if stream:
            # Aggregate streaming response into complete response
            aggregated = self._aggregate_stream_response(response)
            
            # Convert aggregated data to ChatCompletion format
            tool_calls_obj = None
            if aggregated.get('tool_calls'):
                tool_calls_obj = self._parse_tool_calls_from_response(aggregated['tool_calls'])
            
            completion = self._create_completion_from_data(
                model=model,
                content=aggregated.get('content', ''),
                reasoning_content=aggregated.get('reasoning_content'),
                tool_calls=tool_calls_obj
            )
            
            logger.info(f"Stream response aggregated - content_len: {len(aggregated.get('content', ''))}, "
                       f"tool_calls: {len(tool_calls_obj) if tool_calls_obj else 0}")
            return completion
        else:
            # Parse non-streaming response
            response_data = response.json()
            choices_count = len(response_data.get('choices', []))
            logger.debug(f"Received non-streaming response with {choices_count} choices")
            
            if choices_count == 0:
                logger.warning("Response contains no choices")
                # Return empty completion
                return self._create_completion_from_data(model=model, content="")
            
            # Convert response to OpenAI-compatible format
            choices = []
            for choice_data in response_data.get("choices", []):
                message_data = choice_data.get("message", {})
                
                # Parse tool_calls separately from content
                tool_calls_raw = message_data.get("tool_calls")
                tool_calls_obj = None
                if tool_calls_raw:
                    tool_calls_obj = self._parse_tool_calls_from_response(tool_calls_raw)
                    logger.debug(f"Parsed {len(tool_calls_obj) if tool_calls_obj else 0} tool calls")
                
                # Create message with separated fields
                message = ChatCompletionMessage(
                    reasoning_content=message_data.get("reasoning_content"),
                    content=message_data.get("content", ""),
                    role=message_data.get("role", "assistant"),
                    tool_calls=tool_calls_obj
                )
                choice = ChatCompletionChoice(message=message, index=choice_data.get("index", 0))
                choices.append(choice)
            
            completion = ChatCompletion(choices=choices)
            completion.model = model
            logger.info(f"Chat completion created - choices: {len(choices)}, "
                       f"content_len: {len(choices[0].message.content) if choices else 0}")
            return completion

class lightllm_ChatCompletions(ChatCompletions):
    """Mimics OpenAI's chat.completions API for LightLLM with streaming support"""
    def __init__(self, api_key, base_url, timeout = 600):
        env = Environment(loader=FileSystemLoader('inference/template'))
        self.template = env.get_template('chat_template.jinja')
        super().__init__(api_key, base_url, timeout)
        logger.info(f"LightLLM ChatCompletions initialized with base_url: {self.base_url}")

    def handle_url_sync(self, url):
        """Synchronous version of handle_url for processing image URLs"""
        try:
            if url.startswith("file://"):
                with open(url[7:], "rb") as f:
                    return base64.b64encode(f.read()).decode()
            else:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                content = response.content
                return base64.b64encode(content).decode()
        except Exception as e:
            logger.error(f"Failed to handle URL {url}: {e}")
            raise
    
    def _parse_lightllm_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse LightLLM response text to extract content, reasoning, and tool calls.
        Returns dict with separated fields.
        """
        # Extract reasoning content
        reasoning_content = None
        reasoning_match = re.compile(r"<think>\n(.*?)\n</think>", re.DOTALL).search(response_text)
        if reasoning_match:
            reasoning_content = reasoning_match.group(1).strip()
            logger.debug(f"Extracted reasoning content: {len(reasoning_content)} chars")
        
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
                    function = ToolCallFunction(
                        name=toolcall_json.get("name", ""),
                        arguments=json.dumps(toolcall_json.get("arguments", {}))
                    )
                    tool_call = ToolCall(
                        id=f"call_{i}_{int(time.time())}",
                        type="function",
                        function=function
                    )
                    tool_calls_list.append(tool_call)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse tool call: {toolcall_str}, error: {e}")
            
            logger.debug(f"Parsed {len(tool_calls_list)} tool calls")
        
        return {
            'content': response_text,
            'reasoning_content': reasoning_content,
            'tool_calls': tool_calls_list
        }
    
    def _aggregate_lightllm_stream(self, response: requests.Response) -> str:
        """
        Aggregate streaming response from LightLLM into complete text.
        
        Handles various LightLLM streaming formats:
        - JSON chunks with 'token', 'text', or 'generated_text' fields
        - Plain text tokens
        - List responses
        """
        logger.info("Processing LightLLM streaming response")
        aggregated_text = ""
        chunk_count = 0
        
        try:
            for line in response.iter_lines():
                if not line:
                    continue
                
                chunk_count += 1
                try:
                    line = line.decode('utf-8').strip()
                except UnicodeDecodeError as e:
                    logger.warning(f"Failed to decode line in chunk {chunk_count}: {e}")
                    continue
                
                if not line:
                    continue
                
                # LightLLM may use different streaming format
                # Try to parse as JSON first
                try:
                    chunk = json.loads(line)
                    if isinstance(chunk, dict):
                        # Handle dict response
                        if 'token' in chunk:
                            token_text = chunk['token'].get('text', '')
                            aggregated_text += token_text
                            logger.debug(f"Chunk {chunk_count}: Added token text")
                        elif 'generated_text' in chunk:
                            # Some implementations return full text in chunks
                            aggregated_text = chunk['generated_text']
                            logger.debug(f"Chunk {chunk_count}: Got full generated_text")
                        elif 'text' in chunk:
                            aggregated_text += chunk['text']
                            logger.debug(f"Chunk {chunk_count}: Added text")
                        else:
                            logger.debug(f"Chunk {chunk_count}: Unrecognized dict format: {list(chunk.keys())}")
                    elif isinstance(chunk, list) and len(chunk) > 0:
                        # Handle list response
                        if 'generated_text' in chunk[0]:
                            aggregated_text = chunk[0]['generated_text']
                            logger.debug(f"Chunk {chunk_count}: Got generated_text from list")
                except json.JSONDecodeError:
                    # Not JSON, might be plain text tokens
                    aggregated_text += line
                    logger.debug(f"Chunk {chunk_count}: Added plain text")
        
        except Exception as e:
            logger.error(f"Error processing LightLLM stream at chunk {chunk_count}: {e}")
            raise
        
        logger.info(f"LightLLM stream aggregation complete - chunks: {chunk_count}, text_len: {len(aggregated_text)}")
        
        if not aggregated_text:
            logger.warning("LightLLM stream aggregation resulted in empty text")
        
        return aggregated_text

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
                    stream = False,
                    **kwargs):
        """
        Create a chat completion using LightLLM API format.
        Supports both streaming and non-streaming modes.
        
        This implementation:
        - Does not use async/await (all synchronous)
        - Supports tools parameter for function calling
        - Parses tool_call responses from the model
        - Returns OpenAI-compatible format with separated fields
        - Always returns complete response (aggregates if streaming)
        """
        # Validate inputs
        if not model:
            logger.error("Model parameter is required")
            raise ValueError("Model parameter cannot be empty")
        
        if not messages or not isinstance(messages, list):
            logger.error(f"Invalid messages parameter: {type(messages)}")
            raise ValueError("Messages must be a non-empty list")
        
        logger.info(f"LightLLM create - model: {model}, stream: {stream}, "
                   f"has_tools: {tools is not None}, messages_count: {len(messages)}")
        
        # 使用jinja模板组织输入
        try:
            query = self.template.render(
                messages=messages,
                tools=tools if tools else [],
                enable_thinking=False,
                today_date=self.today_date()
            )
            logger.debug(f"Constructed query with template - query_len: {len(query)}")
        except Exception as e:
            logger.error(f"Failed to render template: {e}")
            raise ValueError(f"Template rendering failed: {e}")
        
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
            "stream": stream
        }

        # Make synchronous HTTP request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=stream
            )
            response.raise_for_status()
        except requests.exceptions.Timeout as e:
            logger.error(f"LightLLM request timeout after {self.timeout}s: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"LightLLM connection error to {self.base_url}: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"LightLLM HTTP error {response.status_code}: {e}")
            # Try to log response body for debugging
            try:
                error_body = response.text[:500]
                logger.error(f"Error response body: {error_body}")
            except:
                pass
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"LightLLM request failed: {e}")
            raise
        
        # Handle streaming vs non-streaming
        if stream:
            # Aggregate streaming response
            response_text = self._aggregate_lightllm_stream(response)
        else:
            # Parse non-streaming response
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LightLLM response as JSON: {e}")
                logger.error(f"Response text: {response.text[:500]}")
                raise ValueError(f"Invalid JSON response from LightLLM: {e}")
            
            logger.debug(f"Received LightLLM response: {type(response_data)}")
            
            # Parse the generated text with error handling
            try:
                if isinstance(response_data, list):
                    if not response_data:
                        raise ValueError("Empty response list from LightLLM")
                    generated = response_data[0].get("generated_text", [""])
                    response_text = generated[0] if isinstance(generated, list) else generated
                else:
                    generated = response_data.get("generated_text", [""])
                    response_text = generated[0] if isinstance(generated, list) else generated
                
                if not response_text:
                    logger.warning("LightLLM returned empty generated_text")
                    response_text = ""
            except (KeyError, IndexError, TypeError) as e:
                logger.error(f"Failed to extract generated_text from response: {e}")
                logger.error(f"Response structure: {response_data}")
                raise ValueError(f"Unexpected LightLLM response format: {e}")
        
        # Parse response to extract separated fields
        parsed = self._parse_lightllm_response(response_text)
        
        # Create OpenAI-compatible response with separated fields using helper
        completion = self._create_completion_from_data(
            model=model,
            content=parsed['content'],
            reasoning_content=parsed['reasoning_content'],
            tool_calls=parsed['tool_calls']
        )
        
        logger.info(f"LightLLM completion created - content_len: {len(parsed['content'])}, "
                   f"has_reasoning: {parsed['reasoning_content'] is not None}, "
                   f"has_tool_calls: {parsed['tool_calls'] is not None}")
        
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
