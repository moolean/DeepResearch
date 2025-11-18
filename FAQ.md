# Frequently Asked Questions (FAQ)

### Q: Where can I use Tongyi DeepResearch?

A: (1) **Local deployment:** You can follow the instructions in the [README](README.md#quick-start) to deploy the agent model locally.
(2) **Production service:** For a production-ready service, visit [bailian](https://bailian.console.aliyun.com/?spm=a2ty02.31808181.d_app-market.1.6c4974a1tFmoFc&tab=app#/app/app-market/deep-search/) and follow the guided setup.

### Q: Do you plan to release the training data?

A: We don’t plan to release the training data, but we have open-sourced the methods for synthesizing it in our series of papers.

### Q: Do you plan to release the Heavy Mode?

A: We’ve already open-sourced the code for ReAct inference in our papers. The Heavy Mode is not fully open-sourced yet, but we plan to release it in the future.

### Q: Why can I not reproduce the results in the paper?

A: The agent model was trained using specific prompts and tools. To reproduce the results, please make sure you’re using the same prompts and tools released in the codebase. We’re also working on developing a more general agent model.

### Q: How do I know if my APIs are configured correctly?

A: Run the API test suite before inference:
```bash
bash test_apis.sh
```

This will verify that all required APIs (search, visit, scholar, Python interpreter, file parser) are properly configured and accessible. If any test fails, you'll receive clear error messages indicating what needs to be fixed.

### Q: What should I do if API tests fail?

A: Each test provides specific guidance on fixing the issue:
- **SERPER_KEY_ID not configured**: Get a key from https://serper.dev/
- **JINA_API_KEYS not configured**: Get a key from https://jina.ai/
- **API_KEY/API_BASE not configured**: Configure your OpenAI-compatible API endpoint
- **SANDBOX_FUSION_ENDPOINT not accessible**: Ensure your sandbox endpoints are running (see https://github.com/bytedance/SandboxFusion)
- **DASHSCOPE_API_KEY invalid**: Get a key from https://dashscope.aliyun.com/

For more details, see the [tests/README.md](tests/README.md) documentation.

### Q: Can I skip the API tests?

A: The tests are automatically run when you execute `inference/run_react_infer.sh`. If you want to skip them temporarily (not recommended), you can remove the test runner script from the inference script. However, we strongly recommend fixing any configuration issues before running inference to avoid runtime errors.
