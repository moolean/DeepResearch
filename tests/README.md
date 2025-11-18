# API Availability Tests

This directory contains automated tests to verify that all required APIs are properly configured and accessible before running inference.

## Overview

The test suite checks the availability and configuration of all external services used by DeepResearch:

- **Search API** (`test_api_search.py`) - Google web search via Serper
- **Visit API** (`test_api_visit.py`) - Web page reading via Jina and summarization
- **Scholar API** (`test_api_scholar.py`) - Google Scholar search via Serper
- **Python Interpreter** (`test_api_python.py`) - Code execution sandbox via SandboxFusion
- **File Parser** (`test_api_file.py`) - Document parsing via Dashscope

## Usage

### Automatic Testing (Recommended)

Tests are automatically run when you execute the inference script:

```bash
bash inference/run_react_infer.sh
```

The tests will run before inference starts. If any test fails, the script will terminate with an error message.

### Manual Testing

You can also run the tests manually:

```bash
# Run all tests
python tests/run_api_tests.py

# Run individual tests
python tests/test_api_search.py
python tests/test_api_visit.py
python tests/test_api_scholar.py
python tests/test_api_python.py
python tests/test_api_file.py
```

## Test Behavior

Each test performs the following:

1. **Environment Check**: Verifies that required environment variables are set
2. **API Connectivity**: Makes a simple API call to verify the service is accessible
3. **Result Validation**: Checks that the API returns expected results
4. **Status Report**: Outputs clear PASS/FAIL status with helpful error messages

## Configuration

Tests respect the `ENABLED_TOOLS` setting in your `.env` file. Only tests for enabled tools will be run.

Example `.env` configuration:
```bash
# Only test search and visit APIs
ENABLED_TOOLS=search,visit
```

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed

## Common Issues

### SERPER_KEY_ID not configured
**Solution**: Get an API key from https://serper.dev/ and add it to your `.env` file

### JINA_API_KEYS not configured
**Solution**: Get an API key from https://jina.ai/ and add it to your `.env` file

### SANDBOX_FUSION_ENDPOINT not accessible
**Solution**: Ensure your sandbox endpoints are running and accessible. See https://github.com/bytedance/SandboxFusion

### DASHSCOPE_API_KEY invalid
**Solution**: Get an API key from https://dashscope.aliyun.com/ and add it to your `.env` file

### API_KEY/API_BASE not configured
**Solution**: Configure your OpenAI-compatible API endpoint in your `.env` file

## Adding New Tests

To add a test for a new API:

1. Create a new test file: `test_api_<name>.py`
2. Follow the pattern from existing tests
3. Update `run_api_tests.py` to include the new test
4. Add the tool-to-test mapping in `run_api_tests.py`

## Test Output

The test runner provides color-coded output:
- ✅ Green checkmarks indicate passed tests
- ❌ Red X marks indicate failed tests
- ⚠ Yellow warnings indicate configuration issues

Example output:
```
==================================================================
         DeepResearch API Availability Tests
==================================================================

✓ .env file found

Enabled tools: search, visit, google_scholar, PythonInterpreter, parse_file

Running 5 test(s)...

=== Testing Search API ===
✓ SERPER_KEY_ID is set
✓ Search API is accessible
✅ PASSED: Search API test successful

[... more tests ...]

==================================================================
              Test Results Summary
==================================================================

Tests Run: 5
Passed: 5
Failed: 0

Detailed Results:
  test_api_search: ✅ PASSED
  test_api_visit: ✅ PASSED
  test_api_scholar: ✅ PASSED
  test_api_python: ✅ PASSED
  test_api_file: ✅ PASSED

==================================================================
✅ ALL TESTS PASSED - Environment is ready!
==================================================================
```
