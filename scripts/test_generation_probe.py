from __future__ import annotations

"""
Independent generation-probe test script.
独立生成层探针测试脚本。
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_eval.eval_core import (
    EvaluatorConfig,
    GenerationProbeInput,
    evaluate_generation_probe,
    evaluate_generation_probe_with_adapter,
)
from memory_eval.eval_core.adapter_protocol import GenerationAdapterProtocol


class MockGenerationAdapter(GenerationAdapterProtocol):
    def __init__(self, answer: str):
        self.answer = answer

    def generate_oracle_answer(self, run_ctx, query: str, oracle_context: str) -> str:
        return self.answer


def run_tests() -> int:
    cfg = EvaluatorConfig(
        use_llm_assist=False,
        require_online_answer=False,
        strict_adapter_call=False,
        disable_rule_fallback=False,
        require_llm_judgement=False,
    )
    cases = [
        {
            "name": "pos_pass",
            "inp": GenerationProbeInput(
                question="When did she go?",
                oracle_context="8 May 2023 | Caroline: I went yesterday.",
                answer_online="8 May 2023",
                answer_oracle="8 May 2023",
                answer_gold="8 May 2023",
                task_type="POS",
            ),
            "state": "PASS",
            "defects": [],
        },
        {
            "name": "neg_pass",
            "inp": GenerationProbeInput(
                question="Who is her spouse?",
                oracle_context="NO_RELEVANT_MEMORY",
                answer_online="I don't know",
                answer_oracle="I don't know",
                answer_gold="not mentioned",
                task_type="NEG",
            ),
            "state": "PASS",
            "defects": [],
        },
        {
            "name": "neg_gh",
            "inp": GenerationProbeInput(
                question="Who is her spouse?",
                oracle_context="NO_RELEVANT_MEMORY",
                answer_online="She is married to Alex",
                answer_oracle="She is married to Alex",
                answer_gold="not mentioned",
                task_type="NEG",
            ),
            "state": "FAIL",
            "defects": ["GH"],
        },
        {
            "name": "pos_gf",
            "inp": GenerationProbeInput(
                question="Where did she move from?",
                oracle_context="4 years ago | Caroline: I moved from Sweden.",
                answer_online="Her favorite color is blue.",
                answer_oracle="Her favorite color is blue.",
                answer_gold="Sweden",
                task_type="POS",
            ),
            "state": "FAIL",
            "defects": ["GF"],
        },
        {
            "name": "pos_grf",
            "inp": GenerationProbeInput(
                question="How long ago was her 18th birthday?",
                oracle_context="5 July 2023 | Caroline: My 18th birthday was 10 years ago.",
                answer_online="It was 12 years ago.",
                answer_oracle="It was 12 years ago.",
                answer_gold="10 years ago",
                task_type="POS",
            ),
            "state": "FAIL",
            "defects": ["GRF"],
        },
    ]

    failures = []
    for c in cases:
        r = evaluate_generation_probe(c["inp"], cfg=cfg)
        if r.state != c["state"] or r.defects != c["defects"]:
            failures.append(
                {
                    "case": c["name"],
                    "expect_state": c["state"],
                    "actual_state": r.state,
                    "expect_defects": c["defects"],
                    "actual_defects": r.defects,
                    "evidence": r.evidence,
                }
            )

    # adapter-entry smoke
    sample = type(
        "S",
        (),
        {
            "question": "When did she go?",
            "oracle_context": "8 May 2023 | Caroline: I went yesterday.",
            "answer_gold": "8 May 2023",
            "task_type": "POS",
        },
    )()
    ad = MockGenerationAdapter("8 May 2023")
    ar = evaluate_generation_probe_with_adapter(sample=sample, adapter=ad, run_ctx=None, cfg=cfg)
    if ar.state != "PASS":
        failures.append({"case": "adapter_entry", "expect_state": "PASS", "actual_state": ar.state, "actual_defects": ar.defects})

    if failures:
        print("Generation probe test FAILED.")
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2))
        return 1
    print("Generation probe test PASSED.")
    print("cases:", len(cases) + 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
