from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from memory_eval.adapters import MemboxAdapter, MemboxAdapterConfig
from memory_eval.dataset.locomo_builder import build_locomo_eval_samples
from memory_eval.pipeline.runner import _conversation_to_turns


def _chat_json(base_url: str, api_key: str, model: str, temperature: float, prompt: str) -> Dict[str, Any] | None:
    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
        obj = json.loads(raw)
        content = str(obj["choices"][0]["message"]["content"]).strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
    except Exception:
        return None


def _judge_online_correct(
    *,
    base_url: str,
    api_key: str,
    judge_model: str,
    judge_temperature: float,
    question: str,
    answer_online: str,
    answer_gold: str,
    task_type: str,
) -> Tuple[bool, Dict[str, Any]]:
    prompt = (
        "You are a strict evaluator for memory QA correctness.\n"
        "Return strict JSON:\n"
        "{\"correct\": true|false, \"reason\": \"...\", \"task_type\": \"POS|NEG\"}\n"
        "Rules:\n"
        "- For POS, answer is correct if semantically equivalent to gold answer.\n"
        "- For NEG, answer is correct only when answer abstains/refuses consistently with gold.\n"
        f"TaskType: {task_type}\n"
        f"Question: {question}\n"
        f"OnlineAnswer: {answer_online}\n"
        f"GoldAnswer: {answer_gold}\n"
    )
    j = _chat_json(base_url, api_key, judge_model, judge_temperature, prompt)
    if not isinstance(j, dict) or "correct" not in j:
        raise RuntimeError("baseline correctness judge failed")
    return bool(j.get("correct", False)), j


def _load_episode_map(dataset_path: Path):
    with dataset_path.open("r", encoding="utf-8") as f:
        episodes = json.load(f)
    return {str(ep.get("sample_id", "")).strip(): ep for ep in episodes if str(ep.get("sample_id", "")).strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one Membox baseline reproduction sample.")
    parser.add_argument("--sample-id", default="", help="Target sample_id, e.g. conv-26")
    parser.add_argument("--question-index", type=int, default=0, help="Question index inside selected sample")
    parser.add_argument("--output", default="outputs/membox_baseline_once.json")
    parser.add_argument("--memory-dir", default="outputs/membox_baseline_memory")
    parser.add_argument("--membox-root", default="", help="Optional Membox root path. Empty means system/Membox.")
    parser.add_argument("--judge-model", default="")
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
            run_id_prefix="baseline_once",
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
    print("stage=metrics")
    f1 = adapter._module.AnswerGenerator._f1(answer_online, sample.answer_gold)
    bleu = adapter._module.AnswerGenerator._bleu(answer_online, sample.answer_gold)
    is_correct, judge_payload = _judge_online_correct(
        base_url=str(keys["base_url"]),
        api_key=str(keys["api_key"]),
        judge_model=str(args.judge_model or keys.get("model", "gpt-4o-mini")),
        judge_temperature=0.0,
        question=sample.question,
        answer_online=answer_online,
        answer_gold=sample.answer_gold,
        task_type=sample.task_type,
    )

    payload = {
        "sample": sample.to_dict(),
        "retrieved_items": retrieved_items,
        "answer_online": answer_online,
        "metrics": {"f1": f1, "bleu": bleu, "correct": is_correct, "judge_payload": judge_payload},
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
