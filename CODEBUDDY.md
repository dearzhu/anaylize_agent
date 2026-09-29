# CODEBUDDY.md This file provides guidance to CodeBuddy when working with code in this repository.

本地化金融数据分析智能体，按《金融数据分析智能体设计文档 v0.2》分三期交付。全部模型经 Ollama 本地部署、数据不出内网；**数值一律由规则引擎/ pandas 计算，LLM 只做解读，不负责算数**。

## 常用命令

**环境激活（PowerShell 已受限脚本策略，二选一）**
- 临时放开：`Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`，再 `.venv/Scripts/Activate.ps1`
- 或直接用 venv 解释器前缀（不受策略限制）：`.venv/Scripts/python.exe ...`
- 注意：必须用 **Python 3.11** venv（paddle/rapidocr/onnxruntime 不支持 3.14）。无 venv 时：`py -3.11 -m venv .venv` 后 `pip install -r requirements.txt`。

**运行全部测试（无需 Ollama，链路会自动降级）**
`.venv/Scripts/python.exe -m pytest tests/ -q`

**运行单个测试**
`.venv/Scripts/python.exe -m pytest tests/test_orchestrator.py::test_strategy_depends_on_risk -q`

**生成样例数据（确定性，可重复）**
`.venv/Scripts/python.exe scripts/seed_data.py`

**演示**
- 财报指标+异常（纯本地）：`scripts/demo_financial.py`
- 二期编排：`scripts/demo_orchestrator.py`
- 三期闭环+报告：`scripts/demo_multiagent.py`
- RAG 问答（需 Ollama 已启动并拉取 bge-m3/qwen2.5:7b/qwen2.5-vl:7b）：`scripts/demo_rag.py`

**语法检查**：`.venv/Scripts/python.exe -m py_compile <files>`

## 总体架构

项目采用 **编排层 + 能力层 + 数据层** 分层。核心是一个 `Supervisor` 负责意图识别、任务路由、结果融合与冲突检测；各 `Worker Agent` 单职责，通过统一的 `AgentMessage`/`FusedResult` 通信。

### 包职责（`src/`）

- **`orchestrator/`** — 编排框架（不自己算数）：
  - `message.py`：`AgentMessage`（通信契约，含 `success`/`output`/`confidence`/`sources`/`notes` 等）与 `FusedResult`（多 Agent 结论聚合）。
  - `base.py`：`AgentContext`（跨 Agent 共享上下文，Supervisor 注入上游结果）与 `BaseAgent`（抽象基类，含便捷构造 `_ok()`/`_fail()` 返回 `AgentMessage`）。
  - `intent.py`：`IntentClassifier`，按关键词路由并补齐依赖。
  - `supervisor.py`：`Supervisor`，路由 + 依赖注入 + 拓扑排序 + 加权融合 + 冲突检测 + 人在回路。
- **`agents/`** — Worker Agent 实现（二期/三期），每个继承 `orchestrator.base.BaseAgent`，用 `@register`（来自 `agents.base`）按 `name` 注册到全局 `_AGENT_REGISTRY`：`financial_agent`（财报）、`rag_agent`（知识库问答）、`flow_agent`（流水）、`risk_agent`（风控）、`strategy_agent`（策略）。`agents.base.build_registry(client=None)` 返回 `{name: 实例}`，供 Supervisor 调度。
- **`financial/`** — 一期能力：财报解析/科目标准化（`parser.py`）、指标计算（`metrics.py`：ROE/ROA/毛利率/偿债/周转/同比）、异常检测（`anomaly.py`）。
- **`rag/`** — 一期能力：标题感知切分（`chunker.py`）、向量库抽象+Chroma（`vectorstore.py`，预留 pgvector）、入库（`ingest.py`，文本与 OCR 后图片统一入库）、混合检索（`retriever.py`：向量+BM25+重排）、问答（`qa.py`：检索拼接→本地 LLM 带溯源生成）。
- **`ocr/`** — 一期能力：图像预处理（`preprocess.py`：灰度/降噪/纠偏/超分，纯 PIL 不依赖 scipy）、引擎抽象与结果结构（`engines/base.py`）、RapidOCR 引擎（`engines/rapid_ocr.py`，ONNX 无需 Paddle）、Mock 降级引擎（`engines/mock.py`）、流水线编排（`pipeline.py`：预处理→OCR→可选 VLM 兜底→结果缓存）。
- **`core/`** — 配置加载（`config.py`：YAML→类型化 dataclass，经 `_nested_to_dataclass`；全局 `settings` 单例）与 Ollama 客户端（`llm/ollama_client.py`：封装 `chat`/`embed`/`vision_chat`，OpenAI 兼容接口、依赖延迟导入）。
- **`report/`** — 三期 c2：结构化 Markdown 报告（`generator.py`，含合规免责声明）+ 图表（`visualize.py`）。

### 关键流程：多智能体协作闭环

1. `Supervisor.handle(query)` → `IntentClassifier` 识别意图，按 `_DEPENDENCIES` 补齐依赖 Agent（如命中策略/风控则自动纳入财报与流水）。
2. 对依赖做**拓扑排序**，依次执行各 Worker。
3. Supervisor 将上游结果注入 `AgentContext`，键为 `result:<agent_name>`（Worker 通过 `ctx.get("result:financial_agent")` 等读取；注意旧字段名 `xxx_output` 已弃用）。
4. 各 Agent `run(task, ctx)` 返回 `AgentMessage`；缺失 Ollama 时优雅降级为 `success=False`，不阻断整条链路。
5. `Supervisor` 按置信度加权**融合**各结论，做**冲突检测**（如基本面良好但高风险、配置与高风险背离），冲突或低置信度时标记人工复核（`human_in_the_loop`）并附免责声明。
6. 三期 `Orchestrator`（`agents/orchestrator.py`）将上述串成可迭代闭环（含 `max_iterations` 精修循环），并触发 `report.analyze` 生成报告与图表。

### 配置（`config/settings.yaml` + `core/config.py`）

所有运行参数集中在 `config/settings.yaml`，启动时由 `core.config` 映射为类型化 dataclass：`ollama`（base_url/模型名/num_ctx）、`vectorstore`、`rag`、`ocr`（engine: rapidocr|paddle|mock）、`financial`、`orchestrator`（default_agents/auto_inject_deps/max_iterations/human_review_agents/low_confidence_threshold）、`flow`/`risk`/`strategy`（各阈值与样例数据路径）、`report`。新增配置项需同步在 `core/config.py` 的对应 dataclass 上加字段，否则 YAML 中的键会被忽略。

### 重要约定与坑

- **两套 `base.py` 分工明确**：`orchestrator.base` 提供 `AgentContext`/`BaseAgent`/`_ok`/`_fail`；`agents.base` 提供注册表（`register`/`_AGENT_REGISTRY`/`build_registry`/`resolve_path`）。Worker 通常 `from orchestrator.base import BaseAgent` + `from agents.base import register, resolve_path`。
- **路径解析**：配置中的相对路径须经 `resolve_path()` 转为项目根绝对路径（根 = `src` 的上两级）；样例数据在 `data/`（由 `seed_data.py` 生成 transactions/prices CSV）。
- **数值一致性**：所有金额/比率由 `financial` 规则引擎或 pandas 计算，LLM 仅生成解读文字。
- **测试零外部依赖**：`tests/` 全部用例不要求 Ollama 运行（RAG/OCR/VLM 缺失时自动降级），可在 CI 直接跑。
- **README.md** 是更详细的使用与设计背景，改动架构前先读它与设计文档（`金融数据分析智能体设计文档.md`）。
