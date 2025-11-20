# Web Content Tools Refactoring

## Overview

The original `visit` tool has been refactored into three separate, specialized tools to provide more flexibility and clarity in web content retrieval:

1. **visit** - Web page visiting with LLM summarization
2. **fetch_url** - Direct webpage content fetching without summarization
3. **browse** - Web browsing using search queries

## Tool Descriptions

### 1. visit

**Purpose:** Visit webpage(s) and return an LLM-generated summary of the content based on a specific goal.

**Parameters:**
- `url` (required): The URL(s) of the webpage(s) to visit. Can be a single URL string or an array of URLs.
- `goal` (required): The specific information goal for visiting the webpage(s).

**Behavior:**
- Fetches webpage content using Jina Reader API or direct fetch (based on configuration)
- Processes the content with an LLM to extract relevant information based on the goal
- Returns a structured summary with evidence and conclusions

**Use Cases:**
- When you need to extract specific information from a webpage
- When you want to understand how a webpage relates to a particular goal or question
- When you need summarized content rather than raw text

**Example:**
```json
{
  "url": "https://example.com/article",
  "goal": "Find information about climate change impacts"
}
```

### 2. fetch_url

**Purpose:** Fetch raw webpage content without LLM summarization.

**Parameters:**
- `url` (required): The URL of the webpage to fetch.

**Behavior:**
- Fetches webpage content using Jina Reader API or direct fetch (based on configuration)
- Removes HTML markup and extracts clean text
- Truncates content to a maximum length (configurable via `WEBCONTENT_MAXLENGTH`)
- Returns raw content without any LLM processing

**Use Cases:**
- When you need raw webpage content for further processing
- When you want to avoid LLM API costs or latency
- When you need to inspect full webpage content yourself

**Example:**
```json
{
  "url": "https://example.com/data"
}
```

### 3. browse

**Purpose:** Browse the web using search queries via Jina's search interface.

**Parameters:**
- `query` (required): The search query to find relevant webpage content.

**Behavior:**
- Uses Jina Search API to find relevant web content
- Returns query-related webpage content without requiring specific URLs
- Content is cleaned and truncated to a reasonable length

**Use Cases:**
- When you want to search for information without knowing specific URLs
- When you need to gather information from multiple sources about a topic
- When you want to explore web content related to a query

**Example:**
```json
{
  "query": "latest developments in artificial intelligence"
}
```

## Code Organization

The refactoring introduces a shared utilities module to avoid code duplication:

### File Structure

```
inference/
├── tool_visit.py          # Visit tool (with summarization)
├── tool_fetch_url.py      # Fetch URL tool (no summarization)
├── tool_browse.py         # Browse tool (search-based)
└── tool_visit_utils.py    # Shared utilities
```

### Shared Utilities (tool_visit_utils.py)

Common functions used by all three tools:

- `fetch_webpage_content(url)` - Fetch webpage content using configured method
- `direct_fetch_url(url)` - Direct HTTP fetch with anti-scraping headers
- `jina_readpage(url)` - Fetch content via Jina Reader API
- `jina_search(query)` - Search using Jina Search API
- `truncate_to_tokens(text, max_tokens)` - Truncate text to token limit
- `remove_text_links(text)` - Remove markdown links from text
- `get_domain(url)` - Extract domain from URL

## Configuration

### Environment Variables

- `USE_DIRECT_FETCH` (default: "false"): Use direct HTTP fetch instead of Jina
- `WEBCONTENT_MAXLENGTH` (default: 150000): Maximum content length in characters
- `ENABLE_SUMMARY` (default: "true"): Enable LLM summarization for visit tool
- `JINA_API_KEYS`: API key for Jina services

### Enabling Tools

Add the tools to your `.env` file:

```bash
ENABLED_TOOLS=search,visit,fetch_url,browse,google_scholar,PythonInterpreter,parse_file
```

## Migration Guide

### From Original visit Tool

If you were using the `visit` tool before, it continues to work exactly as before with no changes needed. The tool still requires both `url` and `goal` parameters.

### Using New Tools

**When to use fetch_url instead of visit:**
- You don't need LLM summarization
- You want to save on LLM API costs
- You need the full raw content
- You want faster response times

**When to use browse instead of visit:**
- You don't have specific URLs yet
- You want to search for information
- You need content from multiple sources about a topic

## Testing

Three test suites are available:

1. `tests/test_fetch_url.py` - Tests for fetch_url tool
2. `tests/test_browse.py` - Tests for browse tool
3. `tests/test_tool_separation.py` - Integration tests verifying tool separation

Run all tests:
```bash
python3 tests/test_fetch_url.py
python3 tests/test_browse.py
python3 tests/test_tool_separation.py
python3 tests/test_visit_basic.py  # Existing tests still pass
```

## Benefits of Refactoring

1. **Separation of Concerns**: Each tool has a single, clear responsibility
2. **Code Reusability**: Shared utilities eliminate duplication
3. **Flexibility**: Users can choose the appropriate tool for their needs
4. **Cost Optimization**: fetch_url and browse avoid unnecessary LLM calls
5. **Better Performance**: Direct content fetching when summarization isn't needed
6. **Clearer API**: Parameters make it obvious what each tool does
