from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_eval.eval_core import EvaluatorConfig
from memory_eval.pipeline import PipelineConfig, ThreeProbeEvaluationPipeline


class MockFullAdapter:
    def ingest_conversation(self, sample_id: str, conversation: Dict[str, Any]) -> Dict[str, Any]:
        # Keep raw conversation for deterministic mock behavior.
        return {"sample_id": sample_id, "conversation": conversation}

    def export_full_memory(self, run_ctx: Any) -> List[Dict[str, Any]]:
        return [{"id": "m1", "text": "caroline went to a support group yesterday", "meta": {}}]

    def find_memory_records(
        self,
        run_ctx: Any,
        query: str,
        f_key: List[str],
        memory_corpus: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        return memory_corpus

    def retrieve_original(self, run_ctx: Any, query: str, top_k: int) -> List[Dict[str, Any]]:
        return [{"id": "r1", "text": "caroline went to a support group yesterday", "score": 0.9, "meta": {}}]

    def generate_oracle_answer(self, run_ctx: Any, query: str, oracle_context: str) -> str:
        # stable mock answer
        if "NO_RELEVANT_MEMORY" in str(oracle_context):
            return "I don't know."
        return "support group"

    def generate_online_answer(self, run_ctx: Any, query: str, top_k: int = 5) -> str:
        return "support group"


def main() -> int:
    output = PROJECT_ROOT / "outputs" / "test_eval_pipeline_mock.json"
    run_dir = output.with_suffix("")
    pipeline = ThreeProbeEvaluationPipeline(
        PipelineConfig(
            dataset_path=str(PROJECT_ROOT / "data" / "locomo10.json"),
            output_path=str(output),
            limit=2,
            top_k=5,
            f_key_mode="rule",
            evaluator_config=EvaluatorConfig(
                use_llm_assist=False,
                require_llm_judgement=False,
                disable_rule_fallback=False,
                require_online_answer=False,
            ),
        )
    )
    report = pipeline.run(MockFullAdapter())
    assert report["summary"]["total"] == 2, "unexpected sample count"
    assert output.exists(), "output file not written"
    assert (run_dir / "run_summary.json").exists(), "run summary not written"
    assert (run_dir / "question_index.json").exists(), "question index not written"
    with output.open("r", encoding="utf-8") as f:
        parsed = json.load(f)
    assert "results" in parsed and isinstance(parsed["results"], list), "missing results list"
    assert "question_index" in parsed and len(parsed["question_index"]) == 2, "missing question index"
    first_result_file = run_dir / parsed["question_index"][0]["result_file"]
    assert first_result_file.exists(), "per-question json not written"
    print("Eval pipeline mock test PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
