from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


# -----------------------------
# Core states / 缺陷状态定义
# -----------------------------
ENC_STATES = {"EXIST", "MISS", "CORRUPT_AMBIG", "CORRUPT_WRONG", "DIRTY"}
RET_STATES = {"HIT", "MISS", "NOISE"}
GEN_STATES = {"PASS", "FAIL"}

DEFECT_ORDER = ["EM", "EA", "EW", "DMP", "RF", "LATE", "NOI", "NIR", "GH", "GF", "GRF"]


@dataclass(frozen=True)
class EvalSample:
    """
    Unified evaluation sample contract.
    统一评估样本契约，评估层只依赖这里的字段。
    """

    sample_id: str
    question_id: str
    question: str
    answer_gold: str
    task_type: str  # POS | NEG
    f_key: List[str]
    oracle_context: str
    evidence_ids: List[str] = field(default_factory=list)
    evidence_texts: List[str] = field(default_factory=list)
    evidence_with_time: List[str] = field(default_factory=list)
    construction_evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievedItem:
    """
    Adapter-normalized retrieval item.
    适配器标准化后的检索条目。
    """

    id: str
    text: str
    score: float = 0.0
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdapterTrace:
    """
    Inputs from adapter layer to evaluator.
    适配器层提供给评估层的统一观测输入。
    """

    memory_view: List[Dict[str, Any]]
    retrieved_items: List[RetrievedItem]
    answer_online: str = ""
    answer_oracle: str = ""
    raw_trace: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProbeResult:
    """
    Generic probe result.
    通用探针输出：状态 + 缺陷 + 证据 + 属性。
    """

    probe: str  # enc | ret | gen
    state: str
    defects: List[str]
    evidence: Dict[str, Any] = field(default_factory=dict)
    attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AttributionResult:
    """
    Final per-sample attribution output.
    单样本最终归因输出，包含三层证据。
    """

    question_id: str
    sample_id: str
    task_type: str
    states: Dict[str, str]
    defects: List[str]
    probe_results: Dict[str, ProbeResult]
    attribution_evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question_id": self.question_id,
            "sample_id": self.sample_id,
            "task_type": self.task_type,
            "states": dict(self.states),
            "defects": list(self.defects),
            "probe_results": {k: asdict(v) for k, v in self.probe_results.items()},
            "attribution_evidence": dict(self.attribution_evidence),
        }


@dataclass(frozen=True)
class EvaluatorConfig:
    """
    Rule-mode evaluator configuration.
    规则模式评估器配置。
    """

    tau_rank: int = 5
    tau_snr: float = 0.2
    neg_noise_score_threshold: float = 0.15
    max_workers: int = 3  # parallel probes / 三探针并行线程数
    # Optional LLM-assisted probe judgments / 可选LLM辅助判定
    use_llm_assist: bool = False
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_api_key: str = ""
    llm_base_url: str = "https://vip.dmxapi.com/v1"
