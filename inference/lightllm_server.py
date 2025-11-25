#!/usr/bin/env python3
"""
LightLLM Middleware Server - Standalone OpenAI-compatible API proxy for LightLLM.

This server provides an OpenAI v1 compatible API that proxies requests to a LightLLM
generate endpoint. It supports:
- OpenAI v1 `/v1/chat/completions` endpoint
- Streaming responses (Server-Sent Events)
- `enable_thinking` parameter for chain-of-thought reasoning
- Configurable Jinja2 template files
- Tools/function calling input
- Standard OpenAI output format with reasoning_content, content, and tool_calls

Usage:
    python lightllm_server.py --port 8000 --lightllm-url http://localhost:8080/generate
    python lightllm_server.py --template-dir ./templates --template-name custom_template.jinja
"""

import argparse
import datetime
import json
import logging
import os
import re
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for OpenAI API compatibility
# ============================================================================

class FunctionCall(BaseModel):
    """Function call in a tool call"""
    name: str
    arguments: str


class ToolCall(BaseModel):
    """Tool call in assistant message"""
    id: str
    type: str = "function"
    function: FunctionCall


class Message(BaseModel):
    """Chat message"""
    role: str
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


class Function(BaseModel):
    """Function definition in a tool"""
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class Tool(BaseModel):
    """Tool definition"""
    type: str = "function"
    function: Function


class ChatCompletionRequest(BaseModel):
    """OpenAI chat completion request"""
    model: str
    messages: List[Dict[str, Any]]
    temperature: float = 0.6
    top_p: float = 0.95
    max_tokens: int = 4096
    stream: bool = False
    stop: Optional[List[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    # LightLLM specific parameters
    enable_thinking: bool = False
    top_k: int = 50
    repetition_penalty: float = 1.0


class Choice(BaseModel):
    """Choice in chat completion response"""
    index: int = 0
    message: Message
    finish_reason: str = "stop"


class Usage(BaseModel):
    """Token usage information"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI chat completion response"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage = Field(default_factory=Usage)


class DeltaMessage(BaseModel):
    """Delta message for streaming"""
    role: Optional[str] = None
    content: Optional[str] = None
    reasoning_content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class StreamChoice(BaseModel):
    """Choice in streaming response"""
    index: int = 0
    delta: DeltaMessage
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """Streaming chunk response"""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[StreamChoice]


# ============================================================================
# LightLLM Proxy Server
# ============================================================================

class LightLLMProxy:
    """
    Proxy server that converts OpenAI API requests to LightLLM generate format.
    """
    
    def __init__(
        self,
        lightllm_url: str,
        template_dir: str,
        template_name: str,
        timeout: float = 600.0,
        api_key: Optional[str] = None
    ):
        """
        Initialize the LightLLM proxy.
        
        Args:
            lightllm_url: URL of the LightLLM generate endpoint
            template_dir: Directory containing Jinja2 templates
            template_name: Name of the template file to use
            timeout: Request timeout in seconds
            api_key: Optional API key for LightLLM backend
        """
        self.lightllm_url = lightllm_url
        self.timeout = timeout
        self.api_key = api_key or ""
        
        # Setup Jinja2 template
        self.template_dir = template_dir
        self.template_name = template_name
        self._load_template()
        
        logger.info(f"LightLLM Proxy initialized - URL: {lightllm_url}, Template: {template_dir}/{template_name}")
    
    def _load_template(self):
        """Load the Jinja2 template for chat formatting."""
        try:
            env = Environment(loader=FileSystemLoader(self.template_dir))
            self.template = env.get_template(self.template_name)
            logger.info(f"Loaded template: {self.template_name}")
        except Exception as e:
            logger.error(f"Failed to load template: {e}")
            raise ValueError(f"Failed to load template from {self.template_dir}/{self.template_name}: {e}")
    
    def reload_template(self, template_dir: Optional[str] = None, template_name: Optional[str] = None):
        """Reload the template (useful for runtime configuration changes)."""
        if template_dir:
            self.template_dir = template_dir
        if template_name:
            self.template_name = template_name
        self._load_template()
    
    @staticmethod
    def today_date() -> str:
        """Get today's date in YYYY-MM-DD format."""
        return datetime.date.today().strftime("%Y-%m-%d")
    
    @staticmethod
    def generate_completion_id() -> str:
        """Generate a unique completion ID."""
        return f"chatcmpl-{uuid.uuid4().hex[:24]}"
    
    @staticmethod
    def generate_tool_call_id(index: int = 0) -> str:
        """Generate a unique tool call ID."""
        return f"call_{uuid.uuid4().hex[:24]}"
    
    def _render_prompt(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        enable_thinking: bool = False
    ) -> str:
        """
        Render messages and tools into a prompt string using the Jinja2 template.
        
        Args:
            messages: List of chat messages
            tools: Optional list of tool definitions
            enable_thinking: Whether to enable chain-of-thought reasoning
            
        Returns:
            Rendered prompt string
        """
        try:
            prompt = self.template.render(
                messages=messages,
                tools=tools or [],
                enable_thinking=enable_thinking,
                today_date=self.today_date(),
                add_generation_prompt=True
            )
            logger.debug(f"Rendered prompt length: {len(prompt)}")
            return prompt
        except Exception as e:
            logger.error(f"Failed to render prompt: {e}")
            raise ValueError(f"Template rendering failed: {e}")
    
    def _parse_response(
        self,
        response_text: str,
        tool_call_id_mapping: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Parse LightLLM response text to extract content, reasoning, and tool calls.
        
        Args:
            response_text: Raw response text from LightLLM
            tool_call_id_mapping: Optional mapping of tool names to IDs for consistency
            
        Returns:
            Dict with 'content', 'reasoning_content', and 'tool_calls'
        """
        content = response_text
        reasoning_content = None
        tool_calls = None
        
        # Extract reasoning content from <think> tags
        thinking_pattern = re.compile(r"<think>\n?(.*?)\n?</think>", re.DOTALL)
        thinking_match = thinking_pattern.search(response_text)
        if thinking_match:
            reasoning_content = thinking_match.group(1).strip()
            # Remove the thinking block from content
            content = thinking_pattern.sub('', content).strip()
            logger.debug(f"Extracted reasoning content: {len(reasoning_content)} chars")
        
        # Extract tool calls from <tool_call> tags
        toolcall_pattern = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
        toolcall_matches = toolcall_pattern.findall(response_text)
        
        if toolcall_matches:
            tool_calls = []
            for i, toolcall_str in enumerate(toolcall_matches):
                try:
                    toolcall_json = json.loads(toolcall_str)
                    tool_name = toolcall_json.get("name", "")
                    
                    # Generate or reuse tool call ID
                    if tool_call_id_mapping and tool_name in tool_call_id_mapping:
                        tool_id = tool_call_id_mapping[tool_name]
                    else:
                        tool_id = self.generate_tool_call_id(i)
                        if tool_call_id_mapping is not None:
                            tool_call_id_mapping[tool_name] = tool_id
                    
                    # Format arguments as JSON string
                    arguments = toolcall_json.get("arguments", {})
                    if isinstance(arguments, dict):
                        arguments_str = json.dumps(arguments)
                    else:
                        arguments_str = str(arguments)
                    
                    tool_call = ToolCall(
                        id=tool_id,
                        type="function",
                        function=FunctionCall(
                            name=tool_name,
                            arguments=arguments_str
                        )
                    )
                    tool_calls.append(tool_call)
                    logger.debug(f"Parsed tool call: {tool_name}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse tool call JSON: {toolcall_str}, error: {e}")
            
            # Remove tool call tags from content
            content = toolcall_pattern.sub('', content).strip()
        
        return {
            'content': content if content else None,
            'reasoning_content': reasoning_content,
            'tool_calls': tool_calls
        }
    
    def _build_lightllm_payload(
        self,
        prompt: str,
        request: ChatCompletionRequest,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Build the payload for LightLLM generate endpoint.
        
        Args:
            prompt: Rendered prompt string
            request: Original chat completion request
            stream: Whether to stream the response
            
        Returns:
            Dict payload for LightLLM API
        """
        stop_sequences = ["<|im_end|>"]
        if request.stop:
            stop_sequences.extend(request.stop)
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": request.temperature,
                "top_k": request.top_k,
                "top_p": request.top_p,
                "repetition_penalty": request.repetition_penalty,
                "max_new_tokens": request.max_tokens,
                "do_sample": True,
                "stop_sequences": stop_sequences
            },
            "stream": stream
        }
        
        return payload
    
    def create_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """
        Create a non-streaming chat completion.
        
        Args:
            request: Chat completion request
            
        Returns:
            ChatCompletionResponse with the generated content
        """
        logger.info(f"Creating completion - model: {request.model}, messages: {len(request.messages)}")
        
        # Render the prompt
        prompt = self._render_prompt(
            messages=request.messages,
            tools=request.tools,
            enable_thinking=request.enable_thinking
        )
        
        # Build payload
        payload = self._build_lightllm_payload(prompt, request, stream=False)
        
        # Make request to LightLLM
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            response = requests.post(
                self.lightllm_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"LightLLM request failed: {e}")
            raise HTTPException(status_code=502, detail=f"Backend error: {str(e)}")
        
        # Parse response
        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LightLLM response: {e}")
            raise HTTPException(status_code=502, detail=f"Invalid JSON from backend: {str(e)}")
        
        # Extract generated text
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
                response_text = ""
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Failed to extract generated_text: {e}, response: {response_data}")
            raise HTTPException(status_code=502, detail=f"Unexpected response format: {str(e)}")
        
        # Parse response to extract fields
        parsed = self._parse_response(response_text)
        
        # Build OpenAI-compatible response
        completion_id = self.generate_completion_id()
        created_time = int(time.time())
        
        message = Message(
            role="assistant",
            content=parsed['content'],
            reasoning_content=parsed['reasoning_content'],
            tool_calls=parsed['tool_calls']
        )
        
        return ChatCompletionResponse(
            id=completion_id,
            created=created_time,
            model=request.model,
            choices=[Choice(index=0, message=message, finish_reason="stop")]
        )
    
    async def create_streaming_completion(
        self,
        request: ChatCompletionRequest
    ) -> AsyncGenerator[str, None]:
        """
        Create a streaming chat completion.
        
        Args:
            request: Chat completion request
            
        Yields:
            Server-Sent Events formatted strings
        """
        logger.info(f"Creating streaming completion - model: {request.model}")
        
        # Render the prompt
        prompt = self._render_prompt(
            messages=request.messages,
            tools=request.tools,
            enable_thinking=request.enable_thinking
        )
        
        # Build payload
        payload = self._build_lightllm_payload(prompt, request, stream=True)
        
        # Make streaming request to LightLLM
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        completion_id = self.generate_completion_id()
        created_time = int(time.time())
        
        # Accumulate full response for parsing
        accumulated_text = ""
        sent_role = False
        tool_call_id_mapping: Dict[str, str] = {}
        
        try:
            response = requests.post(
                self.lightllm_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Send initial chunk with role
            initial_chunk = ChatCompletionChunk(
                id=completion_id,
                created=created_time,
                model=request.model,
                choices=[StreamChoice(
                    index=0,
                    delta=DeltaMessage(role="assistant"),
                    finish_reason=None
                )]
            )
            yield f"data: {initial_chunk.model_dump_json()}\n\n"
            sent_role = True
            
            # Process streaming response
            for line in response.iter_lines():
                if not line:
                    continue
                
                try:
                    line_text = line.decode('utf-8').strip()
                except UnicodeDecodeError:
                    continue
                
                if not line_text:
                    continue
                
                # Parse LightLLM streaming format
                token_text = ""
                try:
                    chunk_data = json.loads(line_text)
                    if isinstance(chunk_data, dict):
                        if 'token' in chunk_data:
                            token_obj = chunk_data['token']
                            if isinstance(token_obj, dict):
                                token_text = token_obj.get('text', '')
                            else:
                                token_text = str(token_obj)
                        elif 'generated_text' in chunk_data:
                            # Final chunk with full text
                            token_text = chunk_data['generated_text']
                            if isinstance(token_text, list):
                                token_text = token_text[0] if token_text else ""
                        elif 'text' in chunk_data:
                            token_text = chunk_data['text']
                    elif isinstance(chunk_data, list) and chunk_data:
                        if 'generated_text' in chunk_data[0]:
                            token_text = chunk_data[0]['generated_text']
                            if isinstance(token_text, list):
                                token_text = token_text[0] if token_text else ""
                except json.JSONDecodeError:
                    # Not JSON, treat as plain text token
                    token_text = line_text
                
                if token_text:
                    accumulated_text += token_text
                    
                    # For streaming, we send content as-is during generation
                    # Tool calls and reasoning will be parsed at the end
                    chunk = ChatCompletionChunk(
                        id=completion_id,
                        created=created_time,
                        model=request.model,
                        choices=[StreamChoice(
                            index=0,
                            delta=DeltaMessage(content=token_text),
                            finish_reason=None
                        )]
                    )
                    yield f"data: {chunk.model_dump_json()}\n\n"
            
            # Send final chunk with finish_reason
            final_chunk = ChatCompletionChunk(
                id=completion_id,
                created=created_time,
                model=request.model,
                choices=[StreamChoice(
                    index=0,
                    delta=DeltaMessage(),
                    finish_reason="stop"
                )]
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Streaming request failed: {e}")
            error_chunk = {
                "error": {
                    "message": str(e),
                    "type": "backend_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"


# ============================================================================
# FastAPI Application
# ============================================================================

# Global proxy instance
proxy: Optional[LightLLMProxy] = None


def create_app(
    lightllm_url: str,
    template_dir: str,
    template_name: str,
    api_key: Optional[str] = None,
    timeout: float = 600.0
) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        lightllm_url: URL of the LightLLM generate endpoint
        template_dir: Directory containing Jinja2 templates
        template_name: Name of the template file
        api_key: Optional API key for LightLLM backend
        timeout: Request timeout
        
    Returns:
        Configured FastAPI application
    """
    global proxy
    
    app = FastAPI(
        title="LightLLM Middleware Server",
        description="OpenAI-compatible API proxy for LightLLM",
        version="1.0.0"
    )
    
    # Initialize proxy
    proxy = LightLLMProxy(
        lightllm_url=lightllm_url,
        template_dir=template_dir,
        template_name=template_name,
        timeout=timeout,
        api_key=api_key
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    @app.get("/v1/models")
    async def list_models():
        """List available models (mock endpoint)."""
        return {
            "object": "list",
            "data": [
                {
                    "id": "lightllm-model",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "lightllm"
                }
            ]
        }
    
    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        """
        Create a chat completion.
        
        This endpoint accepts OpenAI v1 format requests and proxies them to LightLLM.
        """
        if proxy is None:
            raise HTTPException(status_code=500, detail="Proxy not initialized")
        
        logger.info(f"Received chat completion request - model: {request.model}, stream: {request.stream}")
        
        if request.stream:
            return StreamingResponse(
                proxy.create_streaming_completion(request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            response = proxy.create_completion(request)
            return JSONResponse(content=response.model_dump())
    
    @app.post("/chat/completions")
    async def chat_completions_no_v1(request: ChatCompletionRequest):
        """Alias for /v1/chat/completions without the v1 prefix."""
        return await chat_completions(request)
    
    @app.post("/v1/config/template")
    async def update_template(request: Request):
        """
        Update the template configuration at runtime.
        
        Body:
            {
                "template_dir": "path/to/templates",  // optional
                "template_name": "template.jinja"      // optional
            }
        """
        if proxy is None:
            raise HTTPException(status_code=500, detail="Proxy not initialized")
        
        try:
            body = await request.json()
            proxy.reload_template(
                template_dir=body.get("template_dir"),
                template_name=body.get("template_name")
            )
            return {"status": "ok", "message": "Template reloaded"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    return app


def main():
    """Main entry point for the server."""
    parser = argparse.ArgumentParser(
        description="LightLLM Middleware Server - OpenAI-compatible API proxy for LightLLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lightllm_server.py --port 8000 --lightllm-url http://localhost:8080/generate
  python lightllm_server.py --template-dir ./templates --template-name custom.jinja
  python lightllm_server.py --host 0.0.0.0 --port 9000 --timeout 300
        """
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)"
    )
    
    parser.add_argument(
        "--lightllm-url",
        type=str,
        default="http://localhost:8080/generate",
        help="URL of the LightLLM generate endpoint (default: http://localhost:8080/generate)"
    )
    
    parser.add_argument(
        "--template-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "template"),
        help="Directory containing Jinja2 templates (default: ./template)"
    )
    
    parser.add_argument(
        "--template-name",
        type=str,
        default="chat_template.jinja",
        help="Name of the template file to use (default: chat_template.jinja)"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("LIGHTLLM_API_KEY", ""),
        help="API key for LightLLM backend (default: from LIGHTLLM_API_KEY env var)"
    )
    
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="Request timeout in seconds (default: 600)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info(f"Starting LightLLM Middleware Server")
    logger.info(f"  Host: {args.host}")
    logger.info(f"  Port: {args.port}")
    logger.info(f"  LightLLM URL: {args.lightllm_url}")
    logger.info(f"  Template: {args.template_dir}/{args.template_name}")
    
    # Create and run the app
    app = create_app(
        lightllm_url=args.lightllm_url,
        template_dir=args.template_dir,
        template_name=args.template_name,
        api_key=args.api_key,
        timeout=args.timeout
    )
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
