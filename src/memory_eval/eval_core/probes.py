from __future__ import annotations

from typing import Any, Dict, List

from memory_eval.eval_core.encoding import EncodingProbeInput, evaluate_encoding_probe
from memory_eval.eval_core.models import EvalSample, EvaluatorConfig, ProbeResult, RetrievedItem
from memory_eval.eval_core.retrieval import RetrievalProbeInput, evaluate_retrieval_probe
from memory_eval.eval_core.utils import (
    grounding_overlap,
    is_abstain,
)


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
        ),
        cfg=cfg,
        s_enc=None,
    )


def run_generation_probe(sample: EvalSample, answer_oracle: str, cfg: EvaluatorConfig) -> ProbeResult:
    """
    Generation probe (P_gen), independent from encoding/retrieval.
    生成探针（P_gen）独立执行，与编码检索并行。
    """
    ans = str(answer_oracle or "").strip()
    gold = str(sample.answer_gold or "").strip()

    if sample.task_type == "NEG":
        abstain = is_abstain(ans)
        if abstain:
            return ProbeResult(
                probe="gen",
                state="PASS",
                defects=[],
                evidence={"reason": "NEG sample correctly abstained.", "answer_oracle": ans},
            )
        return ProbeResult(
            probe="gen",
            state="FAIL",
            defects=["GH"],
            evidence={"reason": "NEG sample did not abstain.", "answer_oracle": ans},
        )

    # POS path
    norm_ans = ans.lower().strip()
    norm_gold = gold.lower().strip()
    direct_correct = norm_gold and (norm_ans == norm_gold or norm_gold in norm_ans)
    overlap, overlap_meta = grounding_overlap(ans, sample.oracle_context)

    if direct_correct:
        return ProbeResult(
            probe="gen",
            state="PASS",
            defects=[],
            attrs={"grounding_overlap": overlap},
            evidence={"reason": "Oracle answer matches gold.", "overlap_meta": overlap_meta},
        )

    # Heuristic fail split:
    # low grounding -> GF, otherwise GRF
    if overlap < 0.1:
        return ProbeResult(
            probe="gen",
            state="FAIL",
            defects=["GF"],
            attrs={"grounding_overlap": overlap},
            evidence={
                "reason": "Oracle answer appears ungrounded in oracle context.",
                "answer_oracle": ans,
                "answer_gold": gold,
                "overlap_meta": overlap_meta,
            },
        )
    return ProbeResult(
        probe="gen",
        state="FAIL",
        defects=["GRF"],
        attrs={"grounding_overlap": overlap},
        evidence={
            "reason": "Grounded but still incorrect, likely reasoning failure.",
            "answer_oracle": ans,
            "answer_gold": gold,
            "overlap_meta": overlap_meta,
        },
    )
