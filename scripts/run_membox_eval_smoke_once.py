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
from memory_eval.adapters.o_mem_adapter import load_runtime_credentials
from memory_eval.dataset.locomo_builder import build_locomo_eval_samples
from memory_eval.eval_core import EvaluatorConfig, ParallelThreeProbeEvaluator
from memory_eval.pipeline.runner import _conversation_to_turns


def _ensure_nltk_punkt() -> None:
    try:
        import nltk

        nltk.data.find("tokenizers/punkt")
    except LookupError:
        import nltk

        try:
            nltk.download("punkt_tab", quiet=True)
        except Exception:
            pass
        nltk.download("punkt", quiet=True)
    except Exception:
        pass


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
    parser.add_argument("--membox-root", default="", help="Empty = system/Membox_stableEval")
    parser.add_argument("--keys-path", default="configs/keys.local.json")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--base-url", default="")
    parser.add_argument("--llm-model", default="")
    parser.add_argument("--embedding-model", default="text-embedding-3-small")
    args = parser.parse_args()

    keys_path = PROJECT_ROOT / args.keys_path if not Path(args.keys_path).is_absolute() else Path(args.keys_path)
    creds = load_runtime_credentials(str(keys_path), require_complete=False)
    api_key = args.api_key or creds.get("api_key", "")
    base_url = args.base_url or creds.get("base_url", "https://vip.dmxapi.com/v1")
    llm_model = args.llm_model or creds.get("model", "gpt-4o-mini")
    if not api_key:
        raise RuntimeError("api_key missing: configs/keys.local.json, --api-key, or MEMORY_EVAL_API_KEY")
    _ensure_nltk_punkt()
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

    mroot = str(Path(args.membox_root).resolve()) if args.membox_root else str(PROJECT_ROOT / "system" / "Membox_stableEval")
    adapter = MemboxAdapter(
        MemboxAdapterConfig(
            api_key=api_key,
            base_url=base_url,
            llm_model=llm_model,
            embedding_model=str(args.embedding_model or "text-embedding-3-small"),
            membox_root=mroot,
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
        llm_model=llm_model,
        llm_temperature=0.0,
        llm_api_key=api_key,
        llm_base_url=base_url,
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
