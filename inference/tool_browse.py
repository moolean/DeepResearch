"""
Tool for browsing the web using Jina search interface.
"""
import os
from typing import Union
from qwen_agent.tools.base import BaseTool, register_tool
from tool_visit_utils import jina_search, remove_text_links, WEBCONTENT_MAXLENGTH


@register_tool('browse', allow_overwrite=True)
class Browse(BaseTool):
    """
    Tool for browsing the web using Jina search interface.
    Returns query-related webpage content.
    """
    name = 'browse'
    description = 'Browse the web using a search query. Returns relevant webpage content related to the query without requiring specific URLs.'
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find relevant webpage content."
            }
        },
        "required": ["query"]
    }
    
    def call(self, params: Union[str, dict], **kwargs) -> str:
        """
        Browse the web using a search query.
        
        Args:
            params: Dictionary containing 'query' field
            
        Returns:
            str: The search results or error message
        """
        try:
            query = params["query"]
        except:
            return "[browse] Invalid request format: Input must be a JSON object containing 'query' field"
        
        # Search using Jina
        content = jina_search(query)
        
        # If search failed, return early
        if not content or content.startswith("[Failed]"):
            return f"[browse] Failed to search for query: {query}. The search could not be completed."
        
        # Clean content by removing markdown links
        content_cleaned = remove_text_links(content)
        
        # Truncate content to reasonable length
        content_cleaned = content_cleaned[:WEBCONTENT_MAXLENGTH] if len(content_cleaned) > WEBCONTENT_MAXLENGTH else content_cleaned
        
        # Format the output
        result = f"Search results for query: {query}\n\n"
        result += f"[Content]:\n{content_cleaned}\n"
        
        return result
