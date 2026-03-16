from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from memory_eval.eval_core.adapter_protocol import RetrievalAdapterProtocol
from memory_eval.eval_core.llm_assist import LLMAssistConfig, llm_judge_retrieval_noise
from memory_eval.eval_core.models import EvalSample, EvaluatorConfig, ProbeResult
from memory_eval.eval_core.utils import rank_and_hit_indices, text_match


@dataclass(frozen=True)
class RetrievalProbeInput:
    """
    Retrieval probe explicit input.
    检索探针显式输入：Q + C_original + F_key。
    """

    question: str
    retrieved_items: List[Dict[str, Any]]
    f_key: List[str]
    task_type: str


def _normalize_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for it in items:
        out.append(
            {
                "id": str(it.get("id", "")),
                "text": str(it.get("text", "")),
                "score": float(it.get("score", 0.0) or 0.0),
                "meta": dict(it.get("meta", {})) if isinstance(it.get("meta", {}), dict) else {},
            }
        )
    return out


def evaluate_retrieval_probe_with_adapter(
    sample: EvalSample,
    adapter: RetrievalAdapterProtocol,
    run_ctx: Any,
    cfg: EvaluatorConfig,
    top_k: int,
    s_enc: Optional[str] = None,
) -> ProbeResult:
    """
    Adapter-integrated retrieval probe entrypoint.
    检索探针入口：由适配器提供原始检索结果 C_original。
    """
    c_original = _normalize_items(adapter.retrieve_original(run_ctx, sample.question, top_k))
    return evaluate_retrieval_probe(
        RetrievalProbeInput(
            question=sample.question,
            retrieved_items=c_original,
            f_key=list(sample.f_key),
            task_type=sample.task_type,
        ),
        cfg=cfg,
        s_enc=s_enc,
    )


def evaluate_retrieval_probe(inp: RetrievalProbeInput, cfg: EvaluatorConfig, s_enc: Optional[str] = None) -> ProbeResult:
    """
    Pure retrieval probe logic with explicit input.
    纯检索探针逻辑：显式输入 Q + C_original + F_key。
    """
    items = _normalize_items(inp.retrieved_items)

    if inp.task_type == "NEG":
        top_score = float(items[0].get("score", 0.0)) if items else 0.0
        noise_by_score = top_score >= cfg.neg_noise_score_threshold
        llm_noise_reason = None
        if cfg.use_llm_assist and items:
            j = llm_judge_retrieval_noise(
                LLMAssistConfig(
                    api_key=cfg.llm_api_key,
                    base_url=cfg.llm_base_url,
                    model=cfg.llm_model,
                    temperature=cfg.llm_temperature,
                ),
                query=inp.question,
                retrieved_items=items,
            )
            if isinstance(j, dict):
                llm_noise_reason = j
                noise_by_score = noise_by_score or bool(j.get("is_noise", False))

        if noise_by_score:
            return ProbeResult(
                probe="ret",
                state="NOISE",
                defects=["NIR"],
                attrs={"rank_index": 10**9, "snr": 0.0, "top_score": top_score},
                evidence={
                    "reason": "NEG sample hit high misleading retrieval noise.",
                    "threshold": cfg.neg_noise_score_threshold,
                    "top_item": items[0] if items else None,
                    "llm_noise_judgement": llm_noise_reason,
                },
            )
        return ProbeResult(
            probe="ret",
            state="MISS",
            defects=[],
            attrs={"rank_index": 10**9, "snr": 0.0, "top_score": top_score},
            evidence={"reason": "NEG sample has no high-noise retrieval evidence.", "llm_noise_judgement": llm_noise_reason},
        )

    # POS tasks
    rank, hit_indices = rank_and_hit_indices(items, inp.f_key)
    hit_count = len(hit_indices)
    snr = hit_count / (len(items) + 1e-6)

    if hit_count <= 0:
        defects: List[str] = []
        # RF should only be assigned if encoding is not MISS (per final metric definition).
        if s_enc is None or s_enc != "MISS":
            defects.append("RF")
        return ProbeResult(
            probe="ret",
            state="MISS",
            defects=defects,
            attrs={"rank_index": rank, "snr": snr},
            evidence={
                "reason": "No retrieval hit for f_key in C_original.",
                "f_key": list(inp.f_key),
                "top_items": items[:5],
                "rf_gate_s_enc": s_enc,
            },
        )

    defects = []
    if rank > cfg.tau_rank:
        defects.append("LATE")
    if snr < cfg.tau_snr:
        defects.append("NOI")
    return ProbeResult(
        probe="ret",
        state="HIT",
        defects=defects,
        attrs={"rank_index": rank, "snr": snr, "hit_count": hit_count},
        evidence={
            "reason": "Retrieved items contain key facts.",
            "f_key": list(inp.f_key),
            "hit_indices": hit_indices,
            "snr_numerator": hit_count,
            "snr_denominator": len(items),
            "top_items": items[:5],
        },
    )
