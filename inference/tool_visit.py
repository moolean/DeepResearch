import json
import os
import signal
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Union, Tuple, Optional
import requests
from qwen_agent.tools.base import BaseTool, register_tool
from prompt import EXTRACTOR_PROMPT 
from openai import OpenAI
import random
from urllib.parse import urlparse, unquote
import time 
from transformers import AutoTokenizer
import tiktoken
import asyncio
import ssl
import httpx

VISIT_SERVER_TIMEOUT = int(os.getenv("VISIT_SERVER_TIMEOUT", 200))
WEBCONTENT_MAXLENGTH = int(os.getenv("WEBCONTENT_MAXLENGTH", 150000))

JINA_API_KEYS = os.getenv("JINA_API_KEYS", "")
USE_DIRECT_FETCH = os.getenv("USE_DIRECT_FETCH", "false").lower() == "true"


@staticmethod
def truncate_to_tokens(text: str, max_tokens: int = 95000) -> str:
    encoding = tiktoken.get_encoding("cl100k_base")
    
    tokens = encoding.encode(text)
    if len(tokens) <= max_tokens:
        return text
    
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)

OSS_JSON_FORMAT = """# Response Formats
## visit_content
{"properties":{"rational":{"type":"string","description":"Locate the **specific sections/data** directly related to the user's goal within the webpage content"},"evidence":{"type":"string","description":"Identify and extract the **most relevant information** from the content, never miss any important information, output the **full original context** of the content as far as possible, it can be more than three paragraphs.","summary":{"type":"string","description":"Organize into a concise paragraph with logical flow, prioritizing clarity and judge the contribution of the information to the goal."}}}}"""


@register_tool('visit', allow_overwrite=True)
class Visit(BaseTool):
    # The `description` tells the agent the functionality of this tool.
    name = 'visit'
    description = 'Visit webpage(s) and return the summary of the content.'
    # The `parameters` tell the agent what input parameters the tool has.
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": ["string", "array"],
                "items": {
                    "type": "string"
                    },
                "minItems": 1,
                "description": "The URL(s) of the webpage(s) to visit. Can be a single URL or an array of URLs."
        },
        "goal": {
                "type": "string",
                "description": "The goal of the visit for webpage(s)."
        }
        },
        "required": ["url", "goal"]
    }
    # The `call` method is the main function of the tool.
    def call(self, params: Union[str, dict], **kwargs) -> str:
        try:
            url = params["url"]
            goal = params["goal"]
        except:
            return "[Visit] Invalid request format: Input must be a JSON object containing 'url' and 'goal' fields"

        start_time = time.time()
        
        # Create log folder if it doesn't exist
        log_folder = "log"
        os.makedirs(log_folder, exist_ok=True)

        if isinstance(url, str):
            response = self.readpage_jina(url, goal)
        else:
            response = []
            assert isinstance(url, List)
            start_time = time.time()
            for u in url: 
                if time.time() - start_time > 900:
                    cur_response = "The useful information in {url} for user goal {goal} as follows: \n\n".format(url=url, goal=goal)
                    cur_response += "Evidence in page: \n" + "The provided webpage content could not be accessed. Please check the URL or file format." + "\n\n"
                    cur_response += "Summary: \n" + "The webpage content could not be processed, and therefore, no information is available." + "\n\n"
                else:
                    try:
                        cur_response = self.readpage_jina(u, goal)
                    except Exception as e:
                        cur_response = f"Error fetching {u}: {str(e)}"
                response.append(cur_response)
            response = "\n=======\n".join(response)
        
        print(f'Summary Length {len(response)}; Summary Content {response}')
        return response.strip()
        
    def call_server(self, msgs, max_retries=2):
        api_key = os.environ.get("API_KEY")
        url_llm = os.environ.get("API_BASE")
        model_name = os.environ.get("SUMMARY_MODEL_NAME", "")
        client = OpenAI(
            api_key=api_key,
            base_url=url_llm,
        )
        for attempt in range(max_retries):
            try:
                chat_response = client.chat.completions.create(
                    model=model_name,
                    messages=msgs,
                    temperature=0.7
                )
                content = chat_response.choices[0].message.content
                if content:
                    try:
                        json.loads(content)
                    except:
                        # extract json from string 
                        left = content.find('{')
                        right = content.rfind('}') 
                        if left != -1 and right != -1 and left <= right: 
                            content = content[left:right+1]
                    return content
            except Exception as e:
                # print(e)
                if attempt == (max_retries - 1):
                    return ""
                continue

    async def direct_fetch_url(self, url: str, max_retries: int = 3, retry_delay: float = 2.0) -> Tuple[Optional[str], Optional[str]]:
        """
        Directly fetch and extract content from a URL using httpx and trafilatura.
        
        Args:
            url: The URL to fetch
            max_retries: Maximum number of retry attempts
            retry_delay: Base delay between retries in seconds
            
        Returns:
            Tuple of (text_content, error_message). If successful, returns (text, None).
            If failed, returns (None, error_message).
        """
        html = None
        last_error = None
        
        try:
            import trafilatura
        except ImportError:
            return None, "trafilatura is not installed. Please install it with: pip install trafilatura"
        
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
                
                # Add delay between retries
                if attempt > 0:
                    await asyncio.sleep(retry_delay * attempt)
                
                # Create a custom SSL context that allows legacy renegotiation
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                # Enable legacy renegotiation for older servers
                ssl_context.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
                
                # Fetch HTML content with longer timeout and retry logic
                async with httpx.AsyncClient(
                    timeout=10.0, 
                    follow_redirects=True,
                    max_redirects=5,
                    http2=True,
                    verify=ssl_context
                ) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    html = response.text
                    break  # Success, exit retry loop
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    print(f"HTTP 403 for URL {url} (attempt {attempt + 1}/{max_retries})")
                    last_error = (
                        f"Access denied (HTTP 403). The website '{url}' is blocking automated requests. "
                        "This could be due to rate limiting, WAF protection, or bot detection. "
                        "Please try a different URL or access the site manually."
                    )
                    if attempt < max_retries - 1:
                        continue  # Retry
                elif e.response.status_code == 404:
                    last_error = f"Page not found (HTTP 404). The URL '{url}' does not exist."
                    break  # Don't retry for 404
                elif e.response.status_code >= 500:
                    print(f"Server error {e.response.status_code} for URL {url} (attempt {attempt + 1}/{max_retries})")
                    last_error = f"Server error (HTTP {e.response.status_code}). The website is experiencing issues. Please try again later."
                    if attempt < max_retries - 1:
                        continue  # Retry for server errors
                else:
                    last_error = f"HTTP error {e.response.status_code}: {str(e)[:200]}"
                    break  # Don't retry for other errors
            except httpx.TimeoutException:
                print(f"Timeout for URL {url} (attempt {attempt + 1}/{max_retries})")
                last_error = f"Request timeout. The website took too long to respond. Please try again later."
                if attempt < max_retries - 1:
                    continue  # Retry on timeout
            except httpx.RequestError as e:
                print(f"Request error for URL {url}: {e} (attempt {attempt + 1}/{max_retries})")
                last_error = f"Network error: {str(e)}"
                if attempt < max_retries - 1:
                    continue  # Retry on network errors
            except Exception as e:
                print(f"Unexpected error fetching URL {url}: {e}")
                last_error = f"Unexpected error: {str(e)}"
                break  # Don't retry for unexpected errors
        
        if html is None:
            return None, last_error or "Failed to fetch HTML content after all retries"
        
        try:
            # Extract text content using trafilatura
            # Run in executor since trafilatura is synchronous
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(
                None,
                lambda: trafilatura.extract(
                    html,
                    include_comments=False,
                    include_images=False,
                    include_tables=False,
                    favor_recall=True,
                    fast=True
                )
            )
            
            if not text:
                return None, "Could not extract readable content from the page. The page may be empty or use unsupported formats."
            
            return text, None
        except Exception as e:
            print(f"Error extracting content: {e}")
            return None, f"Content extraction failed: {str(e)}"

    def direct_fetch_url_sync(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Synchronous wrapper for direct_fetch_url.
        
        Args:
            url: The URL to fetch
            
        Returns:
            Tuple of (text_content, error_message)
        """
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_running_loop()
                # If there's already a running loop, create a new one in a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.direct_fetch_url(url))
                    return future.result(timeout=60)
            except RuntimeError:
                # No running loop, we can create one
                return asyncio.run(self.direct_fetch_url(url))
        except Exception as e:
            return None, f"Error in direct fetch: {str(e)}"


    def jina_readpage(self, url: str) -> str:
        """
        Read webpage content using Jina service.
        
        Args:
            url: The URL to read
            goal: The goal/purpose of reading the page
            
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
                    print(response.text)
                    raise ValueError("jina readpage error")
            except Exception as e:
                time.sleep(0.5)
                if attempt == max_retries - 1:
                    return "[visit] Failed to read page."
                
        return "[visit] Failed to read page."

    def html_readpage_jina(self, url: str) -> str:
        # Check if direct fetch is enabled
        if USE_DIRECT_FETCH:
            print(f"Using direct fetch for URL: {url}")
            text_content, error = self.direct_fetch_url_sync(url)
            if text_content:
                return text_content
            else:
                print(f"Direct fetch failed: {error}")
                return "[visit] Failed to read page."
        
        # Use Jina API if direct fetch is disabled or not configured
        max_attempts = 8
        for attempt in range(max_attempts):
            content = self.jina_readpage(url)
            service = "jina"     
            print(service)
            if content and not content.startswith("[visit] Failed to read page.") and content != "[visit] Empty content." and not content.startswith("[document_parser]"):
                return content
        return "[visit] Failed to read page."

    def readpage_jina(self, url: str, goal: str) -> str:
        """
        Attempt to read webpage content by alternating between jina and aidata services.
        
        Args:
            url: The URL to read
            goal: The goal/purpose of reading the page
            
        Returns:
            str: The webpage content or error message
        """
   
        summary_page_func = self.call_server
        max_retries = int(os.getenv('VISIT_SERVER_MAX_RETRIES', 1))

        content = self.html_readpage_jina(url)

        if content and not content.startswith("[visit] Failed to read page.") and content != "[visit] Empty content." and not content.startswith("[document_parser]"):
            content = truncate_to_tokens(content, max_tokens=95000)
            messages = [{"role":"user","content": EXTRACTOR_PROMPT.format(webpage_content=content, goal=goal)}]
            parse_retry_times = 0
            raw = summary_page_func(messages, max_retries=max_retries)
            summary_retries = 3
            while len(raw) < 10 and summary_retries >= 0:
                truncate_length = int(0.7 * len(content)) if summary_retries > 0 else 25000
                status_msg = (
                    f"[visit] Summary url[{url}] " 
                    f"attempt {3 - summary_retries + 1}/3, "
                    f"content length: {len(content)}, "
                    f"truncating to {truncate_length} chars"
                ) if summary_retries > 0 else (
                    f"[visit] Summary url[{url}] failed after 3 attempts, "
                    f"final truncation to 25000 chars"
                )
                print(status_msg)
                content = content[:truncate_length]
                extraction_prompt = EXTRACTOR_PROMPT.format(
                    webpage_content=content,
                    goal=goal
                )
                messages = [{"role": "user", "content": extraction_prompt}]
                raw = summary_page_func(messages, max_retries=max_retries)
                summary_retries -= 1

            parse_retry_times = 2
            if isinstance(raw, str):
                raw = raw.replace("```json", "").replace("```", "").strip()
            while parse_retry_times < 3:
                try:
                    raw = json.loads(raw)
                    break
                except:
                    raw = summary_page_func(messages, max_retries=max_retries)
                    parse_retry_times += 1
            
            if parse_retry_times >= 3:
                useful_information = "The useful information in {url} for user goal {goal} as follows: \n\n".format(url=url, goal=goal)
                useful_information += "Evidence in page: \n" + "The provided webpage content could not be accessed. Please check the URL or file format." + "\n\n"
                useful_information += "Summary: \n" + "The webpage content could not be processed, and therefore, no information is available." + "\n\n"
            else:
                useful_information = "The useful information in {url} for user goal {goal} as follows: \n\n".format(url=url, goal=goal)
                useful_information += "Evidence in page: \n" + str(raw["evidence"]) + "\n\n"
                useful_information += "Summary: \n" + str(raw["summary"]) + "\n\n"

            if len(useful_information) < 10 and summary_retries < 0:
                print("[visit] Could not generate valid summary after maximum retries")
                useful_information = "[visit] Failed to read page"
            
            return useful_information

        # If no valid content was obtained after all retries
        else:
            useful_information = "The useful information in {url} for user goal {goal} as follows: \n\n".format(url=url, goal=goal)
            useful_information += "Evidence in page: \n" + "The provided webpage content could not be accessed. Please check the URL or file format." + "\n\n"
            useful_information += "Summary: \n" + "The webpage content could not be processed, and therefore, no information is available." + "\n\n"
            return useful_information

    