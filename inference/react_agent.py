import json
import json5
import os
from typing import Dict, Iterator, List, Literal, Optional, Tuple, Union
from qwen_agent.llm.schema import Message
from transformers import AutoTokenizer 
from qwen_agent.agents.fncall_agent import FnCallAgent
from qwen_agent.llm import BaseChatModel
from qwen_agent.llm.schema import ASSISTANT, DEFAULT_SYSTEM_MESSAGE, Message
from qwen_agent.settings import MAX_LLM_CALL_PER_RUN
from qwen_agent.tools import BaseTool
from prompt import *
import time
import asyncio

# Import middleware or OpenAI based on configuration
USE_MIDDLEWARE = os.getenv('USE_OPENAI_MIDDLEWARE', 'false').lower() == 'true'
if USE_MIDDLEWARE:
    from openai_middleware import OpenAICompatibleClient as OpenAI_requests
    from openai_middleware import LightLLMClient as OpenAI_LightLLM
    from openai_middleware import APIError, APIConnectionError, APITimeoutError
else:
    pass
    # from openai import OpenAI, APIError, APIConnectionError, APITimeoutError

from tool_file import *
from tool_scholar import *
from tool_python import *
from tool_search import *
from tool_visit import *

OBS_START = '<tool_response>'
OBS_END = '\n</tool_response>'

MAX_LLM_CALL_PER_RUN = int(os.getenv('MAX_LLM_CALL_PER_RUN', 100))
OMIT_TOOL_RESPONSE_ROUNDS = int(os.getenv('OMIT_TOOL_RESPONSE_ROUNDS', 0))

# Map tool names to their classes
ALL_TOOLS = {
    'parse_file': FileParser(),
    'google_scholar': Scholar(),
    'visit': Visit(),
    'search': Search(),
    'PythonInterpreter': PythonInterpreter(),
}

def get_enabled_tools():
    """Get the list of enabled tools from environment variable."""
    enabled_tools_env = os.getenv('ENABLED_TOOLS', 'search,visit,google_scholar,PythonInterpreter,parse_file')
    enabled_tools = [tool.strip() for tool in enabled_tools_env.split(',')]
    return enabled_tools

def initialize_tools(enabled_tools=None):
    """Initialize tools based on enabled_tools list."""
    if enabled_tools is None:
        enabled_tools = get_enabled_tools()
    
    tool_classes = []
    for tool_name in enabled_tools:
        if tool_name in ALL_TOOLS:
            tool_classes.append(ALL_TOOLS[tool_name])
        else:
            print(f"Warning: Tool '{tool_name}' not found in available tools")
    
    return {tool.name: tool for tool in tool_classes}

# Initialize tools based on environment configuration
TOOL_MAP = initialize_tools()

import random


class MultiTurnReactAgent(FnCallAgent):
    def __init__(self,
                 function_list: Optional[List[Union[str, Dict, BaseTool]]] = None,
                 llm: Optional[Union[Dict, BaseChatModel]] = None,
                 **kwargs):

        self.llm_generate_cfg = llm["generate_cfg"]
        self.llm_local_path = llm["model_path"]
        
        # Support for remote API configuration
        self.use_remote_api = os.getenv('USE_REMOTE_API', 'false').lower() == 'true'
        self.inference_api_base = os.getenv('INFERENCE_API_BASE', 'http://127.0.0.1:6001/v1')
        self.inference_api_key = os.getenv('INFERENCE_API_KEY', 'EMPTY')
        
        # Get enabled tools for generating appropriate system prompt
        self.enabled_tools = get_enabled_tools()
        
        print(f"Agent initialized with USE_REMOTE_API={self.use_remote_api}")
        if self.use_remote_api:
            print(f"Using remote API at: {self.inference_api_base}")
        print(f"Enabled tools: {', '.join(self.enabled_tools)}")

    def sanity_check_output(self, content):
        return "<think>" in content and "</think>" in content
    
    def get_tools_for_api(self):
        """Get tools in OpenAI API format"""
        from prompt import TOOL_DEFINITIONS
        tools = []
        for tool_name in self.enabled_tools:
            if tool_name in TOOL_DEFINITIONS:
                try:
                    tool_def = json.loads(TOOL_DEFINITIONS[tool_name])
                    tools.append(tool_def)
                except json.JSONDecodeError:
                    print(f"Warning: Failed to parse tool definition for {tool_name}")
        return tools if tools else None
    
    def call_server(self, msgs, planning_port, max_tries=10):
        """
        Call the OpenAI-compatible server following standard format.
        Handles retries and error reporting.
        
        Args:
            msgs: List of message dicts with 'role', 'content', and optionally 
                  'reasoning_content' and 'tool_calls' fields
            planning_port: Port number for local server
            max_tries: Maximum number of retry attempts
        
        Returns:
            Tuple of (content, reasoning_content, tool_calls) - all three fields from response
        """
        # Use remote API configuration if enabled, otherwise use local server
        if self.use_remote_api:
            openai_api_key = self.inference_api_key
            openai_api_base = self.inference_api_base
        else:
            openai_api_key = "EMPTY"
            openai_api_base = f"http://127.0.0.1:{planning_port}/v1"

        if self.use_remote_api and "generate" in openai_api_base:
            client = OpenAI_LightLLM(
                api_key=openai_api_key,
                base_url=openai_api_base,
                timeout=6000.0
            )
        else:
            client = OpenAI_requests(
                    api_key=openai_api_key,
                    base_url=openai_api_base,
                    timeout=6000.0,
            )
        
        tools = self.get_tools_for_api()
        base_sleep_time = 1 
        
        for attempt in range(max_tries):
            try:
                if attempt != 0:
                    print(f"--- Attempting to call the service, try {attempt + 1}/{max_tries} ---")
                
                # Standard OpenAI API call
                chat_response = client.chat.completions.create(
                    model=self.model,
                    messages=msgs,
                    stop=["\n<tool_response>", "<tool_response>"],
                    temperature=self.llm_generate_cfg.get('temperature', 0.6),
                    top_p=self.llm_generate_cfg.get('top_p', 0.95),
                    logprobs=False,
                    max_tokens=10000,
                    presence_penalty=self.llm_generate_cfg.get('presence_penalty', 1.1),
                    tools=tools,
                    stream=self.llm_generate_cfg.get('stream', False)
                )

                # Extract all three fields from response
                content = chat_response.choices[0].message.content or ""
                reasoning_content = getattr(chat_response.choices[0].message, 'reasoning_content', None)
                tool_calls = getattr(chat_response.choices[0].message, 'tool_calls', None)
                
                # Log received fields for debugging
                print(f"--- Response received - content_len: {len(content)}, "
                      f"has_reasoning: {reasoning_content is not None}, "
                      f"has_tool_calls: {tool_calls is not None}")
                
                if (content and content.strip()) or reasoning_content is not None or tool_calls is not None:
                    print("--- Service call successful, received a valid response ---")
                    # Return all three fields
                    return content.strip(), reasoning_content, tool_calls
                else:
                    print(f"Warning: Attempt {attempt + 1} received an empty response.")

            except (APIError, APIConnectionError, APITimeoutError) as e:
                print(f"Error: Attempt {attempt + 1} failed with an API or network error: {e}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Error: Attempt {attempt + 1} failed with an unexpected error: {e}")

            if attempt < max_tries - 1:
                sleep_time = base_sleep_time * (2 ** attempt) + random.uniform(0, 1)
                sleep_time = min(sleep_time, 30) 
                
                print(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                print("Error: All retry attempts have been exhausted. The call has failed.")
        
        # Return error in all three fields
        return "main model server error!!!", None, None

    def count_tokens(self, messages):
        tokenizer = AutoTokenizer.from_pretrained(self.llm_local_path) 
        full_prompt = tokenizer.apply_chat_template(messages, tokenize=False)
        tokens = tokenizer(full_prompt, return_tensors="pt")
        token_count = len(tokens["input_ids"][0])
        
        return token_count
    
    def omit_old_tool_responses(self, messages: List[dict], keep_rounds: int) -> List[dict]:
        """
        Replace tool response content in messages older than K rounds with a placeholder.
        
        Args:
            messages: List of message dictionaries
            keep_rounds: Number of recent rounds to keep full tool responses for
        
        Returns:
            Modified list of messages with old tool responses omitted
        """
        if keep_rounds <= 0:
            return messages
        
        # Create a deep copy to avoid modifying the original
        messages_copy = []
        for msg in messages:
            messages_copy.append(msg.copy())
        
        # Find all tool response messages (role="tool" or role="user" with tool_response tags)
        tool_response_indices = []
        for i, msg in enumerate(messages_copy):
            if msg.get("role") == "tool":
                tool_response_indices.append(i)
            elif msg.get("role") == "user" and OBS_START in msg.get("content", ""):
                tool_response_indices.append(i)
        
        # Calculate how many tool responses to omit (all except the last keep_rounds)
        num_to_omit = max(0, len(tool_response_indices) - keep_rounds)
        
        # Replace content of old tool responses
        for i in range(num_to_omit):
            idx = tool_response_indices[i]
            msg = messages_copy[idx]
            
            if msg.get("role") == "tool":
                # For role="tool" messages, replace the content
                messages_copy[idx]["content"] = "<tool_response>\ntool response omitted\n</tool_response>"
            elif msg.get("role") == "user":
                # For role="user" with tool_response tags, replace the content
                messages_copy[idx]["content"] = "<tool_response>\ntool response omitted\n</tool_response>"
        
        return messages_copy

    def _run(self, data: str, model: str, **kwargs) -> List[List[Message]]:
        self.model=model
        try:
            question = data['item']['question']
        except: 
            raw_msg = data['item']['messages'][1]["content"] 
            question = raw_msg.split("User:")[1].strip() if "User:" in raw_msg else raw_msg 

        start_time = time.time()
        planning_port = data['planning_port']
        answer = data['item']['answer']
        self.user_prompt = question
        # Use dynamic system prompt based on enabled tools
        system_prompt = get_system_prompt(self.enabled_tools)
        
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": question}]
        num_llm_calls_available = MAX_LLM_CALL_PER_RUN
        round = 0
        
        # Track used tools during the run
        used_tools = set()
        
        while num_llm_calls_available > 0:
            # Check whether time is reached
            if time.time() - start_time > 150 * 60:  # 150 minutes in seconds
                prediction = 'No answer found after 2h30mins'
                termination = 'No answer found after 2h30mins'
                result = {
                    "question": question,
                    "answer": answer,
                    "messages": messages,
                    "prediction": prediction,
                    "termination": termination,
                    "tools": self._get_tools_dict(used_tools)
                }
                return result
            round += 1
            num_llm_calls_available -= 1
            
            # Apply tool response omission if configured
            messages_to_send = messages
            if OMIT_TOOL_RESPONSE_ROUNDS > 0:
                messages_to_send = self.omit_old_tool_responses(messages, OMIT_TOOL_RESPONSE_ROUNDS)
            
            # Call server and get all three fields
            content, reasoning_content, tool_calls_obj = self.call_server(messages_to_send, planning_port)
            
            if '<tool_response>' in content:
                pos = content.find('<tool_response>')
                content = content[:pos]

            # Build message with all separated fields for proper preservation
            message_cur = {"role": "assistant", "content": content.strip()}
            
            # Add reasoning_content as separate field if present
            if reasoning_content:
                message_cur["reasoning_content"] = reasoning_content.strip()
            
            # Add tool_calls as separate field if present (for preservation in message history)
            if tool_calls_obj:
                # Convert tool_calls objects to dict format for message storage
                message_cur["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in tool_calls_obj
                ]
            
            messages.append(message_cur)
            
            # Execute tool calls if present
            if tool_calls_obj and len(tool_calls_obj) > 0:
                # Process each tool call and append results with proper tool_call_id
                for tool_call in tool_calls_obj:
                    # Extract metadata first to ensure they're always available
                    tool_call_id = tool_call.id
                    tool_name = tool_call.function.name
                    tool_args_str = tool_call.function.arguments
                    
                    try:
                        # Parse arguments
                        try:
                            tool_args = json.loads(tool_args_str) if tool_args_str else {}
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        # Handle Python interpreter specially
                        if "python" in tool_name.lower():
                            try:
                                # For Python, arguments might contain code
                                code_raw = tool_args.get('code', '')
                                if not code_raw and '<code>' in content:
                                    # Fallback: extract from content if not in args
                                    code_raw = content.split('<code>')[1].split('</code>')[0].strip()
                                result = TOOL_MAP['PythonInterpreter'].call(code_raw)
                                used_tools.add('PythonInterpreter')
                            except Exception as e:
                                result = f"[Python Interpreter Error]: {str(e)}"
                        else:
                            # Regular tool call
                            result = self.custom_call_tool(tool_name, tool_args)
                            if tool_name:
                                used_tools.add(tool_name)
                    
                    except Exception as e:
                        result = f'Error: Failed to execute tool call - {str(e)}'
                    
                    result = "<tool_response>\n" + result + "\n</tool_response>"
                    # Use proper OpenAI format with role "tool" and include tool_call_id
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": result
                    })
            elif '<tool_call>' in content and '</tool_call>' in content:
                # Fallback: Parse tool call from content if tool_calls_obj not available
                tool_call = content.split('<tool_call>')[1].split('</tool_call>')[0]
                try:
                    if "python" in tool_call.lower():
                        try:
                            code_raw=content.split('<tool_call>')[1].split('</tool_call>')[0].split('<code>')[1].split('</code>')[0].strip()
                            result = TOOL_MAP['PythonInterpreter'].call(code_raw)
                            used_tools.add('PythonInterpreter')
                        except:
                            result = "[Python Interpreter Error]: Formatting error."
                    else:
                        tool_call = json5.loads(tool_call)
                        tool_name = tool_call.get('name', '')
                        tool_args = tool_call.get('arguments', {})
                        result = self.custom_call_tool(tool_name, tool_args)
                        if tool_name:
                            used_tools.add(tool_name)
                except:
                    result = 'Error: Tool call is not a valid JSON. Tool call must contain a valid "name" and "arguments" field.'
                result = "<tool_response>\n" + result + "\n</tool_response>"
                messages.append({"role": "user", "content": result})
            if '<answer>' in content and '</answer>' in content:
                termination = 'answer'
                break
            if num_llm_calls_available <= 0 and '<answer>' not in content:
                messages[-1]['content'] = 'Sorry, the number of llm calls exceeds the limit.'

            max_tokens = 110 * 1024
            token_count = self.count_tokens(messages)
            print(f"round: {round}, token count: {token_count}")

            if token_count > max_tokens:
                print(f"Token quantity exceeds the limit: {token_count} > {max_tokens}")
                
                messages[-1]['content'] = "You have now reached the maximum context length you can handle. You should stop making tool calls and, based on all the information above, think again and provide what you consider the most likely answer in the following format:<think>your final thinking</think>\n<answer>your answer</answer>"
                
                # Apply tool response omission if configured
                messages_to_send_final = messages
                if OMIT_TOOL_RESPONSE_ROUNDS > 0:
                    messages_to_send_final = self.omit_old_tool_responses(messages, OMIT_TOOL_RESPONSE_ROUNDS)
                
                content, reasoning_content, tool_calls_obj = self.call_server(messages_to_send_final, planning_port)
                
                # Build final message with all fields
                final_message = {"role": "assistant", "content": content.strip()}
                if reasoning_content:
                    final_message["reasoning_content"] = reasoning_content.strip()
                if tool_calls_obj:
                    final_message["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in tool_calls_obj
                    ]
                messages.append(final_message)
                if '<answer>' in content and '</answer>' in content:
                    prediction = messages[-1]['content'].split('<answer>')[1].split('</answer>')[0]
                    termination = 'generate an answer as token limit reached'
                else:
                    prediction = messages[-1]['content']
                    termination = 'format error: generate an answer as token limit reached'
                result = {
                    "question": question,
                    "answer": answer,
                    "messages": messages,
                    "prediction": prediction,
                    "termination": termination,
                    "tools": self._get_tools_dict(used_tools)
                }
                return result

        if '<answer>' in messages[-1]['content']:
            prediction = messages[-1]['content'].split('<answer>')[1].split('</answer>')[0]
            termination = 'answer'
        else:
            prediction = 'No answer found.'
            termination = 'answer not found'
            if num_llm_calls_available == 0:
                termination = 'exceed available llm calls'
        result = {
            "question": question,
            "answer": answer,
            "messages": messages,
            "prediction": prediction,
            "termination": termination,
            "tools": self._get_tools_dict(used_tools)
        }
        return result

    def custom_call_tool(self, tool_name: str, tool_args: dict, **kwargs):
        if tool_name in TOOL_MAP:
            tool_args["params"] = tool_args
            if "python" in tool_name.lower():
                result = TOOL_MAP['PythonInterpreter'].call(tool_args)
            elif tool_name == "parse_file":
                params = {"files": tool_args["files"]}
                
                raw_result = asyncio.run(TOOL_MAP[tool_name].call(params, file_root_path="./eval_data/file_corpus"))
                result = raw_result

                if not isinstance(raw_result, str):
                    result = str(raw_result)
            else:
                raw_result = TOOL_MAP[tool_name].call(tool_args, **kwargs)
                result = raw_result
            return result

        else:
            return f"Error: Tool {tool_name} not found"
    
    def _get_tools_dict(self, used_tools: set) -> dict:
        """
        Get a dictionary of tool definitions that were used during the run.
        
        Args:
            used_tools: Set of tool names that were used
        
        Returns:
            Dictionary with tool names as keys and their definitions as values
        """
        from prompt import TOOL_DEFINITIONS
        tools_dict = {}
        
        for tool_name in used_tools:
            if tool_name in TOOL_DEFINITIONS:
                # Parse the JSON string to get the tool definition
                try:
                    tool_def = json.loads(TOOL_DEFINITIONS[tool_name])
                    tools_dict[tool_name] = tool_def
                except json.JSONDecodeError:
                    # If parsing fails, store the raw string
                    tools_dict[tool_name] = TOOL_DEFINITIONS[tool_name]
        
        return tools_dict
