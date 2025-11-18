# Configuration Guide

This guide explains the new configuration features available in DeepResearch.

## Quick Start Examples

### Example 1: Using OpenRouter API

```bash
# Copy the remote API example configuration
cp .env.remote_api_example .env

# Edit .env and set your OpenRouter API key
# INFERENCE_API_KEY=your_actual_openrouter_key

# Run inference
bash inference/run_react_infer.sh
```

### Example 2: Using Local VLLM with Custom Tools

```bash
# Copy the standard example configuration
cp .env.example .env

# Edit .env and configure:
# USE_REMOTE_API=false
# ENABLED_TOOLS=search,visit  # Only enable search and visit tools
# MODEL_PATH=/path/to/your/model

# Run inference
bash inference/run_react_infer.sh
```

## Configuration Options

### 1. API Endpoint Configuration

Control where inference requests are sent:

| Variable | Description | Default |
|----------|-------------|---------|
| `USE_REMOTE_API` | Use remote API instead of local VLLM servers | `false` |
| `INFERENCE_API_BASE` | Base URL for the inference API | `http://127.0.0.1:6001/v1` |
| `INFERENCE_API_KEY` | API key for authentication | `EMPTY` |
| `USE_OPENAI_MIDDLEWARE` | Use requests-based middleware instead of openai library | `false` |

**Use Case**: Run inference without GPUs by using services like OpenRouter, Azure OpenAI, or other OpenAI-compatible APIs.

**OpenAI Middleware**: Set `USE_OPENAI_MIDDLEWARE=true` to use a lightweight requests-based HTTP client instead of the openai library. This middleware:
- Mimics the OpenAI client interface (client.chat.completions.create)
- Uses the `requests` library for HTTP calls instead of the openai SDK
- Maintains full compatibility with existing code
- Useful for custom API endpoints or debugging network requests

### 2. Tool Selection

Choose which tools are available during inference:

| Variable | Description | Default |
|----------|-------------|---------|
| `ENABLED_TOOLS` | Comma-separated list of enabled tools | `search,visit,google_scholar,PythonInterpreter,parse_file` |

**Available Tools**:
- `search`: Google web search
- `visit`: Web page visiting and summarization
- `google_scholar`: Academic paper search via Google Scholar
- `PythonInterpreter`: Python code execution sandbox
- `parse_file`: Parse uploaded files (PDF, DOCX, PPTX, etc.)

**Use Case**: Improve inference speed and focus by enabling only the tools needed for your use case.

**Example**:
```bash
# Only enable search and visit for web-focused tasks
ENABLED_TOOLS=search,visit

# Enable all tools except file parsing
ENABLED_TOOLS=search,visit,google_scholar,PythonInterpreter
```

### 3. Prompt Customization

Override default prompts with custom versions:

| Variable | Description | Default |
|----------|-------------|---------|
| `SYSTEM_PROMPT` | Custom system prompt for the agent | Built-in default |
| `EXTRACTOR_PROMPT` | Custom prompt for information extraction | Built-in default |

**Use Case**: Customize the agent's behavior, tone, or instruction format for specific domains or languages.

**Example**:
```bash
# In .env file
SYSTEM_PROMPT="You are a medical research assistant specialized in analyzing clinical trials..."
```

**Note**: When using custom system prompts, make sure to include tool definitions if you want the agent to use tools. The default prompt includes tool definitions automatically.

### 4. Inference Parameters

Control inference behavior:

| Variable | Description | Default |
|----------|-------------|---------|
| `ROLLOUT_COUNT` | Number of inference rounds to run | `3` |
| `TEMPERATURE` | Sampling temperature (0.0-2.0) | `0.85` |
| `PRESENCE_PENALTY` | Presence penalty for generation | `1.1` |
| `MAX_WORKERS` | Maximum parallel workers | `30` |
| `MAX_LLM_CALL_PER_RUN` | Maximum LLM calls per inference run | `100` |

**Use Case**: Tune inference quality, speed, and resource usage.

### 5. Model Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `MODEL_PATH` | Path to model weights or model identifier | `/your/model/path` |
| `DATASET` | Path to evaluation dataset | `your_dataset_name` |
| `OUTPUT_PATH` | Directory for saving results | `/your/output/path` |

## Common Configurations

### Configuration 1: Cost-Effective Cloud Inference

For budget-conscious users who want to use cloud APIs:

```bash
USE_REMOTE_API=true
INFERENCE_API_BASE=https://openrouter.ai/api/v1
INFERENCE_API_KEY=your_key
MODEL_PATH=alibaba/tongyi-deepresearch-30b-a3b
ENABLED_TOOLS=search,visit
MAX_LLM_CALL_PER_RUN=50
ROLLOUT_COUNT=1
```

### Configuration 2: High-Performance Local Inference

For users with local GPU resources:

```bash
USE_REMOTE_API=false
MODEL_PATH=/path/to/local/model
ENABLED_TOOLS=search,visit,google_scholar,PythonInterpreter,parse_file
MAX_WORKERS=30
ROLLOUT_COUNT=3
```

### Configuration 3: Research-Focused Configuration

For academic research with scholar search:

```bash
ENABLED_TOOLS=search,google_scholar,visit
ROLLOUT_COUNT=3
TEMPERATURE=0.7  # Lower temperature for more consistent results
```

### Configuration 4: Code-Focused Configuration

For tasks requiring code execution:

```bash
ENABLED_TOOLS=search,visit,PythonInterpreter
SANDBOX_FUSION_ENDPOINT=your_sandbox_endpoint
```

## Troubleshooting

### Issue: Remote API not working

**Check**:
1. Is `USE_REMOTE_API=true`?
2. Is `INFERENCE_API_BASE` correct?
3. Is `INFERENCE_API_KEY` valid?
4. Does the model name in `MODEL_PATH` match the API's expected format?

### Issue: Tools not working as expected

**Check**:
1. Is the tool name spelled correctly in `ENABLED_TOOLS`?
2. Are required API keys configured (e.g., `SERPER_KEY_ID` for search)?
3. Check the console output for tool initialization messages

### Issue: Local servers not starting

**Check**:
1. Is `USE_REMOTE_API=false`?
2. Is `MODEL_PATH` pointing to a valid local model?
3. Are GPUs available and configured correctly?
4. Check CUDA and VLLM installation

## Migration from Old Configuration

If you're upgrading from a previous version:

1. **Old way**: Modify `run_react_infer.sh` directly
2. **New way**: Configure via `.env` file

**Benefits**:
- Easier configuration management
- No need to modify shell scripts
- Supports remote API inference
- Better tool selection control

**Backward Compatibility**: All old configurations still work. The new features are additive.

## Result File Format

The evaluation results are stored in JSONL format (one JSON object per line). Each result entry includes:

- `question`: The input question
- `answer`: The expected answer
- `messages`: Full conversation history with the agent
- `prediction`: The agent's final answer
- `termination`: How the inference ended (e.g., 'answer', 'timeout', 'token limit reached')
- **`tools`**: Dictionary of tool definitions that were actually used during inference

### Tools Dictionary

The `tools` field contains the complete OpenAI-format definitions for each tool that was called during the inference run. This allows you to:
- Track which tools were used for each question
- Analyze tool usage patterns across your dataset
- Reproduce tool configurations for specific queries
- Debug tool-related issues

Example:
```json
{
  "question": "What is the weather in Paris?",
  "prediction": "The weather in Paris is...",
  "tools": {
    "search": {
      "type": "function",
      "function": {
        "name": "search",
        "description": "Perform Google web searches...",
        "parameters": {...}
      }
    },
    "visit": {
      "type": "function",
      "function": {
        "name": "visit",
        "description": "Visit webpage(s)...",
        "parameters": {...}
      }
    }
  }
}
```

## Best Practices

1. **Keep `.env` in `.gitignore`**: Never commit API keys to version control
2. **Use `.env.example` as template**: Copy and modify rather than editing directly
3. **Start with defaults**: Use default settings first, then tune as needed
4. **Enable only needed tools**: Reduce token usage and improve focus
5. **Monitor token usage**: Use `MAX_LLM_CALL_PER_RUN` to control costs
6. **Analyze tool usage**: Use the `tools` field in results to understand which tools are most valuable

## Support

For issues or questions:
- Check [FAQ.md](./FAQ.md)
- Open an issue on GitHub
- Contact: yongjiang.jy@alibaba-inc.com
