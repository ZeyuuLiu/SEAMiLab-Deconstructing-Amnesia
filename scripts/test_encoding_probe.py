from __future__ import annotations

"""
Independent encoding-probe test script.
独立编码层探针测试脚本：用于快速检测实现是否符合预期。
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_eval.eval_core import evaluate_encoding_probe_with_adapter
from memory_eval.eval_core.adapter_protocol import EncodingAdapterProtocol
from memory_eval.eval_core.models import EvalSample


class MockEncodingAdapter(EncodingAdapterProtocol):
    """
    Mock adapter for deterministic encoding tests.
    用于编码层规则验证的 Mock 适配器。
    """

    def __init__(self, memory_corpus: List[Dict[str, Any]]):
        self._memory = list(memory_corpus)

    def export_full_memory(self, run_ctx: Any) -> List[Dict[str, Any]]:
        return list(self._memory)

    def find_memory_records(
        self,
        run_ctx: Any,
        query: str,
        f_key: List[str],
        memory_corpus: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        # Simple deterministic matcher for tests.
        q = str(query).lower().strip()
        out = []
        for m in memory_corpus:
            txt = str(m.get("text", "")).lower().strip()
            if q and q in txt:
                out.append(m)
                continue
            if any(str(f).lower().strip() and str(f).lower().strip() in txt for f in f_key):
                out.append(m)
        return out


def _make_sample(task_type: str, f_key: List[str], question: str = "When did she go to support group?") -> EvalSample:
    return EvalSample(
        sample_id="s1",
        question_id="s1:q1",
        question=question,
        answer_gold="7 May 2023",
        task_type=task_type,
        f_key=f_key,
        oracle_context="8 May 2023 | User: She went yesterday.",
        evidence_ids=["D1:3"],
        evidence_texts=["She went yesterday."],
        evidence_with_time=["8 May 2023 | User: She went yesterday."],
        construction_evidence={"test": True},
    )


def run_tests() -> int:
    cases = []

    # EXIST
    cases.append(
        {
            "name": "exist",
            "sample": _make_sample("POS", ["8 May 2023 | User: She went yesterday."]),
            "memory": [{"id": "m1", "text": "8 May 2023 | User: She went yesterday."}],
            "expect_state": "EXIST",
            "expect_defects": [],
        }
    )

    # MISS
    cases.append(
        {
            "name": "miss",
            "sample": _make_sample("POS", ["8 May 2023 | User: She went yesterday."]),
            "memory": [{"id": "m1", "text": "Unrelated fact"}],
            "expect_state": "MISS",
            "expect_defects": ["EM"],
        }
    )

    # CORRUPT_AMBIG (partial + ambiguous)
    cases.append(
        {
            "name": "corrupt_ambig",
            "sample": _make_sample("POS", ["He", "8 May 2023 | User: She went yesterday."]),
            "memory": [{"id": "m1", "text": "He"}],
            "expect_state": "CORRUPT_AMBIG",
            "expect_defects": ["EA"],
        }
    )

    # CORRUPT_WRONG (partial + not ambiguous)
    cases.append(
        {
            "name": "corrupt_wrong",
            "sample": _make_sample("POS", ["Fact-A", "Fact-B"]),
            "memory": [{"id": "m1", "text": "Fact-A"}],
            "expect_state": "CORRUPT_WRONG",
            "expect_defects": ["EW"],
        }
    )

    # DIRTY (NEG + suspicious memory)
    cases.append(
        {
            "name": "dirty_neg",
            "sample": _make_sample("NEG", [], question="Who is her partner now?"),
            "memory": [{"id": "m1", "text": "Who is her partner now? She is married."}],
            "expect_state": "DIRTY",
            "expect_defects": ["DMP"],
        }
    )

    # NEG clean
    cases.append(
        {
            "name": "neg_clean",
            "sample": _make_sample("NEG", [], question="Who is her partner now?"),
            "memory": [],
            "expect_state": "MISS",
            "expect_defects": [],
        }
    )

    failures = []
    for c in cases:
        adapter = MockEncodingAdapter(c["memory"])
        result = evaluate_encoding_probe_with_adapter(c["sample"], adapter, run_ctx=None)
        ok_state = result.state == c["expect_state"]
        ok_defects = result.defects == c["expect_defects"]
        if not (ok_state and ok_defects):
            failures.append(
                {
                    "case": c["name"],
                    "expect_state": c["expect_state"],
                    "actual_state": result.state,
                    "expect_defects": c["expect_defects"],
                    "actual_defects": result.defects,
                    "evidence": result.evidence,
                }
            )

    if failures:
        print("Encoding probe test FAILED.")
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2))
        return 1

    print("Encoding probe test PASSED.")
    print("cases:", len(cases))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
