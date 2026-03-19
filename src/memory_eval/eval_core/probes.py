from __future__ import annotations

from typing import Any, Dict, List

from memory_eval.eval_core.encoding import EncodingProbeInput, evaluate_encoding_probe
from memory_eval.eval_core.generation import GenerationProbeInput, evaluate_generation_probe
from memory_eval.eval_core.models import EvalSample, EvaluatorConfig, ProbeResult, RetrievedItem
from memory_eval.eval_core.retrieval import RetrievalProbeInput, evaluate_retrieval_probe


def run_encoding_probe(sample: EvalSample, memory_view: List[Dict[str, Any]], cfg: EvaluatorConfig | None = None) -> ProbeResult:
    """
    Encoding probe (P_enc), independent from retrieval/generation.
    编码探针（P_enc），与检索/生成探针输入独立，可并行执行。
    """
    return evaluate_encoding_probe(
        EncodingProbeInput(
            question=sample.question,
            memory_corpus=memory_view,
            f_key=list(sample.f_key),
            task_type=sample.task_type,
            evidence_texts=list(sample.evidence_with_time or sample.evidence_texts),
        ),
        candidate_records=memory_view,
        cfg=cfg,
    )


def run_retrieval_probe(sample: EvalSample, retrieved_items: List[RetrievedItem], cfg: EvaluatorConfig) -> ProbeResult:
    """
    Retrieval probe (P_ret), fully independent from encoding/gen inputs.
    检索探针（P_ret），完全独立计算；与编码层责任归因在汇总阶段融合。
    """
    return evaluate_retrieval_probe(
        RetrievalProbeInput(
            question=sample.question,
            retrieved_items=[{"id": it.id, "text": it.text, "score": it.score, "meta": dict(it.meta)} for it in retrieved_items],
            f_key=list(sample.f_key),
            task_type=sample.task_type,
            evidence_texts=list(sample.evidence_with_time or sample.evidence_texts),
        ),
        cfg=cfg,
        s_enc=None,
    )


def run_generation_probe(sample: EvalSample, answer_oracle: str, cfg: EvaluatorConfig, answer_online: str = "") -> ProbeResult:
    """
    Generation probe (P_gen), independent from encoding/retrieval.
    生成探针（P_gen）独立执行，与编码检索并行。
    """
    return evaluate_generation_probe(
        GenerationProbeInput(
            question=sample.question,
            oracle_context=sample.oracle_context,
            answer_online=str(answer_online or ""),
            answer_oracle=str(answer_oracle or ""),
            answer_gold=sample.answer_gold,
            task_type=sample.task_type,
        ),
        cfg=cfg,
    )
