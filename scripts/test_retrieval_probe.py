from __future__ import annotations

"""
Independent retrieval-probe test script.
独立检索层探针测试脚本。
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_eval.eval_core import EvaluatorConfig, RetrievalProbeInput, evaluate_retrieval_probe, evaluate_retrieval_probe_with_adapter
from memory_eval.eval_core.adapter_protocol import RetrievalAdapterProtocol


class MockRetrievalAdapter(RetrievalAdapterProtocol):
    def __init__(self, items: List[Dict[str, Any]]):
        self.items = list(items)

    def retrieve_original(self, run_ctx: Any, query: str, top_k: int) -> List[Dict[str, Any]]:
        return list(self.items[:top_k])


def run_tests() -> int:
    cfg = EvaluatorConfig(tau_rank=3, tau_snr=0.4, neg_noise_score_threshold=0.5, use_llm_assist=False)
    cases = [
        {
            "name": "pos_hit_clean",
            "inp": RetrievalProbeInput(
                question="When did she go?",
                retrieved_items=[
                    {"id": "1", "text": "8 May 2023 | Caroline: She went yesterday.", "score": 0.9},
                    {"id": "2", "text": "Unrelated", "score": 0.1},
                ],
                f_key=["8 May 2023 | Caroline: She went yesterday."],
                task_type="POS",
            ),
            "s_enc": "EXIST",
            "state": "HIT",
            "defects": [],
        },
        {
            "name": "pos_hit_late_noi",
            "inp": RetrievalProbeInput(
                question="What activities?",
                retrieved_items=[
                    {"id": "1", "text": "noise 1", "score": 0.8},
                    {"id": "2", "text": "noise 2", "score": 0.7},
                    {"id": "3", "text": "noise 3", "score": 0.6},
                    {"id": "4", "text": "camping pottery", "score": 0.5},
                ],
                f_key=["camping pottery"],
                task_type="POS",
            ),
            "s_enc": "EXIST",
            "state": "HIT",
            "defects": ["LATE", "NOI"],
        },
        {
            "name": "pos_miss_rf",
            "inp": RetrievalProbeInput(
                question="Where from?",
                retrieved_items=[{"id": "1", "text": "other fact", "score": 0.3}],
                f_key=["from Sweden"],
                task_type="POS",
            ),
            "s_enc": "EXIST",
            "state": "MISS",
            "defects": ["RF"],
        },
        {
            "name": "pos_miss_no_rf_when_enc_miss",
            "inp": RetrievalProbeInput(
                question="Where from?",
                retrieved_items=[{"id": "1", "text": "other fact", "score": 0.3}],
                f_key=["from Sweden"],
                task_type="POS",
            ),
            "s_enc": "MISS",
            "state": "MISS",
            "defects": [],
        },
        {
            "name": "neg_noise",
            "inp": RetrievalProbeInput(
                question="Who is her spouse?",
                retrieved_items=[{"id": "1", "text": "She is married", "score": 0.95}],
                f_key=[],
                task_type="NEG",
            ),
            "s_enc": "MISS",
            "state": "NOISE",
            "defects": ["NIR"],
        },
        {
            "name": "neg_miss",
            "inp": RetrievalProbeInput(
                question="Who is her spouse?",
                retrieved_items=[{"id": "1", "text": "some weak irrelevant", "score": 0.1}],
                f_key=[],
                task_type="NEG",
            ),
            "s_enc": "MISS",
            "state": "MISS",
            "defects": [],
        },
    ]

    failures = []
    for c in cases:
        r = evaluate_retrieval_probe(c["inp"], cfg=cfg, s_enc=c["s_enc"])
        if r.state != c["state"] or r.defects != c["defects"]:
            failures.append(
                {
                    "case": c["name"],
                    "expect_state": c["state"],
                    "actual_state": r.state,
                    "expect_defects": c["defects"],
                    "actual_defects": r.defects,
                    "evidence": r.evidence,
                    "attrs": r.attrs,
                }
            )

    # adapter-entry smoke
    ad = MockRetrievalAdapter([{"id": "1", "text": "8 May 2023 | Caroline: She went yesterday.", "score": 0.9}])
    ar = evaluate_retrieval_probe_with_adapter(
        sample=type("S", (), {"question": "When did she go?", "f_key": ["8 May 2023 | Caroline: She went yesterday."], "task_type": "POS"})(),
        adapter=ad,
        run_ctx=None,
        cfg=cfg,
        top_k=5,
        s_enc="EXIST",
    )
    if ar.state != "HIT":
        failures.append({"case": "adapter_entry", "expect_state": "HIT", "actual_state": ar.state, "actual_defects": ar.defects})

    if failures:
        print("Retrieval probe test FAILED.")
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2))
        return 1

    print("Retrieval probe test PASSED.")
    print("cases:", len(cases) + 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
