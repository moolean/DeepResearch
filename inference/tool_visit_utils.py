"""
Shared utilities for visit, fetch_url, and browse tools.
This module contains common functions for fetching and processing web content.
"""
import os
import re
import time
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import tiktoken

# Environment variables
JINA_API_KEYS = os.getenv("JINA_API_KEYS", "")
USE_DIRECT_FETCH = os.getenv("USE_DIRECT_FETCH", "false").lower() == "true"
WEBCONTENT_MAXLENGTH = int(os.getenv("WEBCONTENT_MAXLENGTH", 150000))


def truncate_to_tokens(text: str, max_tokens: int = 95000) -> str:
    """
    Truncate text to a maximum number of tokens.
    
    Args:
        text: The text to truncate
        max_tokens: Maximum number of tokens to keep
        
    Returns:
        str: The truncated text
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)


def remove_text_links(text: str) -> str:
    """Remove markdown-style links from text."""
    return re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)


def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc if parsed.netloc else url
    except:
        return url


def direct_fetch_url(url: str, max_retries: int = 3) -> str:
    """
    Directly fetch URL content using requests with comprehensive headers to bypass anti-scraping.
    
    Args:
        url: The URL to fetch
        max_retries: Maximum number of retry attempts
        
    Returns:
        str: The webpage content or error message
    """
    for attempt in range(max_retries):
        try:
            # Set comprehensive headers to mimic a real browser
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "Referer": "https://www.google.com/"
            }
            
            response = requests.get(
                url,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                # Parse HTML content to extract text
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text
                text = soup.get_text()
                
                # Break into lines and remove leading/trailing space on each
                lines = (line.strip() for line in text.splitlines())
                # Break multi-headlines into a line each
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                # Drop blank lines
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                if len(text) > 100:  # Ensure we got meaningful content
                    return text
                else:
                    raise ValueError("Content too short, possibly failed to fetch")
            else:
                print(f"Direct fetch attempt {attempt + 1}/{max_retries}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"Direct fetch attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            if attempt < max_retries - 1:
                # Exponential backoff
                time.sleep(0.5 * (2 ** attempt))
                
    return "[Failed] Failed to read page."


def jina_search(query: str) -> str:
    """
    Search using Jina search service.
    
    Args:
        query: The search query
        
    Returns:
        str: The search results or error message
    """
    max_retries = 3
    timeout = 50
    
    for attempt in range(max_retries):
        headers = {
            "Authorization": f"Bearer {JINA_API_KEYS}",
        }
        try:
            response = requests.get(
                f"https://s.jina.ai/?q={query}",
                headers=headers,
                timeout=timeout
            )
            if response.status_code == 200:
                search_content = response.text
                return search_content
            else:
                raise ValueError("jina search error")
        except Exception as e:
            time.sleep(0.5)
            if attempt == max_retries - 1:
                return "[Failed] Failed to search."
            
    return "[Failed] Failed to search."


def jina_readpage(url: str) -> str:
    """
    Read webpage content using Jina service.
    
    Args:
        url: The URL to read
        
    Returns:
        str: The webpage content or error message
    """
    max_retries = 3
    timeout = 50
    
    for attempt in range(max_retries):
        headers = {
            "Authorization": f"Bearer {JINA_API_KEYS}",
        }
        try:
            response = requests.get(
                f"https://r.jina.ai/{url}",
                headers=headers,
                timeout=timeout
            )
            if response.status_code == 200:
                webpage_content = response.text
                return webpage_content
            else:
                raise ValueError("jina readpage error")
        except Exception as e:
            time.sleep(0.5)
            if attempt == max_retries - 1:
                return "[Failed] Failed to read page."
            
    return "[Failed] Failed to read page."


def fetch_webpage_content(url: str) -> str:
    """
    Fetch webpage content using direct fetch or Jina service based on configuration.
    
    Args:
        url: The URL to fetch
        
    Returns:
        str: The webpage content or error message
    """
    # If direct fetch is enabled, try it first
    if USE_DIRECT_FETCH:
        content = direct_fetch_url(url)
        if content and not content.startswith("[Failed]"):
            return content
        # If direct fetch fails, don't retry with Jina, just return failure
        return "[Failed] Failed to read page."
    
    # Otherwise use Jina reader service with retries
    max_attempts = 8
    for attempt in range(max_attempts):
        content = jina_readpage(url)
        if content and not content.startswith("[Failed]") and content != "[Failed] Empty content." and not content.startswith("[document_parser]"):
            return content
    return "[Failed] Failed to read page."
