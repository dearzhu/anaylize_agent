# 金融数据分析智能体

基于《金融数据分析智能体设计文档 v0.2》的本地化实现，按实施路线图分阶段交付：

- **一期**：Ollama 本地模型适配 · RAG 知识库 MVP · 财报 OCR 流水线 + 指标引擎
- **二期**：Supervisor 编排框架 + 财报/流水/风控/策略/RAG Worker Agent
- **三期**：多智能体协作闭环（冲突检测 + 人在回路）+ 报告自动生成 + 可视化

> 全部模型经 Ollama 本地部署，数据不出内网；数值一律由规则引擎计算，LLM 仅做解读，不负责算数。

---

## 总体架构

```
接入层(Web/API) -> Supervisor(意图识别·路由·融合·冲突检测)
                       |
        +--------------+---------------+--------------+-------------+
        v              v               v              v             v
   财报Agent      流水Agent       风控Agent      策略Agent      RAG Agent
        |              |               |              |             |
   financial        sample_         risk            strategy       rag
   (指标/异常)     transactions    (多维评分)       (因子/配置)    (知识库)
```

- **Supervisor 不自己算数**：仅调度 + 汇总；所有计算下沉到 Worker Agent（基于 `financial` / `pandas` / 规则引擎）。
- **单一职责 Agent**：每个 Agent 只精通一个领域，通过统一 `AgentMessage`（success / output / confidence / sources / notes）通信。
- **人在回路**：涉及风险评级与交易/配置建议的结论强制标记人工复核，并附合规免责声明。

---

## 目录结构

```
anaylize_agent/
├── config/settings.yaml        # 全局配置（模型/向量库/RAG/OCR/财报/Agent/报告）
├── src/
│   ├── core/                  # 配置 + Ollama 客户端（LLM/Embedding/VLM）
│   ├── rag/                   # 切分/向量库/入库/混合检索/问答
│   ├── ocr/                   # 预处理/引擎抽象/PaddleOCR/流水线
│   ├── financial/             # 科目标准化/指标计算/异常检测
│   ├── orchestrator/          # 二期编排框架（Supervisor + Worker 模式）
│   │   ├── message.py         # AgentMessage / FusedResult 通信契约
│   │   ├── base.py            # AgentContext + BaseAgent（_ok/_fail）
│   │   ├── intent.py          # 意图识别（关键词规则 + 可选 LLM）
│   │   └── supervisor.py      # 路由 + 依赖注入 + 拓扑排序 + 融合 + 冲突检测
│   ├── agents/                # 二期/三期 Worker Agent（@register 注册）
│   │   ├── base.py            # 注册表（_AGENT_REGISTRY / build_registry）
│   │   ├── financial_agent.py # 财报分析
│   │   ├── rag_agent.py       # RAG 知识库问答（Ollama 不可用时降级）
│   │   ├── flow_agent.py      # 流水分析（资金流向/异常/画像）
│   │   ├── risk_agent.py      # 风控分析（偿付/流动性/盈利质量/合规）
│   │   └── strategy_agent.py  # 策略分析（因子/配置/回测）
│   └── report/                # 三期 c2：报告自动生成 + 可视化
│       ├── generator.py       # 结构化 Markdown 报告（含合规免责声明）
│       └── visualize.py       # 财务/同比/风险/资金流向图表
├── data/
│   ├── sample_financials/      # 示例财报（含同比）
│   ├── sample_transactions/    # 示例交易流水 CSV（由 seed_data 生成）
│   ├── sample_prices/          # 示例行情 CSV（回测，由 seed_data 生成）
│   ├── knowledge/              # RAG 样例知识
│   └── reports/               # 三期：自动生成的报告与图表（运行后生成）
├── scripts/                    # seed_data / demo_financial / demo_rag
│                                # demo_orchestrator(二期) / demo_multiagent(三期)
└── tests/                      # pytest 单测（无需 Ollama）
```

---

## 环境准备

```bash
pip install -r requirements.txt

# 启动 Ollama 并拉取模型（RAG 与 VLM 需要）
ollama pull bge-m3          # 向量化
ollama pull qwen2.5:7b      # 通用对话
ollama pull qwen2.5vl:7b   # 财报图片直读（OCR 兜底）
# 可选：ollama pull deepseek-r1:32b  # 深度推理

# OCR 引擎（默认 rapidocr，基于 ONNX、无需 Paddle；不装则自动降级为 mock）
pip install rapidocr-onnxruntime
```

> 未安装 OCR 引擎 / 未启动 Ollama 时，相关链路会自动降级或跳过，保证整条多智能体链路在无 GPU、无模型环境也能联调。

---

## 快速验证

```bash
# 0) 生成样例流水/行情数据（确定性，可重复运行）
python scripts/seed_data.py

# 1) 财报指标 + 异常检测（纯本地，无需 Ollama）
python scripts/demo_financial.py

# 2) 单元测试（含多智能体协作 + 报告，无需 Ollama）
pytest tests/ -q

# 3) 二期演示：Supervisor 编排 + 各 Worker Agent
python scripts/demo_orchestrator.py

# 4) 三期演示：多智能体协作闭环 + 报告自动生成 + 可视化
python scripts/demo_multiagent.py

# 5) RAG 入库 + 问答（需 Ollama 已启动）
python scripts/demo_rag.py
```

---

## 三期能力说明（多智能体协作闭环 + 报告可视化）

### 通信契约
各 Agent 间通过统一结构的 `AgentMessage`（success / output / confidence / sources / notes）通信，
`FusedResult` 汇总所有 AgentMessage，供上层消费与序列化。

### 协作闭环（Orchestrator.Supervisor.handle）
1. **意图识别**：`IntentClassifier` 按关键词路由到相关 Agent，并补齐依赖；
2. **依赖注入 + 拓扑排序**：风控依赖财报/流水、策略依赖财报/风控/流水，自动排序执行；
3. **结果融合**：按置信度加权融合各 Agent 结论；
4. **冲突检测**：识别 Agent 间相互矛盾的结论（如基本面良好但高风险、配置建议与高风险背离）；
5. **人在回路**：涉及风险评级 / 交易配置建议或存在冲突 / 低置信度时，强制标记 `human_in_the_loop` 并附免责声明。

### 报告自动生成 + 可视化（c2）
`report.analyze(query)` 串联上述闭环，并生成：
- 结构化 Markdown 报告（综合结论、各 Agent 结论、冲突与复核、风险提示、图表、合规免责声明）；
- 图表（财务比率、同比变动、风险雷达、资金流向），保存至 `data/reports/figures`。

### 关键配置（config/settings.yaml）
- `orchestrator`：默认管线、是否依赖注入、人工复核 Agent、低置信度阈值
- `flow` / `risk` / `strategy`：各 Agent 的阈值与样例数据路径
- `report`：报告与图表输出目录

---

## 一期 / 二期已知边界（后续迭代）

- PDF 拆分（图片型 PDF）需接入 `pdf2image`/`pymupdf`，一期提供 `process_pdf` 占位。
- 真实版面分析依赖 PP-Structure，已封装但未在此环境实测。
- 重排（Rerank）当前为向量+BM25 分数融合，可接入 Cross-Encoder。
- 编排当前为自研轻量状态机（无外部依赖）；如需要可平滑替换为 LangGraph / AutoGen。
- pgvector 后端接口已预留（`vectorstore.get_vectorstore`），生产化阶段接入。
