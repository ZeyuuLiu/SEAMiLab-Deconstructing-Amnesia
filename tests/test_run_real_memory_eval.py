from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

SCRIPT_PATH = PROJECT_ROOT / "scripts" / "run_real_memory_eval.py"
SPEC = importlib.util.spec_from_file_location("run_real_memory_eval_test_module", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load script module: {SCRIPT_PATH}")
RUN_REAL_MEMORY_EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN_REAL_MEMORY_EVAL)
load_dataset = RUN_REAL_MEMORY_EVAL.load_dataset
run_baseline = RUN_REAL_MEMORY_EVAL.run_baseline


class _MockConfig:
    api_key = ""
    base_url = ""
    llm_model = "mock-model"


class MockBaselineAdapter:
    def __init__(self):
        self.config = _MockConfig()

    def ingest_conversation(self, sample_id, turns):
        return {"sample_id": sample_id, "turns": list(turns), "run_id": f"run-{sample_id}", "output_root": "/tmp/mock"}

    def generate_online_answer(self, run_ctx, question, top_k):
        return "stub answer"

    def retrieve_original(self, run_ctx, query, top_k):
        return [{"id": "r1", "text": f"retrieved for {query}", "score": 0.9, "meta": {"top_k": top_k}}]

    def export_build_artifact(self, run_ctx):
        return {
            "sample_id": str(run_ctx.get("sample_id", "")),
            "run_id": str(run_ctx.get("run_id", "")),
            "output_root": str(run_ctx.get("output_root", "")),
        }

    def capabilities(self):
        return {"memory_system": "mock_baseline"}


class RunRealMemoryEvalTests(unittest.TestCase):
    def test_run_baseline_writes_bundle_and_question_files(self):
        dataset_path = load_dataset(PROJECT_ROOT / "data" / "locomo10.json", "conv-26")
        adapter = MockBaselineAdapter()
        with tempfile.TemporaryDirectory(prefix="memory_eval_baseline_test_") as tmp_dir:
            output_path = Path(tmp_dir) / "baseline_bundle.json"
            args = argparse.Namespace(
                memory_system="mock_baseline",
                sample_id="conv-26",
                build_manifest="",
                llm_assist=False,
                strict_judge=False,
                allow_correctness_rule_fallback=True,
                limit=10,
                top_k=3,
                output=str(output_path),
            )
            bundle_path = run_baseline(args, dataset_path, adapter)
            self.assertEqual(bundle_path, output_path)
            self.assertTrue(bundle_path.exists())
            payload = json.loads(bundle_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["mode"], "baseline")
            self.assertEqual(len(payload["question_index"]), 10)
            self.assertEqual(len(payload["results"]), 10)
            self.assertEqual(payload["errors"], [])
            run_dir = bundle_path.with_suffix("")
            self.assertTrue((run_dir / "run_summary.json").exists())
            self.assertTrue((run_dir / "question_index.json").exists())
            first_result_file = run_dir / payload["question_index"][0]["result_file"]
            self.assertTrue(first_result_file.exists())
            first_record = json.loads(first_result_file.read_text(encoding="utf-8"))
            self.assertIn("retrieved_context", first_record)
            self.assertIn("judge_payload", first_record)


if __name__ == "__main__":
    unittest.main()
