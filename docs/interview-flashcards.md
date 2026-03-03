# 面试背诵卡片 — 必背 20 题

> 基于 `requirement_review_v1/` 实现，A=后端/平台岗，B=大模型应用/Agent 岗

---

## A) 后端/平台岗必背 10 题

---

### A1

**Q:** 为什么选择线性串行五节点，而不是 DAG 并行？

**A(20s):** 五个节点数据依赖强，且 risk 和 reviewer 若并行，两者都写 trace 会互相覆盖，TypedDict 默认后写覆盖，需 `Annotated[dict, merge_dicts]`；V1 优先正确性，线性 trace 天然有序。

**A(60s):** 在 workflow.py 用 StateGraph 构建 parser→planner→risk→reviewer→reporter 线性链。Planner 等 parsed_items，Risk 等 tasks，Reviewer 等 Parser+Planner。risk 和 reviewer 理论上可并行但不做：两者都写 trace，默认 merge 会覆盖。V1 节点少、延迟可接受，线性收益是 trace 有序、排错简单，按 status 顺序看即可。

**Proof:** `requirement_review_v1/workflow.py` — `build_review_graph()`，`add_edge` 串行；`state.py` 中 `trace: dict` 无 `Annotated` 注解。

**Pitfall:** 追问「为什么 risk 和 reviewer 没做并行？」— 别说「没时间」，要说「两个节点都写 state['trace']，merge 会覆盖，需改 state 定义 reducer」。避免说「可以并行」却不解释为何没做。

---

### A2

**Q:** `ReviewState` 用了 `TypedDict(total=False)`，为什么？有什么工程意义？

**A(20s):** `total=False` 让所有字段可选，每个 Agent 只需 return 自己负责的字段做 partial update，LangGraph 做增量 merge；主流程 ainvoke 只传 requirement_doc 和 run_dir。

**A(60s):** 12 个字段若 total=True，每个 Agent 必须 return 全部 12 个否则 type checker 报错。total=False 解除限制。main.py 的 ainvoke 只传 requirement_doc 和 run_dir，其余 key 不存在，Agent 用 `.get("xxx", [])` 安全读取。新增字段不需要改已有 Agent。create_initial_state 只在 debug.py 用，主流程不依赖。

**Proof:** `requirement_review_v1/state.py` — `class ReviewState(TypedDict, total=False)`；`main.py` — `ainvoke({"requirement_doc": doc, "run_dir": out_dir})`。

**Pitfall:** 追问「state.get("trace", {}) 拿到什么？会 NPE 吗？」— 不会，key 不存在时 .get 返回默认值，空 dict。避免说「state 会报错」或「trace 是 None」。

---

### A3

**Q:** 每个 Agent 异常后返回空结果而不是终止 pipeline，为什么？

**A(20s):** try/except 捕获后返回空列表 + error trace，pipeline 能跑完，run_trace.json 里五个 agent 都有记录，成功标 ok、失败标 error 附 error_message，便于定位哪一步出问题。

**A(60s):** parser 的 except 返回 parsed_items: [] 和 trace；planner 发现 parsed_items 空时 early return 不调 LLM。和「条件边提前终止」对比：提前终止省空转但 trace 缺被跳过节点，当前设计是运行不贵、诊断信息更重要。

**Proof:** `parser_agent.py` — `except Exception` 返回 `{"parsed_items": [], "trace": trace}`；`planner_agent.py` — `if not parsed_items` 返回 `_empty_result(trace)`。输出：`run_trace.json` 含 parser/planner/risk/reviewer/reporter，每条约有 status、error_message。

**Pitfall:** 追问「真实排过什么问题？」— 举 parser 缺 parsed_items 为例：trace["parser"] 有 status="error"、error_message、raw_output_path，按 raw_output_path 看 raw 文件。避免说「没用过」或泛泛说「能看 trace」。

---

### A4

**Q:** trace 机制是怎么实现的？和 OpenTelemetry 有什么差距？

**A(20s):** `utils/trace.py` 定义 Span 类，四个 slot：agent_name、model、input_chars、_start_dt。trace_start() 开始，span.end() 返回 10 字段 dict 写入 state["trace"]，main 写到 run_trace.json。

**A(60s):** Span.end() 返回 start、end、duration_ms、model、status、input_chars、output_chars、prompt_version、raw_output_path、error_message。和 OTel 差距：无 Trace ID/Span ID/Parent、无 context propagation、无 Jaeger 导出，只能写 JSON。V1 单进程零依赖、代码少，够用。

**Proof:** `requirement_review_v1/utils/trace.py` — `Span`、`trace_start()`、`Span.end()`。输出：`run_trace.json` 结构为 `{"parser": {...}, "planner": {...}, ...}`，每条约 10 字段。

**Pitfall:** 追问「两次运行怎么区分？」— 按 outputs/<run_id>/ 目录区分，run_id 是时间戳；report.json 有 run_id 字段。避免说「有 Trace ID」或「混在一起」。

---

### A5

**Q:** `raw_agent_outputs` 只在失败时保存，正常成功的 LLM 输出不保存。为什么？

**A(20s):** 成功时结构化结果已在 state 中，raw 无额外诊断价值；失败时才需看 LLM 原始输出。调用只在 key 缺失或 except 分支，路径记在 trace 的 raw_output_path。

**A(60s):** 每个 Agent 里 save_raw_agent_output 守卫在 `if run_dir and raw` 后，出现在两处：JSON 解析后缺期望 key、except Exception。保存后绝对路径写入 trace.raw_output_path，最终进 run_trace.json。局限是无法做回归测试（无成功 raw baseline）。

**Proof:** `requirement_review_v1/utils/io.py` — `save_raw_agent_output()`；`parser_agent.py` — `if "parsed_items" not in parsed` 及 except 分支。输出：`run_trace.json` 对应 agent 的 `raw_output_path` 字段；文件在 `run_dir/raw_agent_outputs/<agent>.txt`。

**Pitfall:** 追问「LLM 正常返回但 JSON 缺 key，会保存 raw 吗？」— 会，缺 key 和异常都触发。避免说「只有异常才保存」。

---

### A6

**Q:** `report.json` 中 `report_data.update(result)` 把整个 state 合进去，有什么问题？

**A(20s):** final_report 和 parsed_items、review_results 等冗余，报告就是从这些拼的；state 若有和元信息同名 key 会覆盖 schema_version 等。

**A(60s):** 好处是自包含，单文件能还原全状态。隐患：final_report 已单独存 report.md，JSON 再存冗余；Agent 若 return "schema_version" 会覆盖元信息。改进可把元信息放 "meta" 下，或写入前 pop("final_report")。

**Proof:** `requirement_review_v1/main.py` — `report_data.update(result)` 后 `json.dump(report_data, f)`。输出：report.json 含 schema_version、run_id、model、provider、parsed_items、final_report 等。

**Pitfall:** 追问「为什么不删 final_report？」— 当前设计是自包含，没做 pop。避免说「已经删了」或「没冗余」。

---

### A7

**Q:** 为什么每个 Agent 都对 trace 做浅拷贝而不是直接修改？

**A(20s):** LangGraph 靠 node return 做 merge，直接改 state 引用框架无法区分「要更新」和「误改」；浅拷贝后 return 让框架做干净替换，trace 的 value 是 span.end() 的全新 dict，浅拷贝足够。

**A(60s):** 若 node 内部直接改 state["trace"]，框架不知道你改了什么，因为 merge 只看 return。必须 return {"trace": trace} 才生效。浅拷贝而非深拷贝：trace 每项是 span.end() 的新 dict，无嵌套共享。

**Proof:** `parser_agent.py` — `trace = dict(state.get("trace", {}))`，修改后 `return {..., "trace": trace}`。

**Pitfall:** 追问「直接改 state["trace"] 不 return 会更新吗？」— 不会，框架只看 return。避免说「可能会」「不确定」。

---

### A8

**Q:** Reporter 不调 LLM，纯确定性拼接。为什么这样设计？

**A(20s):** 输入已是 parsed_items、review_results、tasks 等结构化数据，不需要 LLM；确定性拼接保证格式稳定、无 JSON 解析失败、不耗 token。

**A(60s):** reporter_agent 注释写 "no LLM call — deterministic string concatenation"，用 _build_requirement_table、_build_task_table、_build_risk_register 等渲染 Markdown，trace 里 model 硬编码 "none"。若将来加 LLM 摘要，保留拼接逻辑、只在开头插 LLM 输出，失败时后面确定性部分仍完整。

**Proof:** `reporter_agent.py` — 注释 "V1: no LLM call"；`trace_start(_AGENT, model="none", ...)`；`_build_requirement_table` 等函数。输出：run_trace.json 中 reporter 的 model 为 "none"。

**Pitfall:** 追问「reporter 的 trace 和调 LLM 的 agent 有什么区别？」— 结构相同，model 为 "none"，无 raw_output_path，input_chars 是 structured 数据总字符数。避免说「没有 trace」或「字段不同」。

---

### A9

**Q:** `schema_version` 在代码里是怎么用的？有向后兼容机制吗？

**A(20s):** main.py 写入 "schema_version": "v1.1" 到 report.json，当前无 JSON Schema、无校验、无迁移，是预埋版本标记供下游兼容判断。prompt_version 在 trace 里硬编码 "v1.1"。

**A(60s):** schema_version 标输出格式，prompt_version 标 prompt 版本，两者都硬编码、无自动化联动。改 prompt 忘改版本号会脱节。改进可做 jsonschema 校验、prompt hash；兼容原则是 minor 只加字段不删，下游用 .get() 兼容。

**Proof:** `main.py` — `report_data["schema_version"] = "v1.1"`；`trace.py` — `_PROMPT_VERSION = "v1.1"`，span.end() 返回含 "prompt_version"。输出：report.json 有 schema_version；run_trace.json 每条有 prompt_version。

**Pitfall:** 追问「schema_version 和 prompt_version 是一个意思吗？」— 不是，前者在 report.json 标格式，后者在 trace 标 prompt。避免混为一谈。

---

### A10

**Q:** 如果 pipeline 跑到第四步 reviewer 才失败，前三步的 LLM 费用浪费了。如何断点恢复？当前做了吗？

**A(20s):** 当前未做。workflow.compile() 未传 checkpointer，无断点恢复。V1 需求规模小、重跑成本低。失败时 agent 返回 error 不抛异常，ainvoke 正常返回，report.json 含前三步 parsed_items、tasks、risks，可手动捞。

**A(60s):** 改进思路：compile(checkpointer=SqliteSaver(...))，ainvoke 传 thread_id，失败后用同一 thread_id 再调从断点继续。未实现原因：SQLite、恢复 CLI、thread_id 机制复杂度不划算。注意：失败时前三步结果在 report.json 里，因 agent 不抛异常、ainvoke 会返回。

**Proof:** `workflow.py` — `return workflow.compile()` 无 checkpointer 参数。输出：失败时 report.json 仍会写入（含 parser/planner/risk 结果），reviewer 对应 status="error"。

**Pitfall:** 追问「失败时前三步结果能捞出来吗？」— 能，在 report.json 里，因 agent 内部 try/except 不抛异常。避免说「捞不出来」「会丢」。

---

## B) 大模型应用/Agent 岗必背 10 题

---

### B1

**Q:** Prompt 里要求 "no markdown fences"，代码却用 `parse_json_markdown` 处理围栏，矛盾吗？

**A(20s):** 不矛盾，防御性工程。Prompt 降低 LLM 加围栏概率，parse_json_markdown 兜底；"信任但验证" 两层一起用。

**A(60s):** LLM 有强烈倾向加 ```json 围栏，prompt 禁止是第一层，parse_json_markdown 是第二层。若去掉 prompt，围栏概率大增但仍能解析；若去掉 parse_json_markdown，围栏会喂给 json_repair 可能导致失败。当前未记录「是否触发剥离」做监控。

**Proof:** `prompts.py` — "Respond with **valid JSON only** — no markdown fences, no commentary"；`parser_agent.py` — `parse_json_markdown(raw, parser=json_repair.loads)`。

**Pitfall:** 追问「当前有记录是否触发 markdown 剥离吗？」— 没有，trace 无此字段。避免说「有」或「可以监控」。

---

### B2

**Q:** JSON 解析用了 `parse_json_markdown` + `json_repair.loads` 双层容错，各自解决什么问题？

**A(20s):** parse_json_markdown 从围栏内提取 JSON 文本，json_repair 修语法错误（尾部逗号、未加引号、未转义换行等）；前者解决格式包装，后者解决内容损坏。

**A(60s):** parser 参数默认 parse_partial_json，这里显式传 json_repair.loads。流程：先检测 ```json...``` 提取内文，无围栏则整段当 JSON，再调用 json_repair 解析。盲区：语义类型错误如 "is_clear":"yes" 无法检测，需 Pydantic（当前未做）。

**Proof:** `parser_agent.py` — `parse_json_markdown(raw, parser=json_repair.loads)`；planner、risk、reviewer 同理。

**Pitfall:** 追问「"is_clear":"yes" 到 Python 是什么类型？」— str，json_repair 不转类型。_risk_level 里 `not "yes"` 碰巧和 `not True` 一致，但 `"false"` 会误判。避免说「会转成 bool」。

---

### B3

**Q:** 所有 Agent 都用 `temperature=0`，是否保证每次输出完全一致？

**A(20s):** 不能。temperature=0 选最高概率 token，但 GPU 非确定性、API batching、模型版本更新都会导致差异。严格可复现需 seed（当前未做）。

**A(60s):** 选 0 是因需要结构化 JSON、准确性和 schema 一致，不需要多样性。0.3 以上会增加「创造性发挥」。OpenAI 文档指出分布式推理和浮点精度下相同输入可能不同输出。trace 无 system_fingerprint 或 seed，无法从输出判断两次是否同版本。

**Proof:** `parser_agent.py` 等 — `create_chat_completion(..., temperature=0, ...)`。输出：trace 无 fingerprint、seed 字段。

**Pitfall:** 追问「trace 能看出两次是否一致吗？」— 不能，无 fingerprint。要验证只能手动跑两次对比 report.json。避免说「能看出来」。

---

### B4

**Q:** 如果 LLM 返回的 `is_clear` 是字符串 `"yes"` 或 `"false"` 而不是布尔值，系统能正确检测吗？

**A(20s):** 不能。无 schema 校验。`not "yes"` 碰巧等于 `not True`；`not "false"` 是 False（非空字符串 truthy），会把不清晰误判为清晰。

**A(60s):** _risk_level 用 `result.get("is_clear", True)` 直接布尔运算，json_repair 只修语法不修语义。隐藏 bug：`"false"` truthy → `not "false"` = False → 系统认为清晰。修复需 Pydantic 定义 is_clear: bool（当前未做）。

**Proof:** `reporter_agent.py` — `_risk_level()` 里 `not result.get("is_clear", True)`。输出：report.json 的 review_results 里 is_clear 可能为 str。

**Pitfall:** 追问「"yes" 会误判吗？」— "yes" 碰巧对，`not "yes"` = False；"false" 会错。避免只说「会」或「不会」，要分情况。

---

### B5

**Q:** `prompt_version` 硬编码为 "v1.1"，如果改了 prompt 忘更新版本号怎么办？

**A(20s):** 当前会脱节，_PROMPT_VERSION 和 prompts 内容无联动，靠人工维护。改进可算 prompt hash 写进 trace（当前未做）。

**A(60s):** 两次运行 trace 都标 prompt_version: v1.1 但实际 prompt 不同，输出差异分析会误导。自动化方案：prompts 算 SHA-256 前 8 位，trace 记 prompt_hash，CI 检查 hash 变但版本号未更新则阻止合并。当前未实现。

**Proof:** `trace.py` — `_PROMPT_VERSION = "v1.1"`。输出：run_trace.json 每条有 "prompt_version": "v1.1"。

**Pitfall:** 追问「能从 report.json/run_trace 发现 prompt 改过吗？」— 不能，只有 "v1.1" 无 hash。避免说「能发现」或「有 hash」。

---

### B6

**Q:** LLM 调用全部依赖 `gpt_researcher` 的 `create_chat_completion`，这个选择有什么利弊？

**A(20s):** 利：复用多 provider（OpenAI/Azure/Ollama），零成本。弊：返回 str 无 token usage，trace 只能记 output_chars；强耦合 gpt_researcher。

**A(60s):** 接受 model、messages、temperature、llm_provider、llm_kwargs，返回 str。内部封装 LangChain ChatModel 和多 provider 路由。劣势：无 token 数、无法直接控 max_tokens/seed（除非 llm_kwargs）、强耦合。解耦可抽象 LLMClient 接口（当前未做）。

**Proof:** `gpt_researcher/utils/llm.py` — `create_chat_completion()`；`parser_agent.py` 等调用。输出：trace 只有 output_chars，无 token 相关字段。

**Pitfall:** 追问「output_chars 和 token 数差多少？」— output_chars 是 len(raw) 字符数，token 约 1/4 字符（英文），中文更高。避免说「差不多」或「就是 token 数」。

---

### B7

**Q:** trace 里的 `output_chars` 是什么？和 token 数什么关系？

**A(20s):** `len(raw)`，即 LLM 返回字符串的字符数，不是 token 数。token 约字符数 1/4（英文），trace 无 token 字段。

**A(60s):** 各 agent 里 `span.end(output_chars=len(raw))`，raw 是 create_chat_completion 返回的 str。create_chat_completion 不返回 token usage，所以只能记字符数。估算 token 需除 4 或调用 API 的 usage 字段（当前未做）。

**Proof:** 各 agent — `span.end(..., output_chars=len(raw))`。输出：run_trace.json 每条约有 output_chars 字段。

**Pitfall:** 追问「能拿到精确 token 数吗？」— 不能，create_chat_completion 返回 str。避免说「能」或「output_chars 就是 token」。

---

### B8

**Q:** Parser、Planner、Reviewer 各自往 prompt 里塞什么？

**A(20s):** Parser 塞 requirement_doc，Planner 塞 parsed_items 的 JSON，Reviewer 塞 parsed_items + plan 的 JSON。

**A(60s):** Parser：PARSER_USER_PROMPT.format(requirement_doc=requirement_doc)；Planner：PLANNER_USER_PROMPT.format(items_json=json.dumps(parsed_items))；Reviewer：REVIEWER_USER_PROMPT.format(items_json=..., plan_json=...) 拼 parsed_items 和 tasks/milestones/estimation。三次全量分别是原始文档、parsed_items、parsed_items+plan。

**Proof:** `parser_agent.py` — `PARSER_USER_PROMPT.format(requirement_doc=...)`；`planner_agent.py` — `PLANNER_USER_PROMPT.format(items_json=items_json)`；`reviewer_agent.py` — `REVIEWER_USER_PROMPT.format(items_json=..., plan_json=...)`。

**Pitfall:** 追问「Planner 塞的是原始文档吗？」— 不是，塞的是 parsed_items 的 JSON。避免说「都是整份文档」。

---

### B9

**Q:** `run_trace.json` 的结构是什么？每条 agent 记录有哪些字段？

**A(20s):** 五 agent 为 key（parser/planner/risk/reviewer/reporter），每条约 10 字段：start、end、duration_ms、model、status、input_chars、output_chars、prompt_version、raw_output_path、error_message。

**A(60s):** main 写 `json.dump(result.get("trace", {}), f)`，trace 来自各 agent 的 span.end()。reporter 的 model 为 "none"，无 raw_output_path；其他 agent 的 model 来自 Config，失败时 raw_output_path 指向 raw 文件。

**Proof:** `main.py` — `json.dump(result.get("trace", {}), f)` 写到 run_trace.json；`trace.py` — `Span.end()` 返回的 dict 结构。

**Pitfall:** 追问「reporter 有 raw_output_path 吗？」— 一般不写，不调 LLM 无 raw。避免说「都有」或「结构不一样」。

---

### B10

**Q:** `report.json` 包含哪些核心字段？和 run_trace.json 有什么区别？

**A(20s):** 元信息：schema_version、run_id、model、provider、created_at；state：parsed_items、review_results、tasks、milestones、estimation、risks、plan_review、final_report 等。run_trace 是执行追踪，report 是完整 state 快照。

**A(60s):** report_data 先放元信息，再 update(result) 合并全 state，写入 report.json。一个文件能还原全状态。run_trace.json 只含 trace，即五 agent 的 duration、status、error_message 等，不含 parsed_items 等业务数据。

**Proof:** `main.py` — `report_data = {schema_version, run_id, ...}; report_data.update(result)`。输出：report.json 含上述字段；run_trace.json 仅 trace。

**Pitfall:** 追问「plan_review 是结构化计分吗？」— 不是，是 reviewer 的 LLM 自由文本评语，可能提到 coverage 等但不是代码层面的覆盖判定。避免说「有覆盖检查」「有结构化评分」。

---

*文档生成时间：2026-03-02*
*对应 interview-prep.md 必背 20 题*
