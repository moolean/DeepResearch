"""
Tool for fetching webpage content without summarization.
"""
import os
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from tool_visit_utils import (
    fetch_webpage_content,
    remove_text_links,
    get_domain,
    WEBCONTENT_MAXLENGTH
)


@register_tool('fetch_url', allow_overwrite=True)
class FetchUrl(BaseTool):
    """
    Tool for fetching webpage content without summarization.
    Returns raw webpage content truncated to max length.
    """
    name = 'fetch_url'
    description = 'Fetch webpage content directly without summarization. Returns the raw content of the webpage truncated to a reasonable length.'
    
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the webpage to fetch."
            }
        },
        "required": ["url"]
    }
    
    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Fetch webpage content without summarization.
        
        Args:
            params: Dictionary containing 'url' field
            
        Returns:
            str: The webpage content or error message
        """
        try:
            url = params["url"]
        except:
            return "[fetch_url] Invalid request format: Input must be a JSON object containing 'url' field"
        
        # Fetch webpage content
        content = fetch_webpage_content(url)
        
        # If content fetch failed, return early
        if not content or content.startswith("[Failed]"):
            return f"[fetch_url] Failed to fetch content from {url}. The webpage could not be accessed. Please check the URL."
        
        # Clean content by removing markdown links
        content_cleaned = remove_text_links(content)
        
        # Truncate content to reasonable length
        content_cleaned = content_cleaned[:WEBCONTENT_MAXLENGTH] if len(content_cleaned) > WEBCONTENT_MAXLENGTH else content_cleaned
        
        # Format the output
        site_name = get_domain(url)
        result = f"Content from {url}:\n\n"
        result += f"[Website]: {site_name}\n"
        result += f"[URL]: {url}\n"
        result += f"[Content]:\n{content_cleaned}\n"
        
        return result
