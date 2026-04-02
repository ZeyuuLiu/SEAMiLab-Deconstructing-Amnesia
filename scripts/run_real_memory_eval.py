from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]

import sys

if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from memory_eval.adapters import create_adapter_by_system, export_adapter_runtime_manifest, load_runtime_credentials
from memory_eval.dataset.locomo_builder import build_locomo_eval_samples
from memory_eval.eval_core.models import EvaluatorConfig
from memory_eval.pipeline.runner import PipelineConfig, ThreeProbeEvaluationPipeline
from memory_eval.eval_core.utils import normalize_text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real memory-system reproduction or evaluation on LOCOMO.")
    parser.add_argument("--memory-system", required=True, help="Registered adapter key, e.g. o_mem_stable_eval or membox_stable_eval")
    parser.add_argument("--dataset", default="data/locomo10.json")
    parser.add_argument("--sample-id", default="", help="Optional LOCOMO sample_id filter")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mode", choices=["baseline", "eval"], default="eval")
    parser.add_argument("--output", default="")
    parser.add_argument("--keys-path", default=str(PROJECT_ROOT / "configs" / "keys.local.json"))
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--embedding-model-path", default="")
    parser.add_argument("--omem-root", default="")
    parser.add_argument("--membox-root", default="")
    parser.add_argument("--use-real-omem", action="store_true")
    parser.add_argument("--allow-fallback-lightweight", action="store_true")
    parser.add_argument("--llm-assist", action="store_true")
    parser.add_argument("--strict-judge", action="store_true")
    return parser.parse_args()


def load_dataset(path: Path, sample_id: str) -> Path:
    if not sample_id:
        return path
    data = json.loads(path.read_text(encoding="utf-8"))
    filtered = [episode for episode in data if str(episode.get("sample_id", "")).strip() == sample_id]
    if not filtered:
        raise ValueError(f"dataset 中未找到 sample_id={sample_id}")
    temp_dir = tempfile.mkdtemp(prefix="memory_eval_locomo_")
    out = Path(temp_dir) / path.name
    out.write_text(json.dumps(filtered, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def build_adapter_config(args: argparse.Namespace) -> Dict[str, Any]:
    creds = load_runtime_credentials(args.keys_path, require_complete=False)
    cfg: Dict[str, Any] = {
        "api_key": creds.get("api_key", ""),
        "base_url": creds.get("base_url", ""),
        "llm_model": creds.get("model", "") or "gpt-4o-mini",
        "keys_path": args.keys_path,
    }
    key = str(args.memory_system).lower()
    if "o_mem" in key or "omem" in key:
        default_embedding = PROJECT_ROOT / "Qwen" / "Qwen3-Embedding-0.6B"
        cfg.update(
            {
                "use_real_omem": bool(args.use_real_omem or "stable_eval" in key),
                "allow_fallback_lightweight": bool(args.allow_fallback_lightweight),
            }
        )
        cfg["embedding_model_name"] = args.embedding_model_path or (str(default_embedding) if default_embedding.exists() else "all-MiniLM-L6-v2")
        if args.omem_root:
            cfg["omem_root"] = args.omem_root
    if "membox" in key and args.membox_root:
        cfg["membox_root"] = args.membox_root
    return cfg


def run_baseline(args: argparse.Namespace, dataset_path: Path, adapter: Any) -> Path:
    samples = build_locomo_eval_samples(str(dataset_path), limit=args.limit)
    episodes = json.loads(dataset_path.read_text(encoding="utf-8"))
    by_sample = {str(ep.get("sample_id", "")).strip(): ep for ep in episodes}
    results: List[Dict[str, Any]] = []
    correct = 0
    total = 0
    run_ctx_cache: Dict[str, Any] = {}
    for sample in samples:
        sample_id = sample.sample_id
        if sample_id not in run_ctx_cache:
            episode = by_sample.get(sample_id)
            if not episode:
                continue
            flattened = []
            conversation = episode.get("conversation", {})
            turn_index = 0
            for key, turns in conversation.items():
                if not key.startswith("session_") or not isinstance(turns, list):
                    continue
                for turn in turns:
                    flattened.append(
                        {
                            "turn_index": turn_index,
                            "speaker": str(turn.get("speaker", "")).strip(),
                            "text": str(turn.get("text", "")).strip(),
                        }
                    )
                    turn_index += 1
            run_ctx_cache[sample_id] = adapter.ingest_conversation(sample_id, flattened)
        run_ctx = run_ctx_cache[sample_id]
        answer_online = adapter.generate_online_answer(run_ctx, sample.question)
        online_norm = normalize_text(answer_online)
        gold_norm = normalize_text(sample.answer_gold)
        is_correct = bool(gold_norm) and (online_norm == gold_norm or gold_norm in online_norm or online_norm in gold_norm)
        total += 1
        correct += int(is_correct)
        results.append(
            {
                "sample_id": sample.sample_id,
                "question_id": sample.question_id,
                "task_type": sample.task_type,
                "question": sample.question,
                "answer_gold": sample.answer_gold,
                "answer_online": answer_online,
                "correct": is_correct,
            }
        )
    summary = {
        "memory_system": args.memory_system,
        "mode": "baseline",
        "sample_filter": args.sample_id,
        "count": total,
        "correct": correct,
        "accuracy": (correct / total) if total else 0.0,
        "adapter_manifest": export_adapter_runtime_manifest(adapter),
    }
    out_path = Path(args.output) if args.output else PROJECT_ROOT / "outputs" / f"{args.memory_system}_baseline.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def run_eval(args: argparse.Namespace, dataset_path: Path, adapter: Any) -> Path:
    cfg = EvaluatorConfig(
        use_llm_assist=bool(args.llm_assist),
        require_llm_judgement=bool(args.strict_judge),
        disable_rule_fallback=bool(args.strict_judge),
        strict_adapter_call=True,
        require_online_answer=False,
        llm_api_key=getattr(adapter.config, "api_key", ""),
        llm_base_url=getattr(adapter.config, "base_url", ""),
        llm_model=getattr(adapter.config, "llm_model", "gpt-4o-mini"),
    )
    out_path = Path(args.output) if args.output else PROJECT_ROOT / "outputs" / f"{args.memory_system}_eval.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pipeline = ThreeProbeEvaluationPipeline(
        PipelineConfig(
            dataset_path=str(dataset_path),
            output_path=str(out_path),
            top_k=int(args.top_k),
            evaluator_config=cfg,
            limit=args.limit,
        )
    )
    pipeline.run(adapter)
    return out_path


def main() -> None:
    args = parse_args()
    dataset_path = load_dataset((PROJECT_ROOT / args.dataset).resolve(), args.sample_id)
    adapter = create_adapter_by_system(args.memory_system, build_adapter_config(args))
    out_path = run_baseline(args, dataset_path, adapter) if args.mode == "baseline" else run_eval(args, dataset_path, adapter)
    print(json.dumps({"ok": True, "memory_system": args.memory_system, "mode": args.mode, "output": str(out_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
