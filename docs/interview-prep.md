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

**【Code】**
- 文件：`requirement_review_v1/workflow.py`
- 函数：`build_review_graph()`
```python
workflow = StateGraph(ReviewState)
workflow.add_node("parser", parser_agent.run)
workflow.add_node("planner", planner_agent.run)
workflow.add_node("risk", risk_agent.run)
workflow.add_node("reviewer", reviewer_agent.run)
workflow.add_node("reporter", reporter_agent.run)
workflow.set_entry_point("parser")
workflow.add_edge("parser", "planner")
workflow.add_edge("planner", "risk")
workflow.add_edge("risk", "reviewer")
workflow.add_edge("reviewer", "reporter")
workflow.add_edge("reporter", END)
return workflow.compile()
```

**Follow-up：** 你说 risk 和 reviewer 理论上可以并行，那为什么没做？如果真做了，trace 合并会出什么具体问题？

**Safe answer：** 当前未做并行。原因在代码里：两个节点都写 `state["trace"]`，LangGraph 的 `TypedDict` 默认 merge 是后写覆盖，risk 写完 trace 后 reviewer 再写会把 risk 的条目覆盖掉。要并行就得把 `ReviewState` 里 `trace` 改成 `Annotated[dict, operator.add]` 或自定义 reducer，当前 `state.py` 没这么定义，所以保持线性。证据：`workflow.py` 的 `add_edge` 是串行的，`state.py` 里 `trace: dict` 无 `Annotated` 注解。

---

### 2. `ReviewState` 用了 `TypedDict(total=False)`，为什么？有什么工程意义？

**30s 精简版：**
`total=False` 让所有字段都可选，每个 Agent 只需 return 自己负责的字段作为 partial update，不需要每次都返回完整 state。这样 LangGraph 做增量 merge 就行了。

**60s 加分版：**
在 `state.py` 中 `ReviewState` 定义了 12 个字段。如果用默认的 `total=True`，每个 Agent 的 return dict 必须包含所有 12 个字段，否则 type checker 会报错。`total=False` 解除了这个限制。实际上 `main.py` 的 `ainvoke` 只传了 `requirement_doc` 和 `run_dir` 两个字段，其余字段在 state 中根本不存在（不是 None，是 key 不存在），每个 Agent 用 `.get("xxx", [])` 做安全读取。这种模式的好处是：新增一个字段不需要改任何已有 Agent——只要它们不读取这个字段。`create_initial_state()` 函数提供了一个全字段初始化的入口，但只在 `debug.py` 中被使用，主流程不依赖它。

**【Code】**
- 文件：`requirement_review_v1/state.py`，`requirement_review_v1/main.py`
- 类/函数：`ReviewState`，`create_initial_state()`
```python
# state.py
class ReviewState(TypedDict, total=False):
    requirement_doc: str
    run_dir: str
    parsed_items: List[dict]
    review_results: List[dict]
    final_report: str
    trace: dict
    tasks: List[dict]
    milestones: List[dict]
    dependencies: List[dict]
    estimation: Dict[str, object]
    risks: List[dict]
    plan_review: Dict[str, str]

# main.py
result = await graph.ainvoke({"requirement_doc": doc, "run_dir": out_dir})
```

**Follow-up：** `create_initial_state` 只在 debug 用，主流程不初始化全字段，那第一个 Agent 读 `state.get("trace", {})` 拿到的是什么？会不会 NPE？

**Safe answer：** 不会。`main.py` 的 `ainvoke` 只传 `requirement_doc` 和 `run_dir`，parser 里 `state.get("trace", {})` 拿到的就是空 dict `{}`，因为 key 不存在时 `.get` 返回默认值。代码：`parser_agent.run()` 里有 `trace: dict = dict(state.get("trace", {}))`，空 dict 再 `dict()` 拷贝还是空 dict，后续正常 append。`debug.py` 用 `create_initial_state` 会初始化 `trace={}`，主流程不需要。

---

### 3. 每个 Agent 异常后返回空结果而不是终止 pipeline，为什么？

**30s 精简版：**
每个 Agent 内部 try/except 捕获所有异常，返回空列表 + error trace。这样 pipeline 一定能跑完，trace 中能看到所有节点的状态，便于定位"到底哪一步出了问题"。

**60s 加分版：**
以 `parser_agent.py` 为例，`except Exception as exc` 捕获后返回 `{"parsed_items": [], "trace": trace}`。后续的 planner 发现 `parsed_items` 为空时，也不调 LLM，直接返回空结果。一次运行的 `run_trace.json` 中始终有五个 agent 的记录——成功的标 `"ok"`，失败的标 `"error"` 并附带 `error_message`。和"条件边提前终止"方案对比：提前终止节省了空转开销，但 trace 中会缺少被跳过节点的记录，不利于构建 pipeline 健康度看板。当前设计的思路是——运行不贵（空转不调 LLM），诊断信息更重要。

**【Code】**
- 文件：`requirement_review_v1/agents/parser_agent.py`，`requirement_review_v1/agents/planner_agent.py`
- 函数：`run()`
```python
# parser_agent.py — 异常时返回空列表
except Exception as exc:
    raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
    trace[_AGENT] = span.end(status="error", ..., error_message=str(exc))
    return {"parsed_items": [], "trace": trace}

# planner_agent.py — parsed_items 为空时 early return，不调 LLM
if not parsed_items:
    span = trace_start(_AGENT, model="none", input_chars=0)
    trace[_AGENT] = span.end(status="error", error_message="parsed_items is empty — nothing to plan")
    return _empty_result(trace)
```

**Follow-up：** 你说 trace 能排障，那真实排过什么问题？具体怎么用 run_trace.json 定位的？

**Safe answer：** 当前 trace 设计就是为了排障。比如 parser 返回的 JSON 缺 `parsed_items` 时，`parser_agent.py` 里会走 `if "parsed_items" not in parsed` 分支，`trace["parser"]` 写成 `status="error"`, `error_message="key 'parsed_items' missing after json repair"`，并且 `raw_output_path` 指向保存的原始 LLM 输出，方便看模型到底返回了什么。`main.py` 把整个 trace 写到 `run_trace.json`，结构是 `{"parser": {...}, "planner": {...}, ...}`，每个节点有 `status`、`duration_ms`、`error_message`。真实排查时打开 run_trace.json 看哪个节点是 `"error"`，再按 `raw_output_path` 看对应 raw 文件。

---

### 4. trace 机制是怎么实现的？和 OpenTelemetry 有什么差距？

**30s 精简版：**
`utils/trace.py` 中定义了 `Span` 类，记录开始时间、结束时间、耗时、模型、状态、输入输出规模等。每个 Agent 调用 `trace_start()` 开始计时，完成后调用 `span.end()` 输出 trace dict，追加到 `state["trace"]` 中。

**60s 加分版：**
`Span` 有四个 slot：`agent_name`、`model`、`input_chars`、`_start_dt`。`end()` 计算 `duration_ms`，返回包含 10 个字段的 dict（`start`、`end`、`duration_ms`、`model`、`status`、`input_chars`、`output_chars`、`prompt_version`、`raw_output_path`、`error_message`）。和 OpenTelemetry 相比，当前实现缺少三个核心能力：一是没有 Span ID / Trace ID / Parent Span，无法表达"一次 pipeline 是父 span、五个 agent 是子 span"的层级关系；二是没有 context propagation，无法跨服务追踪；三是没有导出能力，只能写 JSON 文件，不能接入 Jaeger 等可视化工具。但在 V1 单进程低频场景下，自建 Span 零外部依赖、代码量极少，是合理的工程权衡。

**【Code】**
- 文件：`requirement_review_v1/utils/trace.py`
- 类/函数：`Span`，`trace_start()`
```python
class Span:
    __slots__ = ("agent_name", "model", "input_chars", "_start_dt")

    def end(self, *, status="ok", output_chars=0, raw_output_path="", error_message="") -> dict[str, Any]:
        end_dt = datetime.now(timezone.utc)
        duration_ms = int((end_dt - self._start_dt).total_seconds() * 1000)
        return {
            "start": self._start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "duration_ms": duration_ms,
            "model": self.model,
            "status": status,
            "input_chars": self.input_chars,
            "output_chars": output_chars,
            "prompt_version": _PROMPT_VERSION,
            "raw_output_path": raw_output_path,
            "error_message": error_message,
        }

def trace_start(agent_name: str, *, model: str = "unknown", input_chars: int = 0) -> Span:
    return Span(agent_name, model=model, input_chars=input_chars)
```

**Follow-up：** 你说和 OpenTelemetry 有差距，那现在 trace 没有 Trace ID，如果两次运行混在一起怎么区分？

**Safe answer：** 当前确实没有 Trace ID。每次运行是独立进程，`main.py` 为每次 run 生成单独的 `run_id`（时间戳格式），输出目录是 `outputs/<run_id>/`，`run_trace.json` 和 `report.json` 都在这个目录下，所以按目录就能区分不同运行。`report.json` 里会写 `"run_id": "20260223T085510Z"` 这类字段。证据：`main.py` 里 `run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")`，`out_dir = os.path.join("outputs", run_id)`。

---

### 5. `raw_agent_outputs` 只在失败时保存，正常成功的 LLM 输出不保存。为什么？

**30s 精简版：**
`utils/io.py` 的 `save_raw_agent_output` 只在 JSON key 缺失或异常时被调用。正常路径只记录 `output_chars`。设计意图是——成功时结构化结果已保存在 state 中，原始文本没有额外诊断价值；失败时才需要看 LLM 到底输出了什么。

**60s 加分版：**
在每个 Agent 中，`save_raw_agent_output` 的调用被守卫在 `if run_dir and raw` 条件后面，只出现在两处：一是 JSON 解析后缺少期望 key 的分支，二是 `except Exception` 分支。保存后的绝对路径记录在 trace 的 `raw_output_path` 字段中。当前设计的局限是无法做回归测试——没有成功运行的 raw baseline。改进方向是加 `SAVE_RAW_OUTPUT=always|error_only` 环境变量，默认维持 `error_only`。

**【Code】**
- 文件：`requirement_review_v1/utils/io.py`，`requirement_review_v1/agents/parser_agent.py`
- 函数：`save_raw_agent_output()`
```python
# io.py
def save_raw_agent_output(run_dir: str, agent_name: str, content: str) -> str:
    raw_dir = os.path.join(run_dir, "raw_agent_outputs")
    path = os.path.join(raw_dir, f"{agent_name}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return os.path.abspath(path)

# parser_agent.py — 仅在 key 缺失或异常时调用
if "parsed_items" not in parsed:
    raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""
    trace[_AGENT] = span.end(..., raw_output_path=raw_path, ...)
# except 分支同理
```

**Follow-up：** 如果 LLM 正常返回了，但 JSON 缺 key，会保存 raw 吗？路径存在哪儿？

**Safe answer：** 会。缺 key 和异常都会触发 `save_raw_agent_output`。代码证据：`parser_agent.py` 里 `if "parsed_items" not in parsed` 分支有 `raw_path = save_raw_agent_output(run_dir, _AGENT, raw) if run_dir and raw else ""`，然后 `span.end(..., raw_output_path=raw_path, ...)`。路径存在 trace 的 `raw_output_path` 字段里，最终写入 `run_trace.json`。`io.py` 里写入的是 `run_dir/raw_agent_outputs/parser.txt`，返回绝对路径。

---

### 6. `report.json` 中 `report_data.update(result)` 把整个 state 合进去，有什么问题？

**30s 精简版：**
`final_report` 这个很长的 Markdown 字符串和 `parsed_items`、`review_results` 等结构化数据存在完全冗余——报告就是从这些字段拼出来的。会导致 JSON 文件体积膨胀。

**60s 加分版：**
`main.py` 的 `update` 把全部 state 字段和元信息（`schema_version`、`run_id`、`model`）合并成一个 dict 写入 `report.json`。好处是自包含——拿到这一个文件就能还原所有状态。但有两个隐患：一是 `final_report` 已经单独存了 `report.md`，JSON 中再存一份是冗余；二是如果 state 中出现和元信息同名的 key（比如某个 Agent 不小心 return 了 `"schema_version": xxx`），`update` 会覆盖元信息。改进方式是把元信息嵌套在 `"meta"` key 下，或在写入时排除 `final_report` 字段。

**【Code】**
- 文件：`requirement_review_v1/main.py`
- 逻辑：`report_data.update(result)` 后写入 `report.json`
```python
report_data: dict = {
    "schema_version": "v1.1",
    "run_id": run_id,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "model": _model,
    "provider": _provider,
    "project": "requirement_review_v1",
}
report_data.update(result)
with open(state_path, "w", encoding="utf-8") as f:
    json.dump(report_data, f, ensure_ascii=False, indent=2)
```

**Follow-up：** 你说 final_report 冗余，那 report.json 里到底有没有 final_report？有的话为什么不删？

**Safe answer：** 有。`main.py` 里 `report_data.update(result)` 会把整个 state 合进去，`result` 里有 `final_report`，所以 report.json 里会有。当前没删是因为设计是"自包含"——单文件能还原全部状态，方便离线分析。删的话要在 update 之后、dump 之前 `report_data.pop("final_report", None)`，当前没做。证据：`main.py` 先 `report_data.update(result)`，再 `json.dump(report_data, f)`，没做 pop。

---

### 7. 为什么每个 Agent 都对 trace 做浅拷贝而不是直接修改？

**30s 精简版：**
`dict(state.get("trace", {}))` 创建了一个新 dict。如果直接修改 `state["trace"]`，是在原地 mutate LangGraph 管理的 state 对象，可能干扰框架的 diff 检测机制，将来改并行还会产生竞态条件。

**60s 加分版：**
LangGraph 的 state 更新模型是"每个 node return partial dict → 框架 merge"。如果 node 内部直接修改 state 引用，框架无法区分"这个字段是你 return 出来要更新的"还是"你只是读着玩儿不小心改了"。浅拷贝确保每个 Agent 操作的是独立副本，return 时让框架做干净的替换。浅拷贝而不是深拷贝足够了——因为 trace 中每个 agent 的 value 是 `span.end()` 返回的全新 dict，不存在嵌套引用共享问题。

**【Code】**
- 文件：`requirement_review_v1/agents/parser_agent.py`
- 模式：`trace = dict(state.get("trace", {}))`
```python
trace: dict[str, Any] = dict(state.get("trace", {}))
# ... 修改 trace ...
return {"parsed_items": parsed_items, "trace": trace}
```

**Follow-up：** 如果直接改 `state["trace"]` 不 return，LangGraph 会怎么处理？会更新吗？

**Safe answer：** 当前实现不会依赖"直接改 state"来更新。LangGraph 的更新模型是：node 的 return 值才会被 merge 进 state。如果只改 `state["trace"]` 不 return，框架不会知道你改了什么，因为它是根据 return 的 dict 做 merge 的。所以必须 return `{"trace": trace}` 才能把新 trace 写回去。代码里每个 agent 都是 `trace = dict(state.get("trace", {}))` 拷贝，改完后 `return {..., "trace": trace}`，没有直接 `state["trace"] = xxx`。

---

### 8. Reporter 不调 LLM，纯确定性拼接。为什么这样设计？

**30s 精简版：**
Reporter 的输入是完全结构化的（`parsed_items`、`review_results`、`tasks` 等 dict/list），不需要 LLM 的理解能力。确定性拼接保证输出格式稳定、不会有 JSON 解析失败的风险、不消耗 token。

**60s 加分版：**
`reporter_agent.py` 注释明确写了 "V1: no LLM call — the report is built by deterministic string concatenation"。它用 `_build_requirement_table`、`_build_task_table`、`_build_risk_register` 等辅助函数将结构化数据渲染为 Markdown 表格。trace 中 `model` 硬编码为 `"none"`。如果将来想让 LLM 生成 Executive Summary，最安全的方式是保留当前拼接逻辑不动，只在报告开头插入一段 LLM 生成的摘要——这样即使 LLM 失败，后面的确定性部分仍然完整。这是"LLM 增强但不依赖"的工程原则。

**【Code】**
- 文件：`requirement_review_v1/agents/reporter_agent.py`
- 函数：`run()`，`_build_requirement_table()`，`_build_task_table()`，`_build_risk_register()`
```python
# 文件头注释
V1: no LLM call — the report is built by deterministic string concatenation.

# run() 中
span = trace_start(_AGENT, model="none", input_chars=input_chars)
# 使用 _build_requirement_table、_build_task_table、_build_risk_register 等
```

**Follow-up：** Reporter 的 model 是 "none"，那 run_trace.json 里 reporter 那条记录有哪些字段？和调了 LLM 的 agent 有什么区别？

**Safe answer：** 结构一样，都是 `span.end()` 返回的 dict。区别是 `model` 为 `"none"`，`input_chars` 是 structured 数据的总字符数，`output_chars` 是 final_report 长度。`trace.py` 的 `Span.end()` 返回 10 个字段：start、end、duration_ms、model、status、input_chars、output_chars、prompt_version、raw_output_path、error_message。reporter 不会写 raw_output_path（不调 LLM 无 raw）。证据：`reporter_agent.py` 里 `span = trace_start(_AGENT, model="none", input_chars=input_chars)`，然后 `trace[_AGENT] = span.end(status="ok", output_chars=len(final_report))`。

---

### 9. `schema_version` 在代码里是怎么用的？有向后兼容机制吗？

**30s 精简版：**
`main.py` 写入 `"schema_version": "v1.1"` 到 `report.json`，但当前没有对应的 JSON Schema 文件、没有校验逻辑、也没有迁移代码。它是一个预埋的版本标记，供未来下游消费者做兼容判断。

**60s 加分版：**
这个版本号配合 `prompt_version`（`trace.py` 中硬编码的 `_PROMPT_VERSION = "v1.1"`）构成了两层版本追踪——前者标记输出格式，后者标记 prompt 模板版本。当前实现：两者都靠开发者手动维护，没有自动化校验；如果改了 prompt 但忘了更新版本号会脱节。改进方向：给 output schema 维护 JSON Schema 定义、写入时做 `jsonschema.validate`；给 prompt 算内容 hash 自动关联版本。兼容原则应为"minor 版本只加字段不删字段"，让旧版消费者用 `.get()` 加默认值兼容新字段。

**【Code】**
- 文件：`requirement_review_v1/main.py`，`requirement_review_v1/utils/trace.py`
- 变量：`schema_version`，`_PROMPT_VERSION`
```python
# main.py
report_data = {"schema_version": "v1.1", ...}

# trace.py
_PROMPT_VERSION = "v1.1"
# span.end() 返回的 dict 中含 "prompt_version": _PROMPT_VERSION
```

**Follow-up：** schema_version 和 prompt_version 都在用 "v1.1"，它们是一个意思吗？如果只改 prompt 不改 schema，版本号该怎么标？

**Safe answer：** 不是同一个。`schema_version` 在 `main.py` 里写进 report.json，标记输出格式；`prompt_version` 在 `trace.py` 的 `_PROMPT_VERSION`，写进每个 span 的 trace dict，标记 prompt 版本。当前两者都硬编码 "v1.1"，没有联动。如果只改 prompt 不改 schema，按设计应该是 prompt_version 变、schema_version 不变，但当前要改得手动改 `trace.py` 的 `_PROMPT_VERSION`，没有自动化。证据：`main.py` 写 `"schema_version": "v1.1"`，`trace.py` 有 `_PROMPT_VERSION = "v1.1"`，两者独立。

---

### 10. 如果 pipeline 跑到第四步 reviewer 才失败，前三步的 LLM 费用浪费了。如何断点恢复？

**30s 精简版：**
当前 `workflow.compile()` 没有传 checkpointer，中间状态不持久化。LangGraph 本身支持 `SqliteSaver` 等 checkpointer，加上后每个节点执行完自动存快照，失败后可以从断点恢复。当前未实现，原因是 V1 场景下需求文档通常不大，从头重跑的成本低于引入 checkpoint 的工程复杂度。

**60s 加分版：**
当前实现：`workflow.compile()` 未传 checkpointer，无断点恢复能力。改进思路：`workflow.compile(checkpointer=SqliteSaver("checkpoint.db"))`，`ainvoke` 时传 `config={"configurable": {"thread_id": run_id}}`。框架会在每个节点后保存全量 state，失败后用相同 `thread_id` 再次调用 `ainvoke(None, config=...)` 从上次中断的节点继续。未实现原因：V1 场景下四次 LLM 调用总花费低，SQLite 文件管理、恢复 CLI、thread_id 机制引入的复杂度不划算。若实现，checkpoint 文件可存到 `outputs/<run_id>/` 下和报告一起归档。

**【Code】**
- 文件：`requirement_review_v1/workflow.py`
- 函数：`build_review_graph()`
```python
return workflow.compile()  # 无 checkpointer 参数
```

**Follow-up：** 你说 V1 没做 checkpoint，那 reviewer 失败时，前三步的结果在内存里还有吗？能手动捞出来吗？

**Safe answer：** 能捞出来。每个 agent 内部都有 try/except，失败时返回空结果和 error trace，不抛异常，所以 `ainvoke` 会正常返回。`main.py` 在 ainvoke 之后写 `report_data.update(result)`，result 里有 parser/planner/risk 的 outputs，所以 report.json 会包含 parsed_items、tasks、risks 等。失败时 reviewer 那条是 status="error"，但前几步的结构化结果都在 report.json 里。断点恢复当前未做——要重跑 reviewer 得手动从 report.json 读前几步结果再拼 state，没有自动化。

---

### 11. 如果需求规模从 10 条扩展到 200 条，当前架构会遇到什么瓶颈？

**30s 精简版：**
Parser 把整份文档一次性塞进 prompt，200 条需求可能超过上下文窗口。后续 Planner 和 Reviewer 又全量灌入 `parsed_items`，三次全量传入加剧 token 消耗和注意力衰减问题。

**60s 加分版：**
三个瓶颈：一是 token 限制——200 条需求的 `parsed_items` 序列化后可能超过 50K tokens，Planner 和 Reviewer 的 prompt 加上 system prompt 可能逼近 128K 上下文窗口；二是质量衰减——LLM 对长输入末尾的注意力下降，容易漏掉靠后的需求；三是延迟——四次 LLM 调用，每次处理长文本，端到端可能超过 5 分钟。解决方案（当前未实现）：在 parser 之后加分片调度节点，按 20 条一组拆 batch，对每组独立跑 planner→risk→reviewer 的子图，最后用聚合节点合并。

**【Code】**
- 文件：`requirement_review_v1/agents/parser_agent.py`
- 逻辑：整份文档传入 prompt
```python
content=PARSER_USER_PROMPT.format(requirement_doc=requirement_doc)
# 无分片，requirement_doc 为完整文档
```

**Follow-up：** Parser 塞整份文档，那 PLANNER_USER_PROMPT 和 REVIEWER_USER_PROMPT 塞的又是什么？也是整份吗？

**Safe answer：** 不是。Parser 塞的是原始 `requirement_doc`。Planner 塞的是 `items_json`，即 `json.dumps(parsed_items, ...)`，也就是 parser 的结构化结果。Reviewer 塞的是 `items_json` 加 `plan_json`，即 parsed_items 和 plan 的 JSON 拼在一起。所以三次全量分别是：原始文档、parsed_items、parsed_items+plan。证据：`parser_agent.py` 用 `PARSER_USER_PROMPT.format(requirement_doc=...)`；`planner_agent.py` 用 `PLANNER_USER_PROMPT.format(items_json=items_json)`；`reviewer_agent.py` 用 `REVIEWER_USER_PROMPT.format(items_json=..., plan_json=...)`。

---

### 12. 如何从 CLI 工具升级为多人使用的 Web 服务？

**30s 精简版：**
用 FastAPI 包裹 `build_review_graph()`，暴露 `POST /api/v1/review` 接口。graph 执行放后台任务（Celery/BackgroundTasks），用 run_id 查询结果。`outputs/` 迁移到 S3。当前 state-driven 架构下，workflow、agents、prompts、trace 模块只需在入口层做适配即可复用，无需改核心逻辑。

**60s 加分版：**
分三层改造（均为未实现的设计建议）。API 层：FastAPI + `POST /review`（提交）+ `GET /review/{run_id}`（查询），graph 执行放入 Celery worker 避免 HTTP 超时。存储层：`save_raw_agent_output` 和 `main.py` 的文件写入改为 S3 客户端，`run_dir` 变为 `s3://bucket/user_id/run_id/`。多租户：state 增加 `user_id`，API key 从用户数据库读取。核心优势：当前 `workflow.py`、五个 agent、`prompts.py`、`trace.py` 均无 Web/S3 相关逻辑，升级时只需在入口层做适配。

**Follow-up：** 你说 "workflow、agents 一行不改"，那 main.py 现在是怎么调 workflow 的？入口层具体指哪几行？

**Safe answer：** 入口层指 `main.py`。当前 `main.py` 里 `graph = build_review_graph()`，然后 `result = await graph.ainvoke({"requirement_doc": doc, "run_dir": out_dir})`，后面是写 report.md、report.json、run_trace.json。升级时把这段包进 FastAPI 的 route，把 `ainvoke` 放后台任务，把文件写入改成 S3，workflow 和 agents 的 import 和调用方式不变。证据：`main.py` 只 import `build_review_graph`，不直接碰 agents；`workflow.py` 的 `build_review_graph` 返回 `workflow.compile()`，对外是黑盒。

---

## 第二部分：大模型应用岗 Top 8

---

### 1. Prompt 里要求"no markdown fences"，代码却用 `parse_json_markdown` 处理围栏，矛盾吗？

**30s 精简版：**
不矛盾，是防御性工程。Prompt 约束降低 LLM 加围栏的概率，`parse_json_markdown` 兜底处理万一加了围栏的情况。"信任但验证"——两层一起用最稳健。

**60s 加分版：**
LLM（尤其 GPT-4/Claude）有强烈倾向给 JSON 加 ` ```json ` 围栏，即使 prompt 明确禁止。Prompt 中的指令是第一层防线——降低发生概率；`parse_json_markdown` 是第二层——即使发生了也能正确提取。如果去掉 prompt 约束，围栏出现概率大增但仍能解析；如果去掉 `parse_json_markdown`，一旦 LLM 加了围栏，`json_repair.loads` 可能无法处理前导的 ` ```json\n ` 文本。可以在 trace 中记录"是否触发了 markdown 剥离"作为 prompt 遵从率监控（当前未实现）。

**【Code】**
- 文件：`requirement_review_v1/prompts.py`，`requirement_review_v1/agents/parser_agent.py`
- 关键字符串与调用
```python
# prompts.py — 各 system prompt 中
Respond with **valid JSON only** — no markdown fences, no commentary.

# parser_agent.py
parsed = parse_json_markdown(raw, parser=json_repair.loads)
```

**Follow-up：** 你说可以记录"是否触发了 markdown 剥离"做监控，当前代码里有这逻辑吗？

**Safe answer：** 当前未做。trace 里没有 "stripped_markdown" 或类似字段。`parse_json_markdown` 是 langchain 的，我们只拿解析结果，不记录中间是否剥离了围栏。要加的话得在调用前后比较 raw 和最终喂给 json_repair 的文本，或改 parse_json_markdown 的包装。证据：`parser_agent.py` 里只有 `parsed = parse_json_markdown(raw, parser=json_repair.loads)`，没有额外 logging。

---

### 2. JSON 解析用了 `parse_json_markdown` + `json_repair.loads` 双层容错，各自解决什么问题？

**30s 精简版：**
`parse_json_markdown` 从 Markdown 代码围栏中提取 JSON 文本；`json_repair.loads` 修复 JSON 语法错误（尾部逗号、单引号、缺失括号）。前者解决格式包装问题，后者解决内容损坏问题。

**60s 加分版：**
两层是串联关系。`parse_json_markdown` 的 `parser` 参数接受可调用对象，默认是 `parse_partial_json`，这里显式传入 `json_repair.loads` 覆盖。执行流程：先用正则检测 ` ```json...``` ` 围栏并提取内部文本；如果没有围栏则把整个 raw 当作 JSON；然后调用 `json_repair.loads` 解析。`json_repair` 能处理 LLM 常见的格式错误——尾部多余逗号、属性名未加双引号、字符串内未转义的换行等。两层结合提高"LLM 输出 → Python dict"的成功率。仍有盲区：语义层面的类型错误（如 `"is_clear": "yes"` 代替 `true`）无法被检测，需要引入 Pydantic schema validation（当前未实现）。

**【Code】**
- 文件：`requirement_review_v1/agents/parser_agent.py`（以及 planner、risk、reviewer）
- 调用：`parse_json_markdown(raw, parser=json_repair.loads)`
```python
parsed: dict = parse_json_markdown(raw, parser=json_repair.loads)
parsed_items: list[dict] = parsed.get("parsed_items", [])
```

**Follow-up：** json_repair 修不了语义错误，那 `"is_clear": "yes"` 会被怎么处理？最终到 Python 里是什么类型？

**Safe answer：** json_repair 只修语法，`"is_clear": "yes"` 会被解析成 Python 的 str `"yes"`，不会转成 bool。`reporter_agent.py` 的 `_risk_level` 里 `result.get("is_clear", True)` 拿到的就是 str，然后 `not result.get("is_clear", True)`：`not "yes"` 是 False，和 `not True` 一样，所以碰巧行为对。但 `"false"` 就错了，`not "false"` 还是 False。证据：`_risk_level` 直接用 `not result.get("is_clear", True)` 做布尔运算，没有 `isinstance` 或转 bool 的逻辑。

---

### 3. 所有 Agent 都用 `temperature=0`，是否保证每次输出完全一致？

**30s 精简版：**
不是。`temperature=0` 让模型选概率最高的 token，但 GPU 浮点运算的非确定性、API 端 batching 差异、模型版本更新都可能导致微小差异。严格可复现需要额外加 `seed` 参数（当前未实现）。

**60s 加分版：**
选择 `temperature=0` 的原因是这个场景需要结构化 JSON 输出，要求准确性和 schema 一致性，不需要多样性。0.3 以上会增加 LLM "创造性发挥"的概率——比如擅自调整 JSON 结构。但 `temperature=0` 不等于确定性：OpenAI 文档指出由于分布式推理和浮点精度问题，相同输入可能产生不同输出。如需严格可复现（如回归测试），应加 `seed` 参数并在 trace 中记录 `system_fingerprint`（当前未实现）。

**【Code】**
- 文件：`requirement_review_v1/agents/parser_agent.py`，`planner_agent.py`，`reviewer_agent.py`，`risk_agent.py`
- 参数：`temperature=0`
```python
raw = await create_chat_completion(
    model=cfg.smart_llm_model,
    messages=messages,
    temperature=0,
    llm_provider=cfg.smart_llm_provider,
    llm_kwargs=cfg.llm_kwargs,
)
```

**Follow-up：** 你们实际跑过两次相同输入吗？输出有没有差异？trace 里能看出来吗？

**Safe answer：** 当前 trace 没有记录 `system_fingerprint` 或 `seed`，无法从输出文件判断两次是否"同一模型版本"。`temperature=0` 理论上更稳定，但 OpenAI 文档说相同输入仍可能不同输出。要验证只能手动跑两次对比 report.json 的 parsed_items、review_results 等。当前没有自动化回归或一致性检查。证据：trace 的 `Span.end()` 返回的字段里没有 fingerprint、seed。

---

### 4. 如果 LLM 返回的 `is_clear` 是字符串 `"yes"` 而不是布尔值 `true`，系统能检测到吗？

**30s 精简版：**
不能。代码没有 schema validation。而且 Python 中 `not "yes"` 等于 `False`（和 `not True` 一致），碰巧结果正确。但如果返回 `"false"` 字符串，`not "false"` 还是 `False`（非空字符串 truthy），和期望的 `not False = True` 完全相反——会把不清晰的需求误判为清晰。

**60s 加分版：**
`reporter_agent.py` 的 `_risk_level` 函数用 `result.get("is_clear", True)` 读取后直接做布尔运算。当前没有任何类型校验层——`json_repair` 修复语法错误但不修复语义类型偏差。这是一个隐藏 bug：字符串 `"false"` 在 Python 中 truthy，导致 `not "false"` = `False`，系统认为"这条需求是清晰的"。修复方式：在 JSON 解析后加一层 Pydantic model（定义 `is_clear: bool`），Pydantic 会自动把 `"true"`/`"false"` 转为布尔值，并拒绝 `"yes"` 报 ValidationError（当前未实现）。

**【Code】**
- 文件：`requirement_review_v1/agents/reporter_agent.py`
- 函数：`_risk_level()`
```python
def _risk_level(result: dict) -> str:
    flags = sum([
        not result.get("is_clear", True),
        not result.get("is_testable", True),
        result.get("is_ambiguous", False),
    ])
```

**Follow-up：** 你说 "false" 会误判，那 review_results 里 is_clear 实际长什么样？有没有从真实 run 里看到过字符串？

**Safe answer：** 当前没有 schema 校验，LLM 返回什么就存什么。report.json 里的 review_results 每项有 is_clear、is_testable、is_ambiguous，正常情况是 bool，但 LLM 若返回 "yes"/"no" 就会变成 str。我们没做类型检查，所以一旦出现字符串，_risk_level 就会按 Python 的 truthy 规则算，可能错。证据：`reporter_agent.py` 里 `_risk_level` 直接 `not result.get("is_clear", True)`，没有 `if isinstance(..., bool)` 之类的分支。

---

### 5. `prompt_version` 硬编码为 `"v1.1"`，如果改了 prompt 忘更新版本号怎么办？

**30s 精简版：**
当前确实会脱节——`trace.py` 中的 `_PROMPT_VERSION` 和 `prompts.py` 中的实际文本没有任何联动。改进方式是对 prompt 模板内容算 hash，在 trace 中同时记录 `prompt_version` 和 `prompt_hash`（当前未实现）。

**60s 加分版：**
当前靠开发者纪律维护一致性——V1 阶段团队小、迭代慢，可以接受。但长期风险是：两次运行的 trace 都标记 `prompt_version: v1.1`，但实际用了不同的 prompt。自动化方案：在 `prompts.py` 底部计算每组 prompt 的 SHA-256 前 8 位，在 `trace_start` 中传入 `prompt_hash` 参数，CI 中检查 prompt hash 变了但 `_PROMPT_VERSION` 没更新时阻止合并（当前未实现）。

**【Code】**
- 文件：`requirement_review_v1/utils/trace.py`
- 变量：`_PROMPT_VERSION`
```python
_PROMPT_VERSION = "v1.1"
# 与 prompts.py 无自动化联动
```

**Follow-up：** 要是有人改了 prompts.py 但没改 _PROMPT_VERSION，能从 report.json 或 run_trace.json 里发现吗？

**Safe answer：** 不能。两个文件里只有 `prompt_version: "v1.1"`，没有 prompt 内容的 hash。要发现只能人工对比 prompts.py 的 git diff 和运行时间。当前未做 hash 或 CI 检查。证据：`trace.py` 的 `span.end()` 只写 `"prompt_version": _PROMPT_VERSION`，没有别的版本相关字段。

---

### 6. LLM 调用全部依赖 `gpt_researcher` 的 `create_chat_completion`，这个选择有什么利弊？

**30s 精简版：**
好处是复用了 `gpt_researcher` 已有的多 provider 支持（OpenAI / Azure / Ollama 等），不需要自己写适配层。劣势是返回值只有纯文本 string，拿不到 token usage、finish_reason 等元信息，trace 中只能记 `output_chars` 而不是精确 token 数。

**60s 加分版：**
`create_chat_completion` 接受 `model`、`messages`、`temperature`、`llm_provider`、`llm_kwargs` 参数，返回 `str`。它内部封装了 LangChain 的 ChatModel 创建逻辑和多 provider 路由。好处是零成本复用。劣势：一是返回值丢失 token usage；二是无法直接控制 `max_tokens`、`top_p`、`seed` 等（除非通过 `llm_kwargs`，取决于 `gpt_researcher` 实现）；三是强耦合——若只想用 requirement_review_v1 模块，也得装整个 `gpt_researcher` 包。解耦方式是抽象 `LLMClient` 接口，默认实现委托给 `create_chat_completion`（当前未实现）。

**【Code】**
- 文件：`gpt_researcher/utils/llm.py`，`requirement_review_v1/agents/parser_agent.py`
- 函数：`create_chat_completion()`
```python
# 调用方式
from gpt_researcher.utils.llm import create_chat_completion
raw = await create_chat_completion(
    model=cfg.smart_llm_model,
    messages=messages,
    temperature=0,
    llm_provider=cfg.smart_llm_provider,
    llm_kwargs=cfg.llm_kwargs,
)
```

**Follow-up：** 拿不到 token usage，那 trace 里 output_chars 是怎么算的？和 token 数差多少？

**Safe answer：** `output_chars` 是 `len(raw)`，即 LLM 返回的原始字符串的字符数。token 数一般是字符数的 1/4 左右（英文），中文更高。trace 里没有 token 数，只能从 output_chars 粗略估。证据：`parser_agent.py` 里 `trace[_AGENT] = span.end(status="ok", output_chars=len(raw))`，raw 是 `create_chat_completion` 返回的 str。

---

### 7. 如何支持多模型对比评估？比如同时用 GPT-4o 和 Claude 跑，比较质量。

**30s 精简版：**
当前所有 Agent 共享 `Config()` 的同一个模型（`cfg.smart_llm_model`）。要对比需要跑两次 pipeline。改进方案是在 state 中加 `model_override` 字段，用 `asyncio.gather` 并发跑多条 pipeline，每条用不同模型、不同 `run_dir`，最后对比 `report.json`（当前未实现）。

**60s 加分版：**
当前实现：每个 Agent 通过 `Config()` 读取 `smart_llm_model`，无 state 级别覆盖。改进方向：`main.py` 增加 `--models gpt-4o,claude-3-sonnet` 参数；每个 Agent 中把 `cfg.smart_llm_model` 改为 `state.get("model_override", cfg.smart_llm_model)`；每条 pipeline 输出到 `outputs/<run_id>/gpt-4o/` 和 `outputs/<run_id>/claude-3-sonnet/`；写 Comparator 脚本读取多个 `report.json` 按 `parsed_items` 数量、`is_clear`/`is_testable` 差异、`estimation.total_days` 差异对比（当前未实现）。

**【Code】**
- 文件：`requirement_review_v1/agents/parser_agent.py` 等
- 逻辑：共享 `Config()` 的模型
```python
cfg = Config()
span.model = cfg.smart_llm_model or "unknown"
raw = await create_chat_completion(model=cfg.smart_llm_model, ...)
```

**Follow-up：** 要对比两个模型，是不是改 .env 里的模型名跑两次就行？report.json 会覆盖吗？

**Safe answer：** 会覆盖。每次运行的输出目录是 `outputs/<run_id>/`，run_id 是时间戳，所以不同次运行进不同目录，不会覆盖。但要对比需要手动跑两次、改 .env 或环境变量里的模型，然后手动对比两个目录下的 report.json。当前没有 `--models` 参数或 Comparator 脚本。证据：`main.py` 里 `run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")`，每次 run 新目录。

---

### 8. 如何对 Agent 输出做自动化质量评估（Eval），而不是靠人工看报告？

**30s 精简版：**
当前没有自动评估。可以加三类检查：结构完整性（`depends_on` 引用的 ID 是否存在）、覆盖率（每条需求是否有对应 task）、LLM-as-Judge（用独立模型对 `review_results` 质量打分）。这些均为未实现的设计建议。

**60s 加分版：**
当前实现：无 Evaluator 模块。改进思路：在 `graph.ainvoke` 之后执行 Evaluator。一是结构校验——`parsed_items` 数量是否与原文段落数匹配，`dependencies` 中引用的 task ID 是否全部存在于 `tasks`；二是覆盖率计分——每条需求的 ID 是否出现在至少一个 task 的 title 或 description 中；三是 LLM-as-Judge——用不同于 pipeline 的模型评估"评审是否遗漏了明显问题"。评分存入 `outputs/<run_id>/eval.json`，可纳入 CI 设置阈值（当前未实现）。

**Follow-up：** 你说覆盖检查，具体怎么判定"每条需求有没有对应 task"？当前有实现吗？

**Safe answer：** 当前未做覆盖检查，没有代码层面的覆盖判定逻辑。report.json 里有 `plan_review` 字段，是 reviewer 的 LLM 输出，其中可能有对 coverage 的评语，但那是自然语言，不是结构化计分。要做覆盖判定，需要遍历 parsed_items 的 id，检查是否出现在 tasks 里某个 task 的 title、description 或 depends_on 中，当前没有这段逻辑。证据：搜索 `coverage`、`覆盖` 等，只有 prompts 里对 reviewer 的指令，没有实现代码。

---

## What I didn't implement yet (and why)

| 未实现项 | 原因 |
|----------|------|
| **Checkpoint / 断点恢复** | V1 场景下需求文档通常不大，四次 LLM 调用成本低，从头重跑比引入 SqliteSaver、thread_id、恢复 CLI 更省事。若需求规模变大再考虑。 |
| **OpenTelemetry 集成** | 当前自建 Span 零外部依赖、代码量极少，足以满足 V1 单进程低频场景。接入 OTel 需要引入依赖和配置，收益有限。 |
| **risk / reviewer 并行** | 线性结构 trace 天然有序、调试简单。并行需处理 `trace` 字段合并（`Annotated[dict, merge_dicts]`），V1 节点少、延迟可接受，暂不引入。 |
| **Parser 分片 / Batch** | 当前整份文档一次性塞入 prompt。200 条需求时需按条数分 batch、子图聚合，工程量较大，V1 未覆盖该规模。 |
| **Web API / FastAPI** | 当前为 CLI 工具。升级需 FastAPI + 后台任务 + run_id 查询，存储迁移到 S3。入口层适配即可，核心模块可复用，但 V1 未做。 |
| **Notion / 外部集成** | 输出仅为本地 `report.md`、`report.json`，无 Notion、Jira 等集成。需要额外 API 适配和鉴权，V1 未涉及。 |
| **SAVE_RAW_OUTPUT=always** | `save_raw_agent_output` 仅在失败时调用。成功时保存 raw 可用于回归测试，但会增大存储，V1 默认 `error_only`。 |
| **Pydantic schema validation** | `json_repair` 只修语法，不修语义类型（如 `"is_clear": "yes"`）。加 Pydantic 可检测并报错，但需定义全套 schema，V1 未做。 |
| **prompt_hash 自动化** | `_PROMPT_VERSION` 与 prompt 文本无联动，靠人工维护。算 hash 自动关联可避免脱节，V1 未实现。 |
| **多模型并发对比** | 需 `model_override`、多 run_dir、Comparator 脚本，V1 单模型够用。 |
| **自动 Eval / LLM-as-Judge** | 无结构校验、覆盖率计分、LLM-as-Judge。需独立 Evaluator 模块和 CI 集成，V1 未实现。 |

---

## A) 后端/平台岗必背 10 题

| # | 题目 | 20 秒一句话答案 | 证据 |
|---|------|-----------------|------|
| 1 | 为什么线性串行五节点？ | 数据依赖强，且并行时两个节点都写 trace 会覆盖，需自定义 reducer，V1 优先正确性。 | `workflow.py`：`add_edge` 串行 |
| 2 | `ReviewState` 用 `total=False` 的意义？ | 字段可选，每个 Agent 只 return 自己负责的字段做 partial update，LangGraph 做增量 merge。 | `state.py`：`class ReviewState(TypedDict, total=False)` |
| 3 | Agent 异常后为何返回空结果不终止？ | try/except 捕获后返回空列表 + error trace，pipeline 能跑完，trace 有全部节点记录便于排障。 | `parser_agent.py`：`except Exception` 返回 `{"parsed_items": [], "trace": trace}` |
| 4 | trace 机制怎么实现？ | `Span` 类四个 slot，`trace_start()` 开始、`span.end()` 返回 10 字段 dict，写入 `state["trace"]`。 | `utils/trace.py`：`Span`、`trace_start` |
| 5 | raw 为何只在失败时保存？ | 成功时结构化结果在 state 中，失败时才需看 LLM 原始输出；调用点在 key 缺失或 except 分支。 | `parser_agent.py`：`if "parsed_items" not in parsed` 及 except |
| 6 | `report.json` 的 `update(result)` 有什么问题？ | final_report 与 parsed_items 等冗余；state 中若有同名 key 会覆盖元信息。 | `main.py`：`report_data.update(result)` |
| 7 | 为何 trace 做浅拷贝？ | LangGraph 靠 node return 做 merge，直接改 state 引用框架无法区分；浅拷贝足够，trace value 是全新 dict。 | `parser_agent.py`：`trace = dict(state.get("trace", {}))` |
| 8 | Reporter 为何不调 LLM？ | 输入已是结构化 dict/list，确定性拼接即可；保证格式稳定、无 JSON 解析失败、不耗 token。 | `reporter_agent.py`：注释 "no LLM call"，`model="none"` |
| 9 | `schema_version` 怎么用？ | 写入 report.json 做版本标记，当前无 JSON Schema、无校验、无迁移，供下游兼容判断。 | `main.py`：`"schema_version": "v1.1"` |
| 10 | 为何无 checkpoint？ | `workflow.compile()` 未传 checkpointer，V1 需求规模小、重跑成本低，引入 SQLite 复杂度不划算。 | `workflow.py`：`return workflow.compile()` |

---

## B) 大模型应用/Agent 岗必背 10 题

| # | 题目 | 20 秒一句话答案 | 证据 |
|---|------|-----------------|------|
| 1 | "no markdown fences" 和 `parse_json_markdown` 矛盾吗？ | 不矛盾，prompt 降低概率，parse_json_markdown 兜底；两层防御。 | `prompts.py`：`no markdown fences`；`parser_agent.py`：`parse_json_markdown(raw, parser=json_repair.loads)` |
| 2 | `parse_json_markdown` 和 `json_repair.loads` 各自作用？ | 前者提取围栏内 JSON 文本，后者修语法错误（尾部逗号、未加引号等）。 | `parser_agent.py`：`parse_json_markdown(raw, parser=json_repair.loads)` |
| 3 | 所有 Agent 用 `temperature=0` 能保证一致吗？ | 不能，GPU 非确定性、API batching、模型更新都会导致差异；严格可复现需 seed（当前未做）。 | `parser_agent.py` 等：`temperature=0` |
| 4 | `is_clear` 返回字符串 `"false"` 会误判吗？ | 会，`not "false"` 为 False（非空字符串 truthy），会把不清晰误判为清晰。 | `reporter_agent.py`：`_risk_level` 里 `not result.get("is_clear", True)` |
| 5 | `prompt_version` 和 prompts 有联动吗？ | 无，`_PROMPT_VERSION` 硬编码，与 prompts 内容无自动化关联。 | `trace.py`：`_PROMPT_VERSION = "v1.1"` |
| 6 | 为何用 `create_chat_completion`？利弊？ | 复用 gpt_researcher 多 provider；利：零成本复用；弊：返回 str 无 token usage，强耦合。 | `gpt_researcher/utils/llm.py`，`parser_agent.py` 等 |
| 7 | trace 里 `output_chars` 是什么？ | `len(raw)`，即 LLM 返回字符串的字符数，非 token 数。 | 各 agent：`span.end(output_chars=len(raw))` |
| 8 | Parser / Planner / Reviewer 各自塞什么进 prompt？ | Parser 塞 `requirement_doc`，Planner 塞 `parsed_items` 的 JSON，Reviewer 塞 parsed_items + plan 的 JSON。 | `parser_agent.py`、`planner_agent.py`、`reviewer_agent.py` |
| 9 | `run_trace.json` 结构？ | 五 agent 为 key，每条约 10 字段：start、end、duration_ms、model、status、input_chars、output_chars、prompt_version、raw_output_path、error_message。 | `main.py` 写 `result.get("trace", {})`；`trace.py` `Span.end()` |
| 10 | `report.json` 含哪些核心字段？ | 元信息：schema_version、run_id、model、provider；state：parsed_items、review_results、tasks、risks、plan_review、final_report 等。 | `main.py`：`report_data.update(result)`；README 文档 |

---

*文档生成时间：2026-03-02*
*基于 `requirement_review_v1/` 目录全部代码审计*
