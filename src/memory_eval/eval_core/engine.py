from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from memory_eval.eval_core.models import AdapterTrace, AttributionResult, EvalSample, EvaluatorConfig, ProbeResult
from memory_eval.eval_core.probes import run_encoding_probe, run_generation_probe, run_retrieval_probe
from memory_eval.eval_core.utils import ordered_defect_union


class ParallelThreeProbeEvaluator:
    """
    Three-probe evaluator with full parallel execution.
    三探针并行评估器：编码/检索/生成并行运行，提高吞吐效率。
    """

    def __init__(self, config: EvaluatorConfig | None = None):
        self.config = config or EvaluatorConfig()

    def evaluate(self, sample: EvalSample, trace: AdapterTrace) -> AttributionResult:
        """
        Evaluate one sample with three probes in parallel.
        对单样本执行并行三探针评估并汇总归因。
        """
        with ThreadPoolExecutor(max_workers=max(1, self.config.max_workers)) as pool:
            f_enc = pool.submit(run_encoding_probe, sample, trace.memory_view, self.config)
            f_ret = pool.submit(run_retrieval_probe, sample, trace.retrieved_items, self.config)
            f_gen = pool.submit(run_generation_probe, sample, trace.answer_oracle, self.config)
            enc = f_enc.result()
            ret = f_ret.result()
            gen = f_gen.result()

        # Attribution reconciliation / 归因收敛规则：
        # RF should be suppressed when source is missing at encoding layer.
        # 当编码层是 MISS 时，检索层 RF 非主要责任，做屏蔽处理。
        ret_defects = list(ret.defects)
        decision_trace = []
        if enc.state == "MISS" and "RF" in ret_defects:
            ret_defects = [d for d in ret_defects if d != "RF"]
            decision_trace.append("Suppressed RF because encoding state is MISS.")

        merged_defects = ordered_defect_union(enc.defects, ret_defects, gen.defects)

        merged_ret = ProbeResult(
            probe=ret.probe,
            state=ret.state,
            defects=ret_defects,
            evidence=ret.evidence,
            attrs=ret.attrs,
        )
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
                "decision_trace": decision_trace,
            },
        )
