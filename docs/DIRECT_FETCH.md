# Direct URL Fetch Feature

## Overview

The `visit` tool now supports direct URL fetching as an alternative to using the Jina API. This feature allows you to fetch and extract web page content directly using `httpx` and `trafilatura`, which can be useful for:

- Avoiding API rate limits
- Reducing external API dependencies
- Custom content extraction requirements
- Working with sites that are accessible without third-party services

## Configuration

### Enable Direct Fetch

To enable direct URL fetching, set the `USE_DIRECT_FETCH` environment variable in your `.env` file:

```bash
# Enable direct URL fetching (bypasses Jina API)
# Set to true to fetch URLs directly using httpx instead of Jina
# Default: false (uses Jina API)
USE_DIRECT_FETCH=true
```

### Dependencies

The direct fetch feature requires the following Python packages:

- `httpx` - HTTP client with HTTP/2 support (already in requirements.txt)
- `h2` - HTTP/2 support for httpx
- `trafilatura` - Web content extraction

These are automatically installed when you run:

```bash
pip install -r requirements.txt
```

If you need to install them separately:

```bash
pip install httpx h2 trafilatura
```

## Features

The direct fetch implementation includes:

### 1. Robust Retry Logic
- 3 retry attempts by default
- Exponential backoff between retries
- Intelligent retry decisions based on error type

### 2. Anti-Scraping Protection
- Comprehensive browser-like headers
- User-Agent spoofing
- Referer header simulation
- Accept-Language and encoding headers

### 3. SSL/TLS Handling
- Custom SSL context for legacy servers
- Support for self-signed certificates
- Legacy renegotiation support

### 4. HTTP/2 Support
- Modern HTTP/2 protocol support
- Automatic fallback to HTTP/1.1
- Improved performance for modern sites

### 5. Smart Error Handling
- **404 errors**: No retry, immediate failure
- **403 errors**: Retry with backoff (anti-bot detection)
- **5xx errors**: Retry (server errors)
- **Timeout errors**: Retry with increased wait
- **Network errors**: Retry with backoff

### 6. Content Extraction
- Uses `trafilatura` for clean text extraction
- Removes HTML tags, scripts, and styles
- Extracts main content only
- Fast extraction mode enabled

## Usage

### Basic Usage

Once enabled, the direct fetch works transparently:

```python
from tool_visit import Visit

visit = Visit()

# This will use direct fetch if USE_DIRECT_FETCH=true
result = visit.call({
    "url": "https://example.com",
    "goal": "Extract information about the website"
})
```

### Programmatic Usage

You can also use the direct fetch methods directly:

```python
from tool_visit import Visit
import asyncio

visit = Visit()

# Async method
async def fetch_url():
    text, error = await visit.direct_fetch_url("https://example.com")
    if text:
        print(f"Successfully fetched: {text[:200]}")
    else:
        print(f"Failed: {error}")

# Sync wrapper
text, error = visit.direct_fetch_url_sync("https://example.com")
if text:
    print(f"Successfully fetched: {text[:200]}")
else:
    print(f"Failed: {error}")
```

## Error Messages

The direct fetch returns detailed error messages:

- **HTTP 403**: "Access denied (HTTP 403). The website is blocking automated requests..."
- **HTTP 404**: "Page not found (HTTP 404). The URL does not exist."
- **HTTP 5xx**: "Server error (HTTP 5xx). The website is experiencing issues..."
- **Timeout**: "Request timeout. The website took too long to respond..."
- **Network Error**: "Network error: [detailed error message]"
- **Empty Content**: "Could not extract readable content from the page..."

## Comparison: Jina API vs Direct Fetch

| Feature | Jina API | Direct Fetch |
|---------|----------|--------------|
| Setup | Requires API key | No API key needed |
| Rate Limits | Subject to API limits | No limits (respect robots.txt) |
| Cost | Pay per request | Free (hosting costs only) |
| Anti-Scraping | Handled by Jina | Custom headers + retry logic |
| JavaScript | Supported | Not supported |
| Content Quality | Optimized extraction | Basic extraction |
| Reliability | High (managed service) | Depends on implementation |
| Speed | Network latency | Direct connection |

## Best Practices

### 1. Choose the Right Mode

- **Use Jina API when**:
  - Working with JavaScript-heavy sites
  - Need consistent, high-quality extraction
  - Don't want to manage anti-scraping
  - Have budget for API calls

- **Use Direct Fetch when**:
  - Working with simple HTML sites
  - Need to avoid API limits
  - Want to minimize external dependencies
  - Have custom extraction needs

### 2. Respect Websites

When using direct fetch:
- Always respect `robots.txt`
- Add appropriate delays between requests
- Use reasonable retry logic
- Identify your bot properly in User-Agent

### 3. Handle Errors Gracefully

```python
text, error = visit.direct_fetch_url_sync(url)

if error:
    if "403" in error:
        # Site is blocking, consider using Jina or waiting
        pass
    elif "404" in error:
        # URL doesn't exist, no need to retry
        pass
    else:
        # Other error, log and handle appropriately
        pass
```

## Testing

Run the tests to verify the direct fetch feature:

```bash
# Test dependencies
python tests/test_api_visit.py

# Run unit tests
python tests/test_direct_fetch_unit.py
```

## Troubleshooting

### Issue: "trafilatura is not installed"

**Solution**: Install trafilatura:
```bash
pip install trafilatura
```

### Issue: "h2 package is not installed"

**Solution**: Install h2 for HTTP/2 support:
```bash
pip install h2
```

### Issue: "Access denied (HTTP 403)"

**Possible causes**:
- Website has anti-bot protection
- IP address is blocked
- Too many requests too quickly

**Solutions**:
1. Add delays between requests
2. Use different IP/proxy
3. Fall back to Jina API
4. Contact website owner for API access

### Issue: "Could not extract readable content"

**Possible causes**:
- JavaScript-rendered content
- Non-HTML content (PDF, images, etc.)
- Complex page structure

**Solutions**:
1. Use Jina API instead (handles JS)
2. Check if URL is correct
3. Try a different URL

## Performance Considerations

### Memory Usage
- Direct fetch uses less memory than Jina API
- Trafilatura extraction is memory-efficient

### Speed
- Direct fetch is typically faster for simple pages
- Network latency is the main factor
- HTTP/2 provides performance benefits

### Concurrency
- The current implementation doesn't include parallel fetching
- For multiple URLs, consider implementing your own concurrency
- Be mindful of rate limiting when fetching many URLs

## Future Enhancements

Potential improvements for the direct fetch feature:

1. **JavaScript Support**: Add headless browser support for JS-heavy sites
2. **Proxy Support**: Add proxy configuration for better anti-scraping
3. **Caching**: Implement response caching to reduce duplicate requests
4. **Rate Limiting**: Add configurable rate limiting
5. **Custom Extractors**: Support for custom extraction rules
6. **Async Batch Fetching**: Parallel fetching of multiple URLs

## Contributing

If you encounter issues or have suggestions for the direct fetch feature, please open an issue on GitHub with:

1. Your environment configuration
2. The URL you're trying to fetch
3. Error messages or unexpected behavior
4. Steps to reproduce

## References

- [httpx documentation](https://www.python-httpx.org/)
- [trafilatura documentation](https://trafilatura.readthedocs.io/)
- [HTTP/2 specification](https://httpwg.org/specs/rfc7540.html)
- [robots.txt specification](https://www.robotstxt.org/)
