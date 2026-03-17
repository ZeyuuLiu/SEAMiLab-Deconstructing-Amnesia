from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_eval.adapters import OMemAdapter
from memory_eval.eval_core.encoding import evaluate_encoding_probe_with_adapter
from memory_eval.eval_core.models import EvalSample


def _sample(f_key: str) -> EvalSample:
    return EvalSample(
        sample_id="conv-26",
        question_id="conv-26:0",
        question="When did Caroline go to the support group?",
        answer_gold="8 May 2023",
        task_type="POS",
        f_key=[f_key],
        oracle_context=f_key,
        evidence_ids=["D26:1"],
        evidence_texts=["She went yesterday."],
        evidence_with_time=[f_key],
        construction_evidence={"test": True},
    )


def run_tests() -> int:
    adapter = OMemAdapter()
    sample = _sample("8 May 2023 | Caroline: She went yesterday.")

    run_ctx_light = {
        "memory_view": [
            {
                "id": "m1",
                "text": "She went yesterday.",
                "meta": {
                    "layer": "conversation_cache",
                    "turn_index": 1,
                    "role": "user",
                    "speaker": "Caroline",
                    "timestamp": "8 May 2023",
                },
            }
        ]
    }
    res_light = evaluate_encoding_probe_with_adapter(sample, adapter, run_ctx_light)
    if res_light.state != "EXIST":
        print("FAIL lightweight:", res_light.to_dict())
        return 1

    run_ctx_real = {
        "memory_view": [
            {
                "id": "user_working-0-1",
                "text": "She went yesterday.",
                "meta": {
                    "layer": "user_working",
                    "turn_index": 1,
                    "role": "user",
                    "speaker": "",
                    "timestamp": "8 May 2023",
                },
            }
        ]
    }
    sample_user = _sample("8 May 2023 | User: She went yesterday.")
    res_real = evaluate_encoding_probe_with_adapter(sample_user, adapter, run_ctx_real)
    if res_real.state != "EXIST":
        print("FAIL real_omem_like:", res_real.to_dict())
        return 1

    print("ALL_PASS test_omem_adapter_encoding")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
