import json
import os
import signal
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Union
import requests
from qwen_agent.tools.base import BaseTool, register_tool
from prompt import EXTRACTOR_PROMPT 
from openai import OpenAI
import random
from urllib.parse import urlparse, unquote
import time 
from transformers import AutoTokenizer
import tiktoken
import re
from bs4 import BeautifulSoup

VISIT_SERVER_TIMEOUT = int(os.getenv("VISIT_SERVER_TIMEOUT", 200))
WEBCONTENT_MAXLENGTH = int(os.getenv("WEBCONTENT_MAXLENGTH", 150000))

JINA_API_KEYS = os.getenv("JINA_API_KEYS", "")
USE_DIRECT_FETCH = os.getenv("USE_DIRECT_FETCH", "false").lower() == "true"
ENABLE_SUMMARY = os.getenv("ENABLE_SUMMARY", "true").lower() == "true"


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


    def direct_fetch_url(self, url: str, max_retries: int = 3) -> str:
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
                    
        return "[visit] Failed to read page."

    def remove_text_links(self, text: str) -> str:
        """Remove markdown-style links from text."""
        return re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)
    
    def get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc if parsed.netloc else url
        except:
            return url

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
                    # print(response.text)
                    raise ValueError("jina readpage error")
            except Exception as e:
                time.sleep(0.5)
                if attempt == max_retries - 1:
                    return "[visit] Failed to read page."
                
        return "[visit] Failed to read page."

    def html_readpage_jina(self, url: str) -> str:
        """
        Read webpage content, using direct fetch if USE_DIRECT_FETCH is enabled,
        otherwise falling back to Jina service.
        """
        # If direct fetch is enabled, try it first
        if USE_DIRECT_FETCH:
            content = self.direct_fetch_url(url)
            if content and not content.startswith("[visit] Failed to read page."):
                return content
            # If direct fetch fails, don't retry with Jina, just return failure
            return "[visit] Failed to read page."
        
        # Otherwise use Jina service with retries
        max_attempts = 8
        for attempt in range(max_attempts):
            content = self.jina_readpage(url)
            service = "jina"     
            # print(service)
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

        # If content fetch failed, return early without summary
        if not content or content.startswith("[visit] Failed to read page.") or content == "[visit] Empty content." or content.startswith("[document_parser]"):
            useful_information = "The useful information in {url} for user goal {goal} as follows: \n\n".format(url=url, goal=goal)
            useful_information += "Evidence in page: \n" + "The provided webpage content could not be accessed. Please check the URL or file format." + "\n\n"
            useful_information += "Summary: \n" + "The webpage content could not be processed, and therefore, no information is available." + "\n\n"
            return useful_information

        # If ENABLE_SUMMARY is False, return content without summarization
        if not ENABLE_SUMMARY:
            # Clean content by removing markdown links
            content_cleaned = self.remove_text_links(content)
            # Truncate content to reasonable length
            content_cleaned = content_cleaned[:WEBCONTENT_MAXLENGTH] if len(content_cleaned) > WEBCONTENT_MAXLENGTH else content_cleaned
            
            # Format similar to Jina search algorithm
            site_name = self.get_domain(url)
            useful_information = f"The information from {url} for user goal '{goal}' as follows:\n\n"
            useful_information += f"[Website]: {site_name}\n"
            useful_information += f"[URL]: {url}\n"
            useful_information += f"[Content]:\n{content_cleaned}\n\n"
            
            return useful_information

        # Otherwise, use summary model
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

    