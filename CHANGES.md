# Changelog - Optimization Features

## Overview

This update adds three major optimization features to DeepResearch based on community feedback:

1. Support for sequential testing and inference
2. Remote API inference with configurable endpoints
3. Comprehensive environment-based configuration including tool selection and prompt customization

## New Features

### 1. Remote API Inference

You can now use remote API endpoints instead of running local VLLM servers:

```bash
# .env configuration
USE_REMOTE_API=true
INFERENCE_API_BASE=https://openrouter.ai/api/v1
INFERENCE_API_KEY=your_api_key
MODEL_PATH=alibaba/tongyi-deepresearch-30b-a3b
```

**Benefits:**
- No GPU required
- Use cloud-based inference services
- Easy integration with OpenRouter, Azure OpenAI, and other OpenAI-compatible APIs
- Automatic server startup skip when using remote mode

### 2. Tool Selection

Choose which tools are available during inference:

```bash
# Enable only specific tools
ENABLED_TOOLS=search,visit,PythonInterpreter
```

**Available Tools:**
- `search` - Google web search
- `visit` - Web page visiting and summarization
- `google_scholar` - Academic paper search
- `PythonInterpreter` - Python code execution
- `parse_file` - File parsing (PDF, DOCX, etc.)

**Benefits:**
- Reduce token usage by excluding unused tools
- Improve inference speed
- Focus agent on specific capabilities
- Dynamic system prompt generation based on enabled tools

### 3. Custom Prompts

Override default prompts with custom versions:

```bash
# Optional prompt customization
SYSTEM_PROMPT="Your custom system prompt..."
EXTRACTOR_PROMPT="Your custom extractor prompt..."
```

**Benefits:**
- Customize agent behavior for specific domains
- Adapt tone and style
- Support different languages
- Fine-tune for specific use cases

### 4. Enhanced Configuration

All inference parameters can now be configured via `.env`:

```bash
ROLLOUT_COUNT=3              # Number of inference rounds
TEMPERATURE=0.85             # Sampling temperature
PRESENCE_PENALTY=1.1         # Presence penalty
MAX_WORKERS=30               # Parallel workers
MAX_LLM_CALL_PER_RUN=100    # LLM call limit per run
```

## Configuration Files

### New Files

1. **`.env.remote_api_example`** - Ready-to-use example for remote API setup
2. **`CONFIGURATION_GUIDE.md`** - Comprehensive configuration documentation
3. **`CHANGES.md`** - This file

### Modified Files

1. **`.env.example`** - Updated with all new configuration options
2. **`inference/prompt.py`** - Dynamic prompt generation with tool filtering
3. **`inference/react_agent.py`** - Remote API support and tool initialization
4. **`inference/run_multi_react.py`** - Environment-based tool configuration
5. **`inference/run_react_infer.sh`** - Conditional server startup
6. **`README.md`** - Updated documentation

## Usage Examples

### Example 1: OpenRouter API

```bash
cp .env.remote_api_example .env
# Edit .env with your OpenRouter API key
bash inference/run_react_infer.sh
```

### Example 2: Local with Custom Tools

```bash
cp .env.example .env
# Edit .env:
# USE_REMOTE_API=false
# ENABLED_TOOLS=search,visit
bash inference/run_react_infer.sh
```

### Example 3: Research-Focused

```bash
# In .env:
ENABLED_TOOLS=search,google_scholar,visit
TEMPERATURE=0.7
ROLLOUT_COUNT=3
```

## Backward Compatibility

All changes are fully backward compatible:

- Existing configurations work without modification
- Default behavior unchanged when new features are not used
- Legacy variables (`SYSTEM_PROMPT`, `EXTRACTOR_PROMPT`) still available
- No breaking changes to existing scripts or APIs

## Migration Guide

### From Old Configuration Method

**Before:**
```bash
# Edit run_react_infer.sh directly
MODEL_PATH=/path/to/model
```

**After:**
```bash
# Configure via .env
echo "MODEL_PATH=/path/to/model" >> .env
```

### Enabling Remote API

**Before:**
```python
# Edit react_agent.py manually
openai_api_base = "http://custom-endpoint.com/v1"
```

**After:**
```bash
# Configure via .env
USE_REMOTE_API=true
INFERENCE_API_BASE=http://custom-endpoint.com/v1
```

## Testing

All features have been tested:

- ✅ Dynamic prompt generation with tool filtering
- ✅ Custom prompt overrides via environment
- ✅ Tool definition completeness
- ✅ Backward compatibility
- ✅ Environment variable parsing
- ✅ Remote API configuration
- ✅ Tool initialization

## Documentation

New documentation has been added:

1. **README.md** - Updated with feature documentation
2. **CONFIGURATION_GUIDE.md** - Detailed configuration guide with examples
3. **`.env.remote_api_example`** - Quick-start template
4. **CHANGES.md** - This changelog

## Support

For issues or questions:
- See [FAQ.md](./FAQ.md)
- Read [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md)
- Open an issue on GitHub
- Contact: yongjiang.jy@alibaba-inc.com

## Contributors

This feature was implemented to address community feedback and improve the usability and flexibility of DeepResearch.
