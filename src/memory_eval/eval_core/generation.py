from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from memory_eval.eval_core.adapter_protocol import GenerationAdapterProtocol
from memory_eval.eval_core.llm_assist import LLMAssistConfig, llm_judge_generation_answer
from memory_eval.eval_core.models import EvalSample, EvaluatorConfig, ProbeResult
from memory_eval.eval_core.utils import grounding_overlap, is_abstain, normalize_text


@dataclass(frozen=True)
class GenerationProbeInput:
    """
    Generation probe explicit input.
    生成探针显式输入：Q + C_oracle + A_oracle + A_gold。
    """

    question: str
    oracle_context: str
    answer_oracle: str
    answer_gold: str
    task_type: str


def evaluate_generation_probe_with_adapter(
    sample: EvalSample,
    adapter: GenerationAdapterProtocol,
    run_ctx: Any,
    cfg: EvaluatorConfig,
) -> ProbeResult:
    """
    Adapter-integrated generation probe entrypoint.
    生成探针入口：通过适配器调用原始记忆系统模型，基于 C_oracle 生成 A_oracle。
    """
    answer_oracle = adapter.generate_oracle_answer(run_ctx, sample.question, sample.oracle_context)
    return evaluate_generation_probe(
        GenerationProbeInput(
            question=sample.question,
            oracle_context=sample.oracle_context,
            answer_oracle=str(answer_oracle or ""),
            answer_gold=sample.answer_gold,
            task_type=sample.task_type,
        ),
        cfg=cfg,
    )


def _is_correct_rule(inp: GenerationProbeInput) -> bool:
    if inp.task_type == "NEG":
        return is_abstain(inp.answer_oracle)
    a = normalize_text(inp.answer_oracle)
    g = normalize_text(inp.answer_gold)
    if not g:
        return False
    return a == g or g in a


def evaluate_generation_probe(inp: GenerationProbeInput, cfg: EvaluatorConfig) -> ProbeResult:
    """
    Pure generation probe logic:
    1) produce/receive A_oracle
    2) compare A_oracle and A_gold (rule or LLM judge)
    纯生成探针逻辑：先拿 A_oracle，再与 A_gold 比较。
    """
    llm_judgement: Dict[str, Any] | None = None
    correct = _is_correct_rule(inp)

    if cfg.use_llm_assist:
        llm_judgement = llm_judge_generation_answer(
            LLMAssistConfig(
                api_key=cfg.llm_api_key,
                base_url=cfg.llm_base_url,
                model=cfg.llm_model,
                temperature=cfg.llm_temperature,
            ),
            question=inp.question,
            oracle_context=inp.oracle_context,
            answer_oracle=inp.answer_oracle,
            answer_gold=inp.answer_gold,
            task_type=inp.task_type,
        )
        if isinstance(llm_judgement, dict) and "correct" in llm_judgement:
            correct = bool(llm_judgement.get("correct", False))

    overlap, overlap_meta = grounding_overlap(inp.answer_oracle, inp.oracle_context)

    if correct:
        return ProbeResult(
            probe="gen",
            state="PASS",
            defects=[],
            attrs={"grounding_overlap": overlap},
            evidence={
                "reason": "A_oracle is judged correct against A_gold.",
                "answer_oracle": inp.answer_oracle,
                "answer_gold": inp.answer_gold,
                "overlap_meta": overlap_meta,
                "llm_judgement": llm_judgement,
            },
        )

    # FAIL classification
    if inp.task_type == "NEG":
        return ProbeResult(
            probe="gen",
            state="FAIL",
            defects=["GH"],
            attrs={"grounding_overlap": overlap},
            evidence={
                "reason": "NEG sample should abstain but oracle answer is non-abstain.",
                "answer_oracle": inp.answer_oracle,
                "answer_gold": inp.answer_gold,
                "llm_judgement": llm_judgement,
            },
        )

    # POS fail => GF or GRF
    if isinstance(llm_judgement, dict):
        sub = str(llm_judgement.get("substate", "")).upper()
        if sub in {"GF", "GRF"}:
            return ProbeResult(
                probe="gen",
                state="FAIL",
                defects=[sub],
                attrs={"grounding_overlap": overlap},
                evidence={
                    "reason": "LLM-assist subtype decision.",
                    "answer_oracle": inp.answer_oracle,
                    "answer_gold": inp.answer_gold,
                    "llm_judgement": llm_judgement,
                    "overlap_meta": overlap_meta,
                },
            )

    # Rule fallback subtype
    if overlap < 0.1:
        defect = "GF"
        reason = "POS fail appears ungrounded in oracle context."
    else:
        defect = "GRF"
        reason = "POS fail appears grounded but still incorrect (reasoning failure)."
    return ProbeResult(
        probe="gen",
        state="FAIL",
        defects=[defect],
        attrs={"grounding_overlap": overlap},
        evidence={
            "reason": reason,
            "answer_oracle": inp.answer_oracle,
            "answer_gold": inp.answer_gold,
            "overlap_meta": overlap_meta,
            "llm_judgement": llm_judgement,
        },
    )
