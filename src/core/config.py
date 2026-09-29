"""配置加载：读取 config/settings.yaml，提供全局 settings 对象。"""
import os
from dataclasses import dataclass, field
from typing import Any, List

import yaml

_DEFAULT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "settings.yaml",
)


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b"
    reasoning_model: str = "deepseek-r1:32b"
    embed_model: str = "bge-m3"
    vlm_model: str = "qwen2.5-vl:7b"
    temperature: float = 0.1
    num_ctx: int = 8192


@dataclass
class VectorStoreConfig:
    type: str = "chroma"
    persist_dir: str = "./data/vectordb"
    collection: str = "finance_kb"
    distance: str = "cosine"
    pg_dsn: str = ""


@dataclass
class RAGConfig:
    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k: int = 6
    rerank_top_n: int = 4


@dataclass
class OCRConfig:
    engine: str = "paddle"
    dpi: int = 200
    use_vlm_fallback: bool = True


@dataclass
class FinancialConfig:
    anomaly_yoy_threshold: float = 0.30
    cash_profit_ratio_min: float = 0.70


@dataclass
class OrchestratorConfig:
    default_agents: List[str] = field(default_factory=lambda: [
        "financial_agent", "rag_agent", "flow_agent", "risk_agent", "strategy_agent"
    ])
    parallel: bool = True
    auto_inject_deps: bool = True
    max_iterations: int = 3
    human_review_agents: List[str] = field(default_factory=lambda: ["risk_agent", "strategy_agent"])
    low_confidence_threshold: float = 0.5


@dataclass
class FlowConfig:
    large_txn_multiplier: float = 3.0
    top_n_counterparties: int = 5
    data_path: str = "./data/sample_transactions/transactions.csv"


@dataclass
class RiskConfig:
    current_ratio_warn: float = 1.0
    current_ratio_risk: float = 0.5
    asset_liab_warn: float = 0.70
    asset_liab_risk: float = 0.85
    roe_warn: float = 0.05


@dataclass
class StrategyConfig:
    risk_free_rate: float = 0.02
    momentum_window: int = 20
    data_path: str = "./data/sample_prices/prices.csv"


@dataclass
class ReportConfig:
    """三期：报告自动生成 + 可视化 配置。"""
    output_dir: str = "./data/reports"
    fig_dir: str = "./data/reports/figures"


@dataclass
class Settings:
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    vectorstore: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    financial: FinancialConfig = field(default_factory=FinancialConfig)
    orchestrator: OrchestratorConfig = field(default_factory=OrchestratorConfig)
    flow: FlowConfig = field(default_factory=FlowConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    report: ReportConfig = field(default_factory=ReportConfig)


def _nested_to_dataclass(data: dict, cls: type) -> Any:
    known = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    kwargs = {}
    for k, v in data.items():
        if k in known and isinstance(v, dict):
            kwargs[k] = _nested_to_dataclass(v, known[k])
        else:
            kwargs[k] = v
    return cls(**kwargs)


def load_settings(path: str | None = None) -> Settings:
    path = path or os.environ.get("FINANCE_AGENT_CONFIG", _DEFAULT_PATH)
    if not os.path.exists(path):
        return Settings()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return _nested_to_dataclass(raw, Settings)


settings = load_settings()
