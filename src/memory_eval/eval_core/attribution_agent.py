from __future__ import annotations

from typing import Dict, List, Optional

from memory_eval.eval_core.llm_assist import LLMAssistConfig, llm_judge_attribution
from memory_eval.eval_core.models import AttributionAssessment, AttributionResult, EvalSample, EvaluatorConfig, ProbeResult
from memory_eval.eval_core.utils import ordered_defect_union


class AttributionAgent:
    name = "AttributionAgent"

    def attribute(
        self,
        sample: EvalSample,
        enc: ProbeResult,
        ret: ProbeResult,
        gen: ProbeResult,
        cfg: Optional[EvaluatorConfig] = None,
    ) -> AttributionResult:
        ret_defects = list(ret.defects)
        decision_trace: List[str] = []
        if ret.state == "MISS" and enc.state != "MISS" and "RF" not in ret_defects and sample.task_type == "POS":
            ret_defects.append("RF")
            decision_trace.append("Added RF because retrieval missed while encoding was not MISS.")
        if enc.state == "MISS" and "RF" in ret_defects:
            ret_defects = [defect for defect in ret_defects if defect != "RF"]
            decision_trace.append("Suppressed RF because encoding state is MISS.")
        merged_ret = ProbeResult(
            probe=ret.probe,
            state=ret.state,
            defects=ret_defects,
            evidence=dict(ret.evidence),
            attrs=dict(ret.attrs),
        )
        merged_defects = ordered_defect_union(enc.defects, merged_ret.defects, gen.defects)
        assessment = self._build_assessment(sample, enc, merged_ret, gen, decision_trace, cfg)
        probe_results: Dict[str, ProbeResult] = {"enc": enc, "ret": merged_ret, "gen": gen}
        return AttributionResult(
            question_id=sample.question_id,
            sample_id=sample.sample_id,
            task_type=sample.task_type,
            states={"enc": enc.state, "ret": merged_ret.state, "gen": gen.state},
            defects=merged_defects,
            probe_results=probe_results,
            attribution_evidence={
                "enc_evidence": enc.evidence,
                "ret_evidence": merged_ret.evidence,
                "gen_evidence": gen.evidence,
                "decision_trace": list(assessment.decision_trace),
                "attribution_agent": {
                    "agent_name": self.name,
                    "primary_cause": assessment.primary_cause,
                    "secondary_causes": list(assessment.secondary_causes),
                    "summary": assessment.summary,
                    "llm_payload": dict(assessment.llm_payload),
                    "cross_probe_summary": {
                        "encoding": {"state": enc.state, "defects": list(enc.defects)},
                        "retrieval": {"state": merged_ret.state, "defects": list(merged_ret.defects)},
                        "generation": {"state": gen.state, "defects": list(gen.defects)},
                    },
                },
            },
        )

    def _build_assessment(
        self,
        sample: EvalSample,
        enc: ProbeResult,
        ret: ProbeResult,
        gen: ProbeResult,
        decision_trace: List[str],
        cfg: Optional[EvaluatorConfig] = None,
    ) -> AttributionAssessment:
        primary_cause = self._primary_cause(enc, ret, gen)
        secondary_causes = [cause for cause in ("encoding", "retrieval", "generation") if cause != primary_cause and self._layer_has_issue(cause, enc, ret, gen)]
        summary = f"primary={primary_cause}; enc={enc.state}; ret={ret.state}; gen={gen.state}"
        llm_payload: Dict[str, object] = {}
        if cfg and cfg.use_llm_assist:
            llm_result = llm_judge_attribution(
                LLMAssistConfig(
                    api_key=cfg.llm_api_key,
                    base_url=cfg.llm_base_url,
                    model=cfg.llm_model,
                    temperature=cfg.llm_temperature,
                ),
                task_type=sample.task_type,
                query=sample.question,
                answer_gold=sample.answer_gold,
                enc_summary={"state": enc.state, "defects": list(enc.defects), "reason": enc.evidence.get("reason", "")},
                ret_summary={"state": ret.state, "defects": list(ret.defects), "reason": ret.evidence.get("reason", "")},
                gen_summary={"state": gen.state, "defects": list(gen.defects), "reason": gen.evidence.get("reason", "")},
                must_succeed=False,
            )
            if isinstance(llm_result, dict):
                candidate_primary = str(llm_result.get("primary_cause", "")).strip().lower()
                if candidate_primary in {"encoding", "retrieval", "generation", "none"}:
                    primary_cause = candidate_primary
                secondary_llm = [str(x).strip().lower() for x in llm_result.get("secondary_causes", []) if str(x).strip()]
                secondary_causes = [x for x in secondary_llm if x in {"encoding", "retrieval", "generation"} and x != primary_cause]
                decision_trace.extend([str(x) for x in llm_result.get("decision_trace", []) if str(x).strip()])
                summary = str(llm_result.get("summary", summary))
                llm_payload = dict(llm_result)
        return AttributionAssessment(
            primary_cause=primary_cause,
            secondary_causes=secondary_causes,
            decision_trace=list(decision_trace),
            summary=summary,
            llm_payload=llm_payload,
        )

    def _primary_cause(self, enc: ProbeResult, ret: ProbeResult, gen: ProbeResult) -> str:
        if enc.state in {"MISS", "CORRUPT_AMBIG", "CORRUPT_WRONG", "DIRTY"}:
            return "encoding"
        if ret.state in {"MISS", "NOISE"} or ret.defects:
            return "retrieval"
        if gen.state == "FAIL" or gen.defects:
            return "generation"
        return "none"

    def _layer_has_issue(self, layer: str, enc: ProbeResult, ret: ProbeResult, gen: ProbeResult) -> bool:
        if layer == "encoding":
            return enc.state in {"MISS", "CORRUPT_AMBIG", "CORRUPT_WRONG", "DIRTY"} or bool(enc.defects)
        if layer == "retrieval":
            return ret.state in {"MISS", "NOISE"} or bool(ret.defects)
        if layer == "generation":
            return gen.state == "FAIL" or bool(gen.defects)
        return False
