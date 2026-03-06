# Interview Flashcards

## LLM Runtime Choice

**Q:** 为什么项目把 LLM 调用统一放在 `review_runtime.utils.llm.create_chat_completion()`？

**A:** 好处是统一 provider 接入点、环境变量解析和调用方式，`requirement_review_v1` 只关心 schema 和业务流程。代价是当前返回值仍以文本为主，trace 里更容易记录 `output_chars`，不直接携带标准化 token usage。

**Proof:** `review_runtime/utils/llm.py`、`requirement_review_v1/utils/llm_structured_call.py`。
