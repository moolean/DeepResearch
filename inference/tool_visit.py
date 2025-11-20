import json
import os
from typing import List, Union
from qwen_agent.tools.base import BaseTool, register_tool
from prompt import EXTRACTOR_PROMPT 
from openai import OpenAI
import time 
from tool_visit_utils import (
    fetch_webpage_content,
    truncate_to_tokens,
    remove_text_links,
    get_domain,
    WEBCONTENT_MAXLENGTH
)

VISIT_SERVER_TIMEOUT = int(os.getenv("VISIT_SERVER_TIMEOUT", 200))
ENABLE_SUMMARY = os.getenv("ENABLE_SUMMARY", "true").lower() == "true"

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




    def readpage_jina(self, url: str, goal: str) -> str:
        """
        Fetch webpage content and summarize it based on the goal.
        
        Args:
            url: The URL to read
            goal: The goal/purpose of reading the page
            
        Returns:
            str: The summarized webpage content or error message
        """
        summary_page_func = self.call_server
        max_retries = int(os.getenv('VISIT_SERVER_MAX_RETRIES', 1))

        # Fetch webpage content using shared utility
        content = fetch_webpage_content(url)

        # If content fetch failed, return early without summary
        if not content or content.startswith("[Failed]") or content == "[Failed] Empty content." or content.startswith("[document_parser]"):
            useful_information = "The useful information in {url} for user goal {goal} as follows: \n\n".format(url=url, goal=goal)
            useful_information += "Evidence in page: \n" + "The provided webpage content could not be accessed. Please check the URL or file format." + "\n\n"
            useful_information += "Summary: \n" + "The webpage content could not be processed, and therefore, no information is available." + "\n\n"
            return useful_information

        # If ENABLE_SUMMARY is False, return content without summarization
        if not ENABLE_SUMMARY:
            # Clean content by removing markdown links
            content_cleaned = remove_text_links(content)
            # Truncate content to reasonable length
            content_cleaned = content_cleaned[:WEBCONTENT_MAXLENGTH] if len(content_cleaned) > WEBCONTENT_MAXLENGTH else content_cleaned
            
            # Format similar to Jina search algorithm
            site_name = get_domain(url)
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

    