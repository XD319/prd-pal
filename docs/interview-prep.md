# Multi-Agent 需求评审系统 — 面试高频题精选

> 基于 `requirement_review_v1/` 真实代码实现，覆盖校招技术面 + 大模型应用岗两条线。

---

## 第一部分：校招技术面试 Top 12

---

### 1. 为什么选择线性串行五节点，而不是 DAG 并行？

**30s 精简版：**
五个节点之间存在强数据依赖——Planner 要等 Parser 的 `parsed_items`，Risk 要等 Planner 的 `tasks`，Reviewer 要等 Parser 和 Planner 的输出。线性结构最简单、最易调试，V1 阶段优先保证正确性。

**60s 加分版：**
在 `workflow.py` 中用 LangGraph 的 `StateGraph` 构建了 parser→planner→risk→reviewer→reporter 的线性链。虽然从数据依赖看 risk 和 reviewer 理论上可以在 planner 之后并行（两者互不消费对方输出），但并行会引入 state 合并问题——两个节点都写 `trace` 字段，`TypedDict` 默认是后写覆盖，需要改用 `Annotated[dict, merge_dicts]` 的 reducer。V1 阶段节点少、延迟可接受，线性结构的收益是 trace 天然有序，排错时只需顺序看每个 agent 的 `status` 字段。未来如果增加更多 Agent 或需求量变大，可以引入 fan-out/fan-in 结构。

---

### 2. `ReviewState` 用了 `TypedDict(total=False)`，为什么？有什么工程意义？

**30s 精简版：**
`total=False` 让所有字段都可选，每个 Agent 只需 return 自己负责的字段作为 partial update，不需要每次都返回完整 state。这样 LangGraph 做增量 merge 就行了。

**60s 加分版：**
在 `state.py` 中 `ReviewState` 定义了 12 个字段。如果用默认的 `total=True`，每个 Agent 的 return dict 必须包含所有 12 个字段，否则 type checker 会报错。`total=False` 解除了这个限制。实际上 `main.py` 的 `ainvoke` 只传了 `requirement_doc` 和 `run_dir` 两个字段，其余字段在 state 中根本不存在（不是 None，是 key 不存在），每个 Agent 用 `.get("xxx", [])` 做安全读取。这种模式的好处是：新增一个字段不需要改任何已有 Agent——只要它们不读取这个字段。`create_initial_state()` 函数提供了一个全字段初始化的入口，但只在 `debug.py` 中被使用，主流程不依赖它。

---

### 3. 每个 Agent 异常后返回空结果而不是终止 pipeline，为什么？

**30s 精简版：**
每个 Agent 内部 try/except 捕获所有异常，返回空列表 + error trace。这样 pipeline 一定能跑完，trace 中能看到所有节点的状态，便于定位"到底哪一步出了问题"。

**60s 加分版：**
以 `parser_agent.py` 为例，第 75-83 行 `except Exception as exc` 捕获后，返回 `{"parsed_items": [], "trace": trace}`。后续的 planner 发现 `parsed_items` 为空时，也不调 LLM，直接返回空结果。这样一次运行的 `run_trace.json` 中始终有五个 agent 的记录——成功的标 `"ok"`，失败的标 `"error"` 并附带 `error_message`。和"条件边提前终止"方案对比：提前终止节省了空转开销，但 trace 中会缺少被跳过节点的记录，不利于构建"pipeline 健康度看板"。当前设计的思路是——运行不贵（空转不调 LLM），诊断信息更重要。

---

### 4. trace 机制是怎么实现的？和 OpenTelemetry 有什么差距？

**30s 精简版：**
`utils/trace.py` 中定义了 `Span` 类，记录开始时间、结束时间、耗时、模型、状态、输入输出规模等。每个 Agent 调用 `trace_start()` 开始计时，完成后调用 `span.end()` 输出 trace dict，追加到全局 `state["trace"]` 中。

**60s 加分版：**
`Span` 有四个 slot：`agent_name`、`model`、`input_chars`、`_start_dt`。`end()` 计算 `duration_ms = (end - start) * 1000`，返回包含 9 个字段的 dict。和 OpenTelemetry 相比，缺少三个核心能力：一是没有 Span ID / Trace ID / Parent Span，无法表达"一次 pipeline 是父 span、五个 agent 是子 span"的层级关系；二是没有 context propagation，无法跨服务追踪；三是没有导出能力，只能写 JSON 文件，不能接入 Jaeger 等可视化工具。但在 V1 单进程低频场景下，自建 Span 零外部依赖、代码量极少，是合理的工程权衡。

---

### 5. `raw_agent_outputs` 只在失败时保存，正常成功的 LLM 输出不保存。为什么？

**30s 精简版：**
`utils/io.py` 的 `save_raw_agent_output` 只在 JSON key 缺失或异常时被调用。正常路径只记录 `output_chars`。设计意图是——成功时结构化结果已保存在 state 中，原始文本没有额外诊断价值；失败时才需要看 LLM 到底输出了什么。

**60s 加分版：**
在每个 Agent 中，`save_raw_agent_output` 的调用被守卫在 `if run_dir and raw` 条件后面，只出现在两处：一是 JSON 解析后缺少期望 key 的分支，二是 `except Exception` 分支。保存后的绝对路径记录在 trace 的 `raw_output_path` 字段中。这个设计的局限是无法做回归测试——没有成功运行的 raw baseline。改进方案是加一个 `SAVE_RAW_OUTPUT=always|error_only` 环境变量控制策略，默认维持 `error_only`，需要调试或回归时切换为 `always`。实现上只需在成功路径也加一行 `save_raw_agent_output` 调用。

---

### 6. `report.json` 中 `report_data.update(result)` 把整个 state 合进去，有什么问题？

**30s 精简版：**
`final_report` 这个很长的 Markdown 字符串和 `parsed_items`、`review_results` 等结构化数据存在完全冗余——报告就是从这些字段拼出来的。会导致 JSON 文件体积膨胀。

**60s 加分版：**
`main.py` 第 68 行的 `update` 把全部 state 字段和元信息（`schema_version`、`run_id`、`model`）合并成一个 dict 写入 `report.json`。好处是自包含——拿到这一个文件就能还原所有状态。但有两个隐患：一是 `final_report` 已经单独存了 `report.md`，JSON 中再存一份是冗余；二是如果 state 中出现和元信息同名的 key（比如某个 Agent 不小心 return 了 `"schema_version": xxx`），`update` 会覆盖元信息。改进方式是把元信息嵌套在 `"meta"` key 下，或者在写入时排除 `final_report` 字段。

---

### 7. 为什么每个 Agent 都对 trace 做浅拷贝而不是直接修改？

**30s 精简版：**
`dict(state.get("trace", {}))` 创建了一个新 dict。如果直接修改 `state["trace"]`，是在原地 mutate LangGraph 管理的 state 对象，可能干扰框架的 diff 检测机制，将来改并行还会产生竞态条件。

**60s 加分版：**
LangGraph 的 state 更新模型是"每个 node return partial dict → 框架 merge"。如果 node 内部直接修改 state 引用，框架无法区分"这个字段是你 return 出来要更新的"还是"你只是读着玩儿不小心改了"。浅拷贝确保每个 Agent 操作的是独立副本，return 时让框架做干净的替换。浅拷贝而不是深拷贝足够了——因为 trace 中每个 agent 的 value 是 `span.end()` 返回的全新 dict，不存在嵌套引用共享问题。

---

### 8. Reporter 不调 LLM，纯确定性拼接。为什么这样设计？

**30s 精简版：**
Reporter 的输入是完全结构化的（`parsed_items`、`review_results`、`tasks` 等 dict/list），不需要 LLM 的理解能力。确定性拼接保证输出格式稳定、不会有 JSON 解析失败的风险、不消耗 token。

**60s 加分版：**
`reporter_agent.py` 注释明确写了"V1: no LLM call — the report is built by deterministic string concatenation"。它用 `_build_requirement_table`、`_build_task_table`、`_build_risk_register` 等辅助函数将结构化数据渲染为 Markdown 表格。trace 中 `model` 硬编码为 `"none"`。如果将来想让 LLM 生成 Executive Summary，最安全的方式是保留当前拼接逻辑不动，只在报告开头插入一段 LLM 生成的摘要——这样即使 LLM 失败，后面的确定性部分仍然完整。这是"LLM 增强但不依赖"的工程原则。

---

### 9. `schema_version` 在代码里是怎么用的？有向后兼容机制吗？

**30s 精简版：**
`main.py` 写入 `"schema_version": "v1.1"` 到 `report.json`，但当前没有对应的 JSON Schema 文件、没有校验逻辑、也没有迁移代码。它是一个预埋的版本标记，供未来下游消费者做兼容判断。

**60s 加分版：**
这个版本号配合 `prompt_version`（`trace.py` 中硬编码的 `"v1.1"`）构成了两层版本追踪——前者标记输出格式，后者标记 prompt 模板版本。当前的局限是两者都靠开发者手动维护，如果改了 prompt 但忘了更新版本号就会脱节。改进方向：给 output schema 维护一份 JSON Schema 定义文件，写入时做 `jsonschema.validate`；给 prompt 算内容 hash 自动关联版本。遵循的兼容原则应该是"minor 版本只加字段不删字段"，让旧版消费者用 `.get()` 加默认值兼容新字段。

---

### 10. 如果 pipeline 跑到第四步 reviewer 才失败，前三步的 LLM 费用浪费了。如何断点恢复？

**30s 精简版：**
当前 `workflow.compile()` 没有传 checkpointer，中间状态不持久化。LangGraph 本身支持 `SqliteSaver` 等 checkpointer，加上后每个节点执行完自动存快照，失败后可以从断点恢复。

**60s 加分版：**
改动很小：`workflow.compile(checkpointer=SqliteSaver("checkpoint.db"))`，然后 `ainvoke` 时传 `config={"configurable": {"thread_id": run_id}}`。框架会在每个节点后保存全量 state。失败后用相同 `thread_id` 再次调用 `ainvoke(None, config=...)` 就能从上次中断的节点继续。当前不使用的原因是 V1 场景——需求文档通常不大，四次 LLM 调用总花费几毛钱，从头重跑的成本远低于引入 checkpoint 的工程复杂度（SQLite 文件管理、恢复 CLI、thread_id 机制）。可以把 checkpoint 文件也存到 `outputs/<run_id>/` 下和报告一起归档。

---

### 11. 如果需求规模从 10 条扩展到 200 条，当前架构会遇到什么瓶颈？

**30s 精简版：**
Parser 把整份文档一次性塞进 prompt，200 条需求可能超过上下文窗口。后续 Planner 和 Reviewer 又全量灌入 `parsed_items`，三次全量传入加剧 token 消耗和注意力衰减问题。

**60s 加分版：**
三个瓶颈：一是 token 限制——200 条需求的 `parsed_items` 序列化后可能超过 50K tokens，Planner 和 Reviewer 的 prompt 加上 system prompt 可能逼近 128K 上下文窗口；二是质量衰减——LLM 对长输入末尾的注意力下降，容易漏掉靠后的需求；三是延迟——四次 LLM 调用，每次处理长文本，端到端可能超过 5 分钟。解决方案是在 parser 之后加分片调度节点，按 20 条一组拆 batch，对每组独立跑 planner→risk→reviewer 的子图，最后用聚合节点合并所有 batch 的 tasks、risks、review_results。

---

### 12. 如何从 CLI 工具升级为多人使用的 Web 服务？

**30s 精简版：**
用 FastAPI 包裹 `build_review_graph()`，暴露 `POST /api/v1/review` 接口。graph 执行放后台任务（Celery/BackgroundTasks），用 run_id 查询结果。`outputs/` 迁移到 S3。现有 workflow、agents、prompts 模块完全不需要改。

**60s 加分版：**
分三层改造。API 层：FastAPI + `POST /review`（提交）+ `GET /review/{run_id}`（查询），graph 执行放入 Celery worker 避免 HTTP 超时。存储层：`save_raw_agent_output` 和 `main.py` 的文件写入改为 S3 客户端，`run_dir` 变为 `s3://bucket/user_id/run_id/`。多租户：state 增加 `user_id`，API key 从用户数据库读取而非环境变量。核心优势：当前的 state-driven 架构天然适合这种升级——`workflow.py`、五个 agent、`prompts.py`、`trace.py` 一行不改，只需要在入口层做适配。

---

## 第二部分：大模型应用岗 Top 8

---

### 1. Prompt 里要求"no markdown fences"，代码却用 `parse_json_markdown` 处理围栏，矛盾吗？

**30s 精简版：**
不矛盾，是防御性工程。Prompt 约束降低 LLM 加围栏的概率，`parse_json_markdown` 兜底处理万一加了围栏的情况。"信任但验证"——两层一起用最稳健。

**60s 加分版：**
LLM（尤其 GPT-4/Claude）有强烈倾向给 JSON 加 ` ```json ` 围栏，即使 prompt 明确禁止。Prompt 中的指令是第一层防线——降低发生概率；`parse_json_markdown` 是第二层——即使发生了也能正确提取。如果去掉 prompt 约束，围栏出现概率大增但仍能解析；如果去掉 `parse_json_markdown`，一旦 LLM 加了围栏，`json_repair.loads` 可能无法处理前导的 ` ```json\n ` 文本。可以在 trace 中记录"是否触发了 markdown 剥离"，作为 prompt 遵从率的监控指标。

---

### 2. JSON 解析用了 `parse_json_markdown` + `json_repair.loads` 双层容错，各自解决什么问题？

**30s 精简版：**
`parse_json_markdown` 从 Markdown 代码围栏中提取 JSON 文本；`json_repair.loads` 修复 JSON 语法错误（尾部逗号、单引号、缺失括号）。前者解决格式包装问题，后者解决内容损坏问题。

**60s 加分版：**
两层是串联关系。`parse_json_markdown` 的 `parser` 参数接受一个可调用对象，默认是 `json.loads`，这里被替换成了 `json_repair.loads`。执行流程：先用正则检测 ` ```json...``` ` 围栏并提取内部文本；如果没有围栏则把整个 raw 当作 JSON；然后调用 `json_repair.loads` 解析。`json_repair` 能处理 LLM 常见的格式错误——尾部多余逗号、属性名未加双引号、字符串内未转义的换行等。两层结合把"LLM 输出 → Python dict"的成功率从约 85%（纯 `json.loads`）提升到接近 99%。但仍有盲区：语义层面的类型错误（如 `"is_clear": "yes"` 代替 `true`）无法被检测到，需要引入 Pydantic schema validation。

---

### 3. 所有 Agent 都用 `temperature=0`，是否保证每次输出完全一致？

**30s 精简版：**
不是。`temperature=0` 让模型选概率最高的 token，但 GPU 浮点运算的非确定性、API 端 batching 差异、模型版本更新都可能导致微小差异。严格可复现需要额外加 `seed` 参数。

**60s 加分版：**
选择 `temperature=0` 的原因是这个场景需要结构化 JSON 输出，要求准确性和 schema 一致性，不需要多样性。0.3 以上会增加 LLM "创造性发挥"的概率——比如擅自调整 JSON 结构或添加额外字段。但 `temperature=0` 不等于确定性：OpenAI 文档指出由于分布式推理和浮点精度问题，相同输入可能产生不同输出。如果需要严格可复现（比如回归测试），应该加 `seed` 参数并在 trace 中记录返回的 `system_fingerprint`，当 fingerprint 变化时标记为"模型更新，结果可能不一致"。

---

### 4. 如果 LLM 返回的 `is_clear` 是字符串 `"yes"` 而不是布尔值 `true`，系统能检测到吗？

**30s 精简版：**
不能。代码没有 schema validation。而且 Python 中 `not "yes"` 等于 `False`（和 `not True` 一致），碰巧结果正确。但如果返回 `"false"` 字符串，`not "false"` 还是 `False`（非空字符串 truthy），和期望的 `not False = True` 完全相反——会把不清晰的需求误判为清晰。

**60s 加分版：**
`reporter_agent.py` 的 `_risk_level` 函数用 `result.get("is_clear", True)` 读取后直接做布尔运算。当前没有任何类型校验层——`json_repair` 修复语法错误但不修复语义类型偏差。这是一个隐藏 bug：字符串 `"false"` 在 Python 中 truthy，导致 `not "false"` = `False`，系统认为"这条需求是清晰的"，实际上 LLM 说的是不清晰。修复方式：在 JSON 解析后加一层 Pydantic model（定义 `is_clear: bool`），Pydantic 会自动把 `"true"`/`"false"` 字符串转为布尔值，同时拒绝 `"yes"` 这种无法转换的值并报 ValidationError，写入 trace 的 `error_message`。

---

### 5. `prompt_version` 硬编码为 `"v1.1"`，如果改了 prompt 忘更新版本号怎么办？

**30s 精简版：**
当前确实会脱节——`trace.py` 中的 `_PROMPT_VERSION` 和 `prompts.py` 中的实际文本没有任何联动。改进方式是对 prompt 模板内容算 hash，在 trace 中同时记录 `prompt_version` 和 `prompt_hash`，hash 变了自然知道 prompt 改过。

**60s 加分版：**
这是"约定 vs 自动化"的工程选择。当前靠开发者纪律维护一致性——V1 阶段团队小、迭代慢，可以接受。但长期风险是：两次运行的 trace 都标记 `prompt_version: v1.1`，但实际用了不同的 prompt，导致输出差异分析时产生误导。自动化方案：在 `prompts.py` 底部计算每组 prompt 的 SHA-256 前 8 位，类似 `PARSER_PROMPT_HASH = hashlib.sha256((PARSER_SYSTEM_PROMPT + PARSER_USER_PROMPT).encode()).hexdigest()[:8]`。然后在 `trace_start` 中传入 `prompt_hash` 参数。更进一步可以在 CI 中加检查——如果 prompt hash 变了但 `_PROMPT_VERSION` 没更新，阻止合并。

---

### 6. LLM 调用全部依赖 `gpt_researcher` 的 `create_chat_completion`，这个选择有什么利弊？

**30s 精简版：**
好处是复用了 `gpt_researcher` 已有的多 provider 支持（OpenAI / Azure / Ollama 等），不需要自己写适配层。劣势是返回值只有纯文本 string，拿不到 token usage、finish_reason 等元信息，限制了可观测性。

**60s 加分版：**
`create_chat_completion` 接受 `model`、`messages`、`temperature`、`llm_provider`、`llm_kwargs` 参数，返回 `str`。它内部封装了 LangChain 的 `ChatModel` 创建逻辑和多 provider 路由。好处是零成本复用——不需要自己处理 API key 管理、重试逻辑、provider 切换。劣势有三：一是返回值丢失了 token usage 信息，trace 中只能记 `output_chars` 而不是精确的 token 数；二是无法控制 `max_tokens`、`top_p`、`seed` 等高级参数（除非通过 `llm_kwargs` 传入，但这取决于 `gpt_researcher` 的实现）；三是强耦合了 `gpt_researcher` 的依赖——如果只想用 requirement_review_v1 模块，也得装整个 `gpt_researcher` 包。解耦方式是抽象一个 `LLMClient` 接口，默认实现委托给 `create_chat_completion`，也可以替换为直接调 OpenAI SDK。

---

### 7. 如何支持多模型对比评估？比如同时用 GPT-4o 和 Claude 跑，比较质量。

**30s 精简版：**
当前所有 Agent 共享 `Config()` 的同一个模型。要对比需要跑两次 pipeline。改进方案是在 state 中加 `model_override` 字段，用 `asyncio.gather` 并发跑多条 pipeline，每条用不同模型、不同 `run_dir`，最后对比 `report.json`。

**60s 加分版：**
具体改动：`main.py` 增加 `--models gpt-4o,claude-3-sonnet` 参数，解析后对每个模型创建独立 pipeline。每个 Agent 中把 `cfg.smart_llm_model` 改为 `state.get("model_override", cfg.smart_llm_model)`，这样 state 级别的模型覆盖优先于环境变量配置。每条 pipeline 输出到 `outputs/<run_id>/gpt-4o/` 和 `outputs/<run_id>/claude-3-sonnet/`。最后写一个 Comparator 脚本，读取多个 `report.json`，按维度对比：需求解析完整性（`parsed_items` 数量）、评审一致性（`is_clear` / `is_testable` 的差异）、计划合理性（`estimation.total_days` 差异）。这些指标天然可从 state 字段中提取。

---

### 8. 如何对 Agent 输出做自动化质量评估（Eval），而不是靠人工看报告？

**30s 精简版：**
当前没有自动评估。可以加三类检查：结构完整性（每个 task 的 `depends_on` 引用的 ID 是否存在）、覆盖率（每条需求是否有对应 task）、LLM-as-Judge（用独立模型对 `review_results` 质量打分）。

**60s 加分版：**
增加一个独立于 pipeline 的 Evaluator 模块，在 `graph.ainvoke` 之后执行。三类检查：一是**结构校验**——用代码检查 `parsed_items` 数量是否与原文段落数匹配（正则提取有序列表项数量做基准），`dependencies` 中引用的 task ID 是否全部存在于 `tasks` 列表；二是**覆盖率计分**——遍历 `parsed_items`，检查每条需求的 ID 是否出现在至少一个 task 的 title 或 description 中，计算 coverage_ratio；三是**LLM-as-Judge**——用一个不同于 pipeline 的模型（避免自己评自己的偏差），输入 `requirement_doc` + `review_results`，让它评估"评审是否遗漏了明显问题"。所有评分存入 `outputs/<run_id>/eval.json`，可以纳入 CI 设置阈值——低于 0.8 标记为低质量运行。

---

*文档生成时间：2026-02-27*
*基于 `requirement_review_v1/` 目录全部代码分析*
