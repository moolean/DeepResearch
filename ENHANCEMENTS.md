# Visit Tool Enhancements

This document describes the three major enhancements made to the Visit tool and React Agent in DeepResearch.

## Overview

Three new features have been added to improve flexibility, reduce costs, and manage context better:

1. **Direct URL Fetching** - Fetch web pages directly without relying on Jina API
2. **No-Summary Mode** - Skip LLM summarization to save costs and get full content
3. **Tool Response Omission** - Automatically omit old tool responses to manage context

## 1. Direct URL Fetching

### Description
The Visit tool can now fetch URLs directly using HTTP requests with comprehensive anti-scraping headers, instead of relying solely on the Jina API.

### Environment Variable
```bash
USE_DIRECT_FETCH=true  # Enable direct fetching (default: false)
```

### Features
- **Comprehensive Browser Headers**: Mimics a real browser with User-Agent, Accept headers, etc.
- **Retry Logic**: Implements exponential backoff (3 retries by default)
- **HTML Parsing**: Uses BeautifulSoup4 to extract clean text from HTML
- **Error Handling**: Returns error message for inaccessible pages without attempting summary

### Use Cases
- When Jina API is unavailable or rate-limited
- For common websites (news, blogs, documentation)
- When you need more control over the fetching process
- To reduce dependency on external services

### Implementation Details
```python
# In tool_visit.py
def direct_fetch_url(self, url: str, max_retries: int = 3) -> str:
    """
    Directly fetch URL content using requests with comprehensive headers.
    """
    for attempt in range(max_retries):
        headers = {
            "User-Agent": "Mozilla/5.0...",
            "Accept": "text/html...",
            "Referer": "https://www.google.com/",
            # ... more headers
        }
        response = requests.get(url, headers=headers, timeout=30)
        # Parse HTML and extract text
        # ...
```

### Limitations
- May fail on heavily protected websites
- Does not handle JavaScript-rendered content
- Requires beautifulsoup4 dependency

## 2. No-Summary Mode

### Description
The Visit tool can now return raw webpage content without invoking the LLM-based summarization. When disabled, it automatically switches to use Jina's search endpoint (`https://s.jina.ai`) instead of the reader endpoint (`https://r.jina.ai`), providing search-optimized results.

### Environment Variable
```bash
ENABLE_SUMMARY=false  # Disable LLM summarization (default: true)
```

### Features
- **Automatic Endpoint Switching**: Uses Jina search endpoint (`s.jina.ai/?q={url}`) when summary is disabled
- **Full Content Preservation**: Returns complete webpage text without truncation
- **Cost Reduction**: Skips expensive LLM API calls for summarization
- **Lower Latency**: No waiting for summary model response
- **Markdown Link Removal**: Cleans up markdown-style links for readability

### Output Format
When `ENABLE_SUMMARY=false`, the output format is:
```
The information from {url} for user goal '{goal}' as follows:

[Website]: example.com
[URL]: https://example.com/page
[Content]:
{full webpage content}
```

### Use Cases
- When you need the full, unprocessed webpage content
- For structured data extraction tasks
- When working with content that doesn't need summarization
- To reduce API costs and latency

### Implementation Details
```python
# In tool_visit.py

# New method for Jina search endpoint
def jina_search(self, url: str) -> str:
    """Search using Jina search service."""
    response = requests.get(
        f"https://s.jina.ai/?q={url}",
        headers={"Authorization": f"Bearer {JINA_API_KEYS}"},
        timeout=50
    )
    return response.text

# Modified html_readpage_jina to use search endpoint when ENABLE_SUMMARY=false
if not ENABLE_SUMMARY:
    content = self.jina_search(url)  # Use search endpoint instead of reader
else:
    content = self.jina_readpage(url)  # Use reader endpoint with summary

# Format output when ENABLE_SUMMARY=false
if not ENABLE_SUMMARY:
    content_cleaned = self.remove_text_links(content)
    content_cleaned = content_cleaned[:WEBCONTENT_MAXLENGTH]
    
    useful_information = f"The information from {url}...\n"
    useful_information += f"[Website]: {site_name}\n"
    useful_information += f"[URL]: {url}\n"
    useful_information += f"[Content]:\n{content_cleaned}\n\n"
```

## 3. Tool Response Omission

### Description
The React Agent can now automatically replace old tool responses with placeholder text, keeping only the most recent K rounds of full responses. This helps manage context window size in long conversations.

### Environment Variable
```bash
OMIT_TOOL_RESPONSE_ROUNDS=5  # Keep last 5 rounds (default: 0 = disabled)
```

### Features
- **Automatic Management**: Applied before each LLM call
- **Configurable**: Set K to control how many rounds to keep
- **Preserves Structure**: Keeps message structure intact, only replaces content
- **Smart Detection**: Identifies tool responses by role="tool" or content markers

### Behavior
- When K=0 (default): Feature disabled, all responses kept
- When K>0: Keeps last K tool responses, replaces older ones with:
  ```
  <tool_response>
  tool response omitted
  </tool_response>
  ```

### Use Cases
- Long research sessions with many tool calls
- When approaching context length limits
- To maintain conversation history without full tool outputs
- For better token efficiency in extended interactions

### Implementation Details
```python
# In react_agent.py
def omit_old_tool_responses(self, messages: List[dict], keep_rounds: int) -> List[dict]:
    """
    Replace tool response content older than K rounds with placeholder.
    """
    # Find all tool response indices
    tool_response_indices = []
    for i, msg in enumerate(messages):
        if msg.get("role") == "tool" or "<tool_response>" in msg.get("content", ""):
            tool_response_indices.append(i)
    
    # Calculate how many to omit
    num_to_omit = max(0, len(tool_response_indices) - keep_rounds)
    
    # Replace old responses
    for i in range(num_to_omit):
        messages[tool_response_indices[i]]["content"] = "<tool_response>\ntool response omitted\n</tool_response>"
```

### Example
```python
# Before (4 tool responses, keep_rounds=2):
messages = [
    {"role": "tool", "content": "Old response 1"},     # Will be omitted
    {"role": "tool", "content": "Old response 2"},     # Will be omitted
    {"role": "tool", "content": "Recent response 1"},  # Kept
    {"role": "tool", "content": "Recent response 2"},  # Kept
]

# After omission:
messages = [
    {"role": "tool", "content": "<tool_response>\ntool response omitted\n</tool_response>"},
    {"role": "tool", "content": "<tool_response>\ntool response omitted\n</tool_response>"},
    {"role": "tool", "content": "Recent response 1"},
    {"role": "tool", "content": "Recent response 2"},
]
```

## Configuration Examples

### Example 1: Cost-Effective Web Scraping
```bash
USE_DIRECT_FETCH=true
ENABLE_SUMMARY=false
```
- Fetches pages directly without Jina
- No LLM summarization
- **Lowest cost**, full content preserved

### Example 2: High-Quality Research
```bash
USE_DIRECT_FETCH=false
ENABLE_SUMMARY=true
```
- Uses Jina for reliable fetching
- LLM summarization for quality
- **Highest quality**, best for complex research

### Example 3: Long Conversations
```bash
OMIT_TOOL_RESPONSE_ROUNDS=10
```
- Keeps only last 10 rounds of tool responses
- Prevents context overflow
- **Best for extended sessions**

### Example 4: Hybrid Approach
```bash
USE_DIRECT_FETCH=true
ENABLE_SUMMARY=true
OMIT_TOOL_RESPONSE_ROUNDS=5
```
- Direct fetch for reliability
- Summary for quality
- Response omission for long conversations
- **Balanced approach**

## Dependencies

Added dependency:
```
beautifulsoup4==4.12.3
```

This is required for HTML parsing when using direct URL fetching.

## Testing

Three test files have been created:

1. **test_visit_basic.py** - Tests core logic without full dependencies
2. **test_visit_enhancements.py** - Comprehensive unit tests (requires full environment)
3. **test_visit_integration.py** - Integration tests and documentation verification

Run tests:
```bash
python3 tests/test_visit_basic.py
python3 tests/test_visit_integration.py
```

## Migration Guide

### For Existing Users

No changes are required for existing users. All features are **opt-in** via environment variables:

1. Copy `.env.example` to `.env` if you haven't already
2. Add the new variables to your `.env` file:
   ```bash
   USE_DIRECT_FETCH=false
   ENABLE_SUMMARY=true
   OMIT_TOOL_RESPONSE_ROUNDS=0
   ```
3. Install new dependency:
   ```bash
   pip install beautifulsoup4==4.12.3
   ```

### Enabling Features

Enable features by updating your `.env` file:

```bash
# Enable direct fetching
USE_DIRECT_FETCH=true

# Disable summarization
ENABLE_SUMMARY=false

# Enable response omission (keep last 10 rounds)
OMIT_TOOL_RESPONSE_ROUNDS=10
```

## Performance Considerations

### Direct Fetch
- **Pros**: No API rate limits, faster for some sites
- **Cons**: May fail on protected sites, no JavaScript support

### No-Summary Mode
- **Pros**: Lower latency, reduced costs, full content
- **Cons**: Larger context usage, no content distillation

### Response Omission
- **Pros**: Better token efficiency, longer sessions possible
- **Cons**: Agent loses access to old tool outputs

## Troubleshooting

### Direct Fetch Failures
If direct fetch fails frequently:
1. Check if the target website blocks scrapers
2. Consider using `USE_DIRECT_FETCH=false` to fall back to Jina
3. Verify internet connectivity and firewall settings

### Content Too Long
If content exceeds limits:
1. Enable `ENABLE_SUMMARY=true` to get condensed content
2. Adjust `WEBCONTENT_MAXLENGTH` environment variable
3. Use response omission to manage context

### Context Overflow
If you hit context limits:
1. Enable `OMIT_TOOL_RESPONSE_ROUNDS` with appropriate value
2. Reduce the number of tool calls per session
3. Consider splitting long research tasks

## Future Enhancements

Potential improvements:
- User-agent rotation for better anti-scraping
- JavaScript rendering support (e.g., Playwright)
- Smart response omission based on importance
- Configurable content extraction strategies

## Support

For issues or questions:
1. Check the test files for usage examples
2. Review the `.env.example` for configuration options
3. See the implementation in `inference/tool_visit.py` and `inference/react_agent.py`
