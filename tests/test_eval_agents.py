from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_eval.eval_core import HighRecallRequest, HighRecallResponse
from memory_eval.eval_core.correctness_judge import judge_answer_correctness
from memory_eval.eval_core.encoding import EncodingProbeInput
from memory_eval.eval_core.encoding_agent import EncodingAgent
from memory_eval.eval_core.engine import ParallelThreeProbeEvaluator
from memory_eval.eval_core.generation import GenerationProbeInput
from memory_eval.eval_core.generation_agent import GenerationAgent
from memory_eval.eval_core.models import EvalSample, EvaluatorConfig
from memory_eval.eval_core.retrieval import RetrievalProbeInput
from memory_eval.eval_core.retrieval_agent import RetrievalAgent


def build_cfg() -> EvaluatorConfig:
    return EvaluatorConfig(
        use_llm_assist=False,
        require_llm_judgement=False,
        disable_rule_fallback=False,
        strict_adapter_call=False,
        require_online_answer=False,
        correctness_use_llm_judge=False,
        correctness_require_llm_judge=False,
        max_workers=3,
    )


class MockFullAdapter:
    def __init__(self, memory_view, retrieved_items, online_answer, oracle_answer):
        self.memory_view = memory_view
        self.retrieved_items = retrieved_items
        self.online_answer = online_answer
        self.oracle_answer = oracle_answer
        self._external_high_recall_retriever = None

    def ingest_conversation(self, session_id, user_id, turns):
        return {"session_id": session_id, "user_id": user_id, "turns": list(turns)}

    def export_full_memory(self, run_ctx):
        return list(self.memory_view)

    def find_memory_records(self, run_ctx, query, f_key, memory_corpus):
        return [item for item in memory_corpus if any(fact.lower() in item["text"].lower() for fact in f_key)]

    def hybrid_retrieve_candidates(self, run_ctx, query, f_key, evidence_texts, top_n=100):
        return [item for item in self.memory_view if any(fact.lower() in item["text"].lower() for fact in f_key)]

    def retrieve_original(self, run_ctx, query, top_k):
        return list(self.retrieved_items)[:top_k]

    def generate_online_answer(self, run_ctx, query):
        return self.online_answer

    def generate_oracle_answer(self, run_ctx, query, oracle_context):
        return self.oracle_answer

    def set_external_high_recall_retriever(self, retriever):
        self._external_high_recall_retriever = retriever

    def get_external_high_recall_retriever(self):
        return self._external_high_recall_retriever


class MockHighRecallRetriever:
    def retrieve(self, request: HighRecallRequest) -> HighRecallResponse:
        return HighRecallResponse(
            candidates=[{"id": "ext-1", "text": "昨天 Caroline 去了 LGBTQ support group。", "score": 1.0, "meta": {"source": "external"}}],
            diagnostics={"provider": "mock"},
        )


class QueryAwareAdapter(MockFullAdapter):
    def retrieve_original(self, run_ctx, query, top_k):
        if "LGBTQ support group" in str(query):
            return [{"id": "rk-1", "text": "LGBTQ support group", "score": 0.95, "meta": {"query_type": "f_key"}}]
        return [{"id": "rq-1", "text": "昨天 Caroline 去了 LGBTQ support group。", "score": 0.9, "meta": {"query_type": "question"}}]


class EvalAgentTests(unittest.TestCase):
    def setUp(self):
        self.cfg = build_cfg()
        self.pos_sample = EvalSample(
            sample_id="s-pos",
            question_id="q-pos",
            question="Caroline 昨天去了哪里？",
            answer_gold="Caroline 昨天去了 LGBTQ support group。",
            task_type="POS",
            f_key=["Caroline", "LGBTQ support group"],
            oracle_context="原文写道 Caroline 昨天去了 LGBTQ support group。",
            evidence_texts=["Caroline 昨天去了 LGBTQ support group。"],
            evidence_with_time=["昨天 Caroline 去了 LGBTQ support group。"],
        )
        self.neg_sample = EvalSample(
            sample_id="s-neg",
            question_id="q-neg",
            question="Caroline 是否赢得了马拉松冠军？",
            answer_gold="应拒绝回答，因为原文没有相关证据。",
            task_type="NEG",
            f_key=["Caroline", "马拉松冠军"],
            oracle_context="原文没有任何关于 Caroline 赢得马拉松冠军的证据。",
            evidence_texts=[],
            evidence_with_time=[],
        )

    def test_encoding_agent_pos_exist(self):
        agent = EncodingAgent()
        result = agent.evaluate(
            inp=EncodingProbeInput(
                question=self.pos_sample.question,
                memory_corpus=[
                    {"id": "m1", "text": "昨天 Caroline 去了 LGBTQ support group。", "meta": {}},
                ],
                f_key=list(self.pos_sample.f_key),
                task_type="POS",
                evidence_texts=list(self.pos_sample.evidence_texts),
                evidence_with_time=list(self.pos_sample.evidence_with_time),
            ),
            candidate_records=[{"id": "m1", "text": "昨天 Caroline 去了 LGBTQ support group。", "meta": {}}],
            cfg=self.cfg,
        )
        self.assertEqual(result.state, "EXIST")
        self.assertIn("EncodingAgent", result.evidence.get("agent_name", ""))

    def test_encoding_agent_neg_dirty(self):
        agent = EncodingAgent()
        result = agent.evaluate(
            inp=EncodingProbeInput(
                question=self.neg_sample.question,
                memory_corpus=[
                    {"id": "m2", "text": "Caroline 赢得了马拉松冠军。", "meta": {}},
                ],
                f_key=list(self.neg_sample.f_key),
                task_type="NEG",
                evidence_texts=[],
                evidence_with_time=[],
            ),
            candidate_records=[{"id": "m2", "text": "Caroline 赢得了马拉松冠军。", "meta": {}}],
            cfg=self.cfg,
        )
        self.assertEqual(result.state, "DIRTY")
        self.assertIn("DMP", result.defects)

    def test_retrieval_agent_pos_hit(self):
        agent = RetrievalAgent()
        result = agent.evaluate(
            RetrievalProbeInput(
                question=self.pos_sample.question,
                retrieved_items=[
                    {"id": "r1", "text": "昨天 Caroline 去了 LGBTQ support group。", "score": 0.9, "meta": {}},
                    {"id": "r2", "text": "无关内容", "score": 0.1, "meta": {}},
                ],
                f_key=list(self.pos_sample.f_key),
                task_type="POS",
                evidence_texts=list(self.pos_sample.evidence_with_time),
            ),
            self.cfg,
            None,
        )
        self.assertEqual(result.state, "HIT")
        self.assertEqual(result.evidence.get("agent_name"), "RetrievalAgent")

    def test_generation_agent_pos_pass(self):
        agent = GenerationAgent()
        result = agent.evaluate(
            GenerationProbeInput(
                question=self.pos_sample.question,
                oracle_context=self.pos_sample.oracle_context,
                answer_online=self.pos_sample.answer_gold,
                answer_oracle=self.pos_sample.answer_gold,
                answer_gold=self.pos_sample.answer_gold,
                task_type="POS",
            ),
            self.cfg,
        )
        self.assertEqual(result.state, "PASS")
        self.assertEqual(result.evidence.get("agent_name"), "GenerationAgent")

    def test_correctness_judge_pos_refusal_hard_veto(self):
        judgement = judge_answer_correctness(
            task_type="POS",
            question=self.pos_sample.question,
            answer_gold=self.pos_sample.answer_gold,
            answer_pred="不知道",
            cfg=self.cfg,
            judge_mode="online",
            retrieved_context="",
        )
        self.assertFalse(judgement.final_correct)
        self.assertTrue(judgement.judge_payload["hard_veto"])
        self.assertFalse(judgement.rule_correct)

    def test_correctness_judge_falls_back_to_rule_when_llm_unavailable(self):
        cfg = EvaluatorConfig(
            use_llm_assist=False,
            require_llm_judgement=False,
            disable_rule_fallback=False,
            strict_adapter_call=False,
            require_online_answer=False,
            correctness_use_llm_judge=True,
            correctness_require_llm_judge=False,
            llm_api_key="",
            llm_base_url="",
        )
        judgement = judge_answer_correctness(
            task_type="POS",
            question=self.pos_sample.question,
            answer_gold=self.pos_sample.answer_gold,
            answer_pred=self.pos_sample.answer_gold,
            cfg=cfg,
            judge_mode="online",
            retrieved_context="",
        )
        self.assertTrue(judgement.final_correct)
        self.assertEqual(judgement.judge_label, "RULE_FALLBACK")
        self.assertFalse(judgement.judge_payload["llm_available"])

    def test_attribution_agent_suppresses_rf_when_encoding_miss(self):
        evaluator = ParallelThreeProbeEvaluator(config=self.cfg)
        adapter = MockFullAdapter(
            memory_view=[],
            retrieved_items=[{"id": "r1", "text": "无关内容", "score": 0.8, "meta": {}}],
            online_answer="不知道",
            oracle_answer="不知道",
        )
        run_ctx = adapter.ingest_conversation("s-pos", "u1", [])
        result = evaluator.evaluate_with_adapters(
            sample=self.pos_sample,
            encoding_adapter=adapter,
            retrieval_adapter=adapter,
            generation_adapter=adapter,
            run_ctx=run_ctx,
            top_k=5,
        )
        self.assertEqual(result.states["enc"], "MISS")
        self.assertNotIn("RF", result.probe_results["ret"].defects)
        self.assertEqual(result.attribution_evidence["final_attribution"]["primary_cause"], "encoding")

    def test_attribution_agent_adds_rf_when_encoding_exists_but_retrieval_miss(self):
        evaluator = ParallelThreeProbeEvaluator(config=self.cfg)
        adapter = MockFullAdapter(
            memory_view=[{"id": "m1", "text": "昨天 Caroline 去了 LGBTQ support group。", "meta": {}}],
            retrieved_items=[],
            online_answer="不知道",
            oracle_answer=self.pos_sample.answer_gold,
        )
        run_ctx = adapter.ingest_conversation("s-pos", "u1", [])
        result = evaluator.evaluate_with_adapters(
            sample=self.pos_sample,
            encoding_adapter=adapter,
            retrieval_adapter=adapter,
            generation_adapter=adapter,
            run_ctx=run_ctx,
            top_k=5,
        )
        self.assertEqual(result.states["enc"], "EXIST")
        self.assertIn("RF", result.probe_results["ret"].defects)

    def test_encoding_agent_uses_external_high_recall_retriever(self):
        agent = EncodingAgent()
        adapter = MockFullAdapter(
            memory_view=[{"id": "m1", "text": "无关内容", "meta": {}}],
            retrieved_items=[],
            online_answer="",
            oracle_answer="",
        )
        adapter.set_external_high_recall_retriever(MockHighRecallRetriever())
        bundle = agent.collect_observations(self.pos_sample, adapter, run_ctx={})
        self.assertTrue(bundle.coverage_report["used_external_high_recall_retriever"])
        self.assertTrue(any(obs.source_name == "external_high_recall_retriever" for obs in bundle.native_candidate_view))

    def test_encoding_agent_merges_query_and_f_key_retrieval_shadow(self):
        agent = EncodingAgent()
        adapter = QueryAwareAdapter(
            memory_view=[{"id": "m1", "text": "昨天 Caroline 去了 LGBTQ support group。", "meta": {}}],
            retrieved_items=[],
            online_answer="",
            oracle_answer="",
        )
        bundle = agent.collect_observations(self.pos_sample, adapter, run_ctx={}, cfg=self.cfg)
        self.assertEqual(bundle.coverage_report["query_retrieval_shadow_count"], 1)
        self.assertEqual(bundle.coverage_report["f_key_retrieval_shadow_count"], 1)
        self.assertTrue(any(obs.source_name == "retrieve_original_query" for obs in bundle.native_retrieval_shadow))
        self.assertTrue(any(obs.source_name == "retrieve_original_f_key" for obs in bundle.native_retrieval_shadow))


if __name__ == "__main__":
    unittest.main()
