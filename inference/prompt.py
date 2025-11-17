import os

# Default system prompt template
DEFAULT_SYSTEM_PROMPT = """You are a deep research assistant. Your core function is to conduct thorough, multi-source investigations into any topic. You must handle both broad, open-domain inquiries and queries within specialized academic fields. For every request, synthesize information from credible, diverse sources to deliver a comprehensive, accurate, and objective response. When you have gathered sufficient information and are ready to provide the definitive response, you must enclose the entire final answer within <answer></answer> tags.

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tool_definitions}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{{"name": <function-name>, "arguments": <args-json-object>}}
</tool_call>

Current date: """

# Tool definitions mapping
TOOL_DEFINITIONS = {
    "search": '{"type": "function", "function": {"name": "search", "description": "Perform Google web searches then returns a string of the top search results. Accepts multiple queries.", "parameters": {"type": "object", "properties": {"query": {"type": "array", "items": {"type": "string", "description": "The search query."}, "minItems": 1, "description": "The list of search queries."}}, "required": ["query"]}}}',
    "visit": '{"type": "function", "function": {"name": "visit", "description": "Visit webpage(s) and return the summary of the content.", "parameters": {"type": "object", "properties": {"url": {"type": "array", "items": {"type": "string"}, "description": "The URL(s) of the webpage(s) to visit. Can be a single URL or an array of URLs."}, "goal": {"type": "string", "description": "The specific information goal for visiting webpage(s)."}}, "required": ["url", "goal"]}}}',
    "PythonInterpreter": '{"type": "function", "function": {"name": "PythonInterpreter", "description": "Executes Python code in a sandboxed environment. To use this tool, you must follow this format:\\n1. The \'arguments\' JSON object must be empty: {}.\\n2. The Python code to be executed must be placed immediately after the JSON block, enclosed within <code> and </code> tags.\\n\\nIMPORTANT: Any output you want to see MUST be printed to standard output using the print() function.\\n\\nExample of a correct call:\\n<tool_call>\\n{\\"name\\": \\"PythonInterpreter\\", \\"arguments\\": {}}\\n<code>\\nimport numpy as np\\n# Your code here\\nprint(f\\"The result is: {np.mean([1,2,3])}\\")\\n</code>\\n</tool_call>", "parameters": {"type": "object", "properties": {}, "required": []}}}',
    "google_scholar": '{"type": "function", "function": {"name": "google_scholar", "description": "Leverage Google Scholar to retrieve relevant information from academic publications. Accepts multiple queries. This tool will also return results from google search", "parameters": {"type": "object", "properties": {"query": {"type": "array", "items": {"type": "string", "description": "The search query."}, "minItems": 1, "description": "The list of search queries for Google Scholar."}}, "required": ["query"]}}}',
    "parse_file": '{"type": "function", "function": {"name": "parse_file", "description": "This is a tool that can be used to parse multiple user uploaded local files such as PDF, DOCX, PPTX, TXT, CSV, XLSX, DOC, ZIP, MP4, MP3.", "parameters": {"type": "object", "properties": {"files": {"type": "array", "items": {"type": "string"}, "description": "The file name of the user uploaded local files to be parsed."}}, "required": ["files"]}}}'
}

def get_system_prompt(enabled_tools=None):
    """
    Get the system prompt with tools dynamically filtered based on enabled_tools.
    
    Args:
        enabled_tools: List of enabled tool names, or None to enable all tools
    
    Returns:
        System prompt string with appropriate tool definitions
    """
    # Load custom system prompt from environment if available
    custom_prompt = os.getenv('SYSTEM_PROMPT')
    if custom_prompt:
        return custom_prompt
    
    # Filter tool definitions based on enabled tools
    if enabled_tools is None:
        enabled_tools = list(TOOL_DEFINITIONS.keys())
    
    tool_defs = [TOOL_DEFINITIONS[tool] for tool in enabled_tools if tool in TOOL_DEFINITIONS]
    tool_definitions_str = '\n'.join(tool_defs)
    
    return DEFAULT_SYSTEM_PROMPT.replace('{tool_definitions}', tool_definitions_str)

# For backward compatibility
SYSTEM_PROMPT = get_system_prompt()

# Default extractor prompt
DEFAULT_EXTRACTOR_PROMPT = """Please process the following webpage content and user goal to extract relevant information:

## **Webpage Content** 
{webpage_content}

## **User Goal**
{goal}

## **Task Guidelines**
1. **Content Scanning for Rational**: Locate the **specific sections/data** directly related to the user's goal within the webpage content
2. **Key Extraction for Evidence**: Identify and extract the **most relevant information** from the content, you never miss any important information, output the **full original context** of the content as far as possible, it can be more than three paragraphs.
3. **Summary Output for Summary**: Organize into a concise paragraph with logical flow, prioritizing clarity and judge the contribution of the information to the goal.

**Final Output Format using JSON format has "rational", "evidence", "summary" feilds**
"""

def get_extractor_prompt():
    """Get the extractor prompt from environment or use default."""
    return os.getenv('EXTRACTOR_PROMPT', DEFAULT_EXTRACTOR_PROMPT)

# For backward compatibility
EXTRACTOR_PROMPT = get_extractor_prompt()
