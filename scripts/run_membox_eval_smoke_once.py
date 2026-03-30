from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_eval.adapters import MemboxAdapter, MemboxAdapterConfig
from memory_eval.dataset.locomo_builder import build_locomo_eval_samples
from memory_eval.eval_core import EvaluatorConfig, ParallelThreeProbeEvaluator
from memory_eval.pipeline.runner import _conversation_to_turns


def _load_episode_map(dataset_path: Path):
    with dataset_path.open("r", encoding="utf-8") as f:
        episodes = json.load(f)
    return {str(ep.get("sample_id", "")).strip(): ep for ep in episodes if str(ep.get("sample_id", "")).strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Membox strict evaluation smoke.")
    parser.add_argument("--sample-id", default="", help="Target sample_id, e.g. conv-26")
    parser.add_argument("--question-index", type=int, default=0, help="Question index inside selected sample")
    parser.add_argument("--output", default="outputs/membox_eval_smoke_once.json")
    parser.add_argument("--memory-dir", default="outputs/membox_eval_smoke_memory")
    parser.add_argument("--membox-root", default="", help="Optional Membox root path. Empty means system/Membox.")
    args = parser.parse_args()

    keys = json.loads((PROJECT_ROOT / "configs" / "keys.local.json").read_text(encoding="utf-8-sig"))
    dataset_path = PROJECT_ROOT / "data" / "locomo10.json"
    out_path = PROJECT_ROOT / args.output

    samples = [s.to_eval_sample() for s in build_locomo_eval_samples(str(dataset_path), limit=None, f_key_mode="rule")]
    if not samples:
        raise RuntimeError("no sample built")
    if args.sample_id:
        matched = [s for s in samples if s.sample_id == args.sample_id]
        if not matched:
            raise RuntimeError(f"sample_id not found: {args.sample_id}")
        if args.question_index < 0 or args.question_index >= len(matched):
            raise RuntimeError(f"question_index out of range for {args.sample_id}: {args.question_index}")
        sample = matched[args.question_index]
    else:
        sample = samples[0]

    episode_map = _load_episode_map(dataset_path)
    episode = episode_map.get(sample.sample_id, {})
    conv = _conversation_to_turns(episode.get("conversation", {}))

    adapter = MemboxAdapter(
        MemboxAdapterConfig(
            api_key=str(keys["api_key"]),
            base_url=str(keys["base_url"]),
            llm_model=str(keys.get("model", "gpt-4o-mini")),
            membox_root=str(Path(args.membox_root).resolve()) if args.membox_root else str(PROJECT_ROOT / "system" / "Membox"),
            memory_dir=str((PROJECT_ROOT / args.memory_dir).resolve()),
            run_id_prefix="eval_once",
            answer_top_n=5,
            text_modes=["content_trace_event"],
        )
    )

    print("stage=ingest")
    run_ctx = adapter.ingest_conversation(sample.sample_id, conv)
    print("stage=retrieval")
    retrieved_items = adapter.retrieve_original(run_ctx, sample.question, 5)
    print("stage=online_answer")
    answer_online = adapter.generate_online_answer(run_ctx, sample.question, 5)
    print("stage=oracle_answer")
    answer_oracle = adapter.generate_oracle_answer(run_ctx, sample.question, sample.oracle_context)

    evaluator_cfg = EvaluatorConfig(
        tau_rank=5,
        tau_snr=0.2,
        neg_noise_score_threshold=0.15,
        max_workers=3,
        use_llm_assist=True,
        llm_model=str(keys.get("model", "gpt-4o-mini")),
        llm_temperature=0.0,
        llm_api_key=str(keys["api_key"]),
        llm_base_url=str(keys["base_url"]),
        require_llm_judgement=True,
        strict_adapter_call=True,
        disable_rule_fallback=True,
        require_online_answer=True,
        encoding_merge_native_retrieval=True,
        encoding_native_retrieval_top_k=20,
    )
    evaluator = ParallelThreeProbeEvaluator(evaluator_cfg)

    print("stage=eval")
    result = evaluator.evaluate_with_adapters(
        sample=sample,
        run_ctx=run_ctx,
        encoding_adapter=adapter,
        retrieval_adapter=adapter,
        generation_adapter=adapter,
        top_k=5,
    )

    payload = {
        "sample": sample.to_dict(),
        "retrieved_items": retrieved_items,
        "answer_online": answer_online,
        "answer_oracle": answer_oracle,
        "attribution_result": result.to_dict(),
        "run_ctx": {
            "run_id": run_ctx.get("run_id"),
            "output_root": run_ctx.get("output_root"),
            "config_snapshot": run_ctx.get("config_snapshot", {}),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("done")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
