from __future__ import annotations

from dataclasses import dataclass
import re
from dataclasses import field
from typing import Any, Dict, List, Optional

from memory_eval.eval_core.adapter_protocol import EncodingAdapterProtocol
from memory_eval.eval_core.llm_assist import LLMAssistConfig, llm_judge_encoding_storage, llm_judge_fact_match
from memory_eval.eval_core.models import EvalSample, EvaluatorConfig, ProbeResult
from memory_eval.eval_core.utils import looks_ambiguous, normalize_text, text_match


@dataclass(frozen=True)
class EncodingProbeInput:
    """
    Explicit input contract for encoding probe.
    编码探针显式输入：Q + M + F_key。
    """

    question: str
    memory_corpus: List[Dict[str, Any]]
    f_key: List[str]
    task_type: str
    evidence_texts: List[str] = field(default_factory=list)


def _normalize_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in records:
        out.append(
            {
                "id": str(r.get("id", "")),
                "text": str(r.get("text", "")),
                "meta": dict(r.get("meta", {})) if isinstance(r.get("meta", {}), dict) else {},
            }
        )
    return out


def _fallback_find_records(question: str, f_key: List[str], memory_corpus: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fallback matcher if adapter returns empty candidate records.
    兜底匹配：当适配器未返回候选时，评估层按规则扫描全量库。
    """
    candidates: List[Dict[str, Any]] = []
    for m in memory_corpus:
        txt = str(m.get("text", ""))
        q_hit = text_match(question, txt)
        f_hit = any(text_match(f, txt) for f in f_key if f)
        if q_hit or f_hit:
            candidates.append(m)
    return candidates


def _fact_match(fact: str, text: str) -> bool:
    """
    Safer fact matcher to avoid accidental short-token collisions (e.g., "he" in "she").
    更安全的事实匹配，避免短词误匹配（如 "he" 命中 "she"）。
    """
    nf = normalize_text(fact)
    nt = normalize_text(text)
    if not nf or not nt:
        return False
    if len(nf) <= 3:
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", nt)
        return nf in tokens
    # Fact-to-memory direction only:
    # the memory text should contain the fact, not the reverse.
    # 仅允许“记忆文本包含事实”，避免短文本反向命中长事实。
    return nf == nt or nf in nt


def evaluate_encoding_probe_with_adapter(
    sample: EvalSample,
    adapter: EncodingAdapterProtocol,
    run_ctx: Any,
    cfg: Optional[EvaluatorConfig] = None,
) -> ProbeResult:
    """
    Encoding probe entrypoint with adapter integration.
    编码探针入口：通过适配器拿到 M，并让适配器先执行 Q/F_key 匹配。
    """
    # 1) Get full memory corpus M from adapter / 从适配器导出全量记忆库 M
    memory_corpus = _normalize_records(adapter.export_full_memory(run_ctx))
    # 2) Optional hybrid high-recall candidates first / 可选混合高召回候选
    candidates: List[Dict[str, Any]] = []
    hybrid_fn = getattr(adapter, "hybrid_retrieve_candidates", None)
    if callable(hybrid_fn):
        try:
            candidates = _normalize_records(
                hybrid_fn(
                    run_ctx=run_ctx,
                    query=sample.question,
                    f_key=list(sample.f_key),
                    evidence_texts=list(sample.evidence_with_time or sample.evidence_texts),
                    top_n=100,
                )
            )
        except Exception as exc:
            if cfg and cfg.strict_adapter_call:
                raise RuntimeError(f"encoding hybrid_retrieve_candidates failed: {exc}") from exc
            candidates = []

    # 3) Adapter-side traversal and matching / 适配器层执行脚本匹配逻辑
    if not candidates:
        candidates = _normalize_records(adapter.find_memory_records(run_ctx, sample.question, sample.f_key, memory_corpus))
    # 4) Evaluator fallback scan if adapter returns none / 若适配器无候选则评估层兜底
    if not candidates and memory_corpus and not (cfg and cfg.disable_rule_fallback):
        candidates = _fallback_find_records(sample.question, sample.f_key, memory_corpus)
    evidence_texts = list(getattr(sample, "evidence_with_time", []) or getattr(sample, "evidence_texts", []))

    return evaluate_encoding_probe(
        EncodingProbeInput(
            question=sample.question,
            memory_corpus=memory_corpus,
            f_key=list(sample.f_key),
            task_type=sample.task_type,
            evidence_texts=evidence_texts,
        ),
        candidate_records=candidates,
        cfg=cfg,
    )


def evaluate_encoding_probe(
    inp: EncodingProbeInput,
    candidate_records: Optional[List[Dict[str, Any]]] = None,
    cfg: Optional[EvaluatorConfig] = None,
) -> ProbeResult:
    """
    Pure encoding probe logic with explicit input (Q + M + F_key).
    纯编码探针逻辑：显式输入 Q + M + F_key。
    """
    memory_corpus = _normalize_records(inp.memory_corpus)
    candidates = _normalize_records(candidate_records or [])
    if not candidates and memory_corpus and not (cfg and cfg.disable_rule_fallback):
        candidates = _fallback_find_records(inp.question, inp.f_key, memory_corpus)

    llm_encoding_judgement: Dict[str, Any] | None = None
    if cfg and cfg.use_llm_assist:
        llm_encoding_judgement = llm_judge_encoding_storage(
            LLMAssistConfig(
                api_key=cfg.llm_api_key,
                base_url=cfg.llm_base_url,
                model=cfg.llm_model,
                temperature=cfg.llm_temperature,
            ),
            query=inp.question,
            f_key=list(inp.f_key),
            evidence_texts=list(inp.evidence_texts),
            candidates=candidates,
            task_type=inp.task_type,
        )
        if cfg.require_llm_judgement and not isinstance(llm_encoding_judgement, dict):
            raise RuntimeError("encoding llm judgement failed or empty")

    # Prefer adapter+LLM holistic storage judgement when available.
    # 有可用的结构化 LLM 判定时优先采用（并保留规则兜底）。
    if isinstance(llm_encoding_judgement, dict):
        s = str(llm_encoding_judgement.get("encoding_state", "")).upper()
        defects = [str(x).upper() for x in llm_encoding_judgement.get("defects", []) if str(x).strip()]
        if s in {"EXIST", "MISS", "CORRUPT_AMBIG", "CORRUPT_WRONG", "DIRTY"}:
            return ProbeResult(
                probe="enc",
                state=s,
                defects=defects,
                evidence={
                    "reason": str(llm_encoding_judgement.get("reasoning", "LLM holistic encoding judgement.")),
                    "memory_source": "adapter.export_full_memory",
                    "candidate_count": len(candidates),
                    "matched_candidate_ids": list(llm_encoding_judgement.get("matched_candidate_ids", [])),
                    "evidence_snippets": list(llm_encoding_judgement.get("evidence_snippets", [])),
                    "llm_encoding_judgement": llm_encoding_judgement,
                },
            )
        if cfg and cfg.require_llm_judgement and cfg.disable_rule_fallback:
            raise RuntimeError(f"encoding llm judgement returned invalid state: {s or 'EMPTY'}")

    if cfg and cfg.use_llm_assist and cfg.disable_rule_fallback:
        raise RuntimeError("encoding strict mode rejects rule fallback")

    # NEG definition (should abstain): if query-related memory exists, treat as DIRTY.
    # NEG 定义（应拒答）：若出现 query 相关记忆，视为污染 DIRTY。
    if inp.task_type == "NEG":
        if candidates:
            return ProbeResult(
                probe="enc",
                state="DIRTY",
                defects=["DMP"],
                evidence={
                    "reason": "NEG sample has query/f_key-related memory candidates.",
                    "memory_source": "adapter.export_full_memory",
                    "candidate_count": len(candidates),
                    "candidates": candidates[:10],
                },
            )
        return ProbeResult(
            probe="enc",
            state="MISS",
            defects=[],
            evidence={
                "reason": "NEG sample has no query/f_key-related memory candidates.",
                "memory_source": "adapter.export_full_memory",
                "candidate_count": 0,
            },
        )

    # POS path
    if not inp.f_key:
        return ProbeResult(
            probe="enc",
            state="MISS",
            defects=["EM"],
            evidence={
                "reason": "POS sample has empty f_key.",
                "memory_source": "adapter.export_full_memory",
                "candidate_count": len(candidates),
            },
        )

    matched_facts: Dict[str, List[Dict[str, Any]]] = {}
    unmatched_facts: List[str] = []
    ambiguity_hits: List[Dict[str, Any]] = []
    for fact in inp.f_key:
        fact_matches: List[Dict[str, Any]] = []
        for r in candidates:
            base_match = _fact_match(fact, str(r.get("text", "")))
            llm_match_reason = None
            if cfg and cfg.use_llm_assist and not base_match:
                lj = llm_judge_fact_match(
                    LLMAssistConfig(
                        api_key=cfg.llm_api_key,
                        base_url=cfg.llm_base_url,
                        model=cfg.llm_model,
                        temperature=cfg.llm_temperature,
                    ),
                    question=inp.question,
                    fact=fact,
                    candidate_text=str(r.get("text", "")),
                )
                if isinstance(lj, dict):
                    llm_match_reason = lj
                    base_match = bool(lj.get("match", False))

            if base_match:
                fact_matches.append(r)
                if looks_ambiguous(str(r.get("text", ""))):
                    ambiguity_hits.append(r)
                if llm_match_reason is not None:
                    r.setdefault("meta", {})
                    if isinstance(r["meta"], dict):
                        r["meta"]["llm_match_reason"] = llm_match_reason
        if fact_matches:
            matched_facts[fact] = fact_matches
        else:
            unmatched_facts.append(fact)

    if not matched_facts:
        return ProbeResult(
            probe="enc",
            state="MISS",
            defects=["EM"],
            evidence={
                "reason": "No key-fact match in candidate records.",
                "memory_source": "adapter.export_full_memory",
                "candidate_count": len(candidates),
                "unmatched_facts": unmatched_facts,
            },
        )

    if unmatched_facts:
        if ambiguity_hits:
            return ProbeResult(
                probe="enc",
                state="CORRUPT_AMBIG",
                defects=["EA"],
                evidence={
                    "reason": "Partial key-fact match with ambiguous memory text.",
                    "memory_source": "adapter.export_full_memory",
                    "matched_facts": matched_facts,
                    "unmatched_facts": unmatched_facts,
                    "ambiguity_hits": ambiguity_hits[:10],
                },
            )
        return ProbeResult(
            probe="enc",
            state="CORRUPT_WRONG",
            defects=["EW"],
            evidence={
                "reason": "Partial key-fact match without ambiguity, treated as wrong/corrupt.",
                "memory_source": "adapter.export_full_memory",
                "matched_facts": matched_facts,
                "unmatched_facts": unmatched_facts,
            },
        )

    return ProbeResult(
        probe="enc",
        state="EXIST",
        defects=[],
        evidence={
            "reason": "All key facts matched in candidate records.",
            "memory_source": "adapter.export_full_memory",
            "matched_facts": matched_facts,
            "candidate_count": len(candidates),
        },
    )
