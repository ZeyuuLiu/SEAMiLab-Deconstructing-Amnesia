from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Protocol

from memory_eval.adapters.registry import export_adapter_runtime_manifest
from memory_eval.dataset.locomo_builder import build_locomo_eval_samples
from memory_eval.eval_core.engine import ParallelThreeProbeEvaluator
from memory_eval.eval_core.models import AttributionResult, EvalSample, EvaluatorConfig


def _redact_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for key, value in obj.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("api_key", "apikey", "token", "secret", "password")):
                out[key] = "***REDACTED***" if value else value
            else:
                out[key] = _redact_secrets(value)
        return out
    if isinstance(obj, list):
        return [_redact_secrets(x) for x in obj]
    return obj


class FullEvalAdapterProtocol(Protocol):
    """
    Full adapter contract used by end-to-end evaluation pipeline.
    端到端评估流水线所需的完整适配器协议。
    """

    def ingest_conversation(self, sample_id: str, conversation: List[Dict[str, Any]]) -> Any:
        ...

    def export_full_memory(self, run_ctx: Any) -> List[Dict[str, Any]]:
        ...

    def find_memory_records(
        self,
        run_ctx: Any,
        query: str,
        f_key: List[str],
        memory_corpus: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        ...

    def retrieve_original(self, run_ctx: Any, query: str, top_k: int) -> List[Dict[str, Any]]:
        ...

    def generate_oracle_answer(self, run_ctx: Any, query: str, oracle_context: str) -> str:
        ...


@dataclass(frozen=True)
class PipelineConfig:
    dataset_path: str
    output_path: str
    top_k: int = 5
    limit: int | None = None
    f_key_mode: str = "rule"
    evaluator_config: EvaluatorConfig = EvaluatorConfig()


def _load_episode_map(dataset_path: str) -> Dict[str, Dict[str, Any]]:
    path = Path(dataset_path)
    with path.open("r", encoding="utf-8") as f:
        episodes = json.load(f)
    out: Dict[str, Dict[str, Any]] = {}
    for ep in episodes:
        sid = str(ep.get("sample_id", "")).strip()
        if sid:
            out[sid] = ep
    return out


def _build_summary(results: List[AttributionResult]) -> Dict[str, Any]:
    defect_counts: Dict[str, int] = {}
    task_counts: Dict[str, int] = {"POS": 0, "NEG": 0}
    state_counts: Dict[str, Dict[str, int]] = {"enc": {}, "ret": {}, "gen": {}}

    for r in results:
        task_counts[r.task_type] = task_counts.get(r.task_type, 0) + 1
        for d in r.defects:
            defect_counts[d] = defect_counts.get(d, 0) + 1
        for probe in ("enc", "ret", "gen"):
            s = r.states.get(probe, "UNKNOWN")
            probe_map = state_counts[probe]
            probe_map[s] = probe_map.get(s, 0) + 1

    return {
        "total": len(results),
        "ok": len(results),
        "errors": 0,
        "task_counts": task_counts,
        "defect_counts": defect_counts,
        "state_counts": state_counts,
    }


def _build_error_record(sample: EvalSample, exc: Exception) -> Dict[str, Any]:
    return {
        "question_id": sample.question_id,
        "sample_id": sample.sample_id,
        "task_type": sample.task_type,
        "status": "EVAL_ERROR",
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
    }


def _conversation_to_turns(conversation: Any) -> List[Dict[str, Any]]:
    """
    Normalize dataset conversation payload into flat turns list.
    将数据集中 conversation 统一展开为 turn 列表，方便适配器 ingest。
    """
    if isinstance(conversation, list):
        out: List[Dict[str, Any]] = []
        for i, turn in enumerate(conversation):
            if not isinstance(turn, dict):
                continue
            out.append(
                {
                    "turn_index": int(turn.get("turn_index", i)),
                    "speaker": str(turn.get("speaker") or turn.get("role") or "").strip(),
                    "text": str(turn.get("text") or turn.get("content") or "").strip(),
                    "timestamp": str(turn.get("timestamp") or turn.get("time") or "").strip(),
                }
            )
        return [x for x in out if x.get("text")]

    if not isinstance(conversation, dict):
        return []

    out: List[Dict[str, Any]] = []
    session_dt: Dict[str, str] = {}
    for key, value in conversation.items():
        k = str(key)
        if k.startswith("session_") and k.endswith("_date_time"):
            session_dt[k.replace("_date_time", "")] = str(value).strip()

    turn_index = 0
    for key in sorted(conversation.keys()):
        k = str(key)
        if not k.startswith("session_") or k.endswith("_date_time"):
            continue
        turns = conversation.get(k)
        if not isinstance(turns, list):
            continue
        ts = session_dt.get(k, "")
        for turn in turns:
            if not isinstance(turn, dict):
                continue
            text = str(turn.get("text", "")).strip()
            if not text:
                continue
            out.append(
                {
                    "turn_index": turn_index,
                    "speaker": str(turn.get("speaker", "")).strip(),
                    "text": text,
                    "timestamp": ts,
                }
            )
            turn_index += 1
    return out


class ThreeProbeEvaluationPipeline:
    """
    End-to-end pipeline:
    dataset -> adapter runtime ctx -> three-probe evaluator -> output report.
    端到端流水线：数据集 -> 适配器运行态 -> 三探针评估 -> 结果落盘。
    """

    def __init__(self, cfg: PipelineConfig):
        self.cfg = cfg
        self.evaluator = ParallelThreeProbeEvaluator(config=cfg.evaluator_config)

    def run(self, adapter: FullEvalAdapterProtocol) -> Dict[str, Any]:
        samples = build_locomo_eval_samples(
            dataset_path=self.cfg.dataset_path,
            limit=self.cfg.limit,
            f_key_mode=self.cfg.f_key_mode,
        )
        eval_samples: List[EvalSample] = [s.to_eval_sample() for s in samples]
        episode_map = _load_episode_map(self.cfg.dataset_path)
        run_ctx_cache: Dict[str, Any] = {}
        results: List[AttributionResult] = []
        errors: List[Dict[str, Any]] = []

        for sample in eval_samples:
            if sample.sample_id not in run_ctx_cache:
                episode = episode_map.get(sample.sample_id, {})
                conv = episode.get("conversation", {})
                run_ctx_cache[sample.sample_id] = adapter.ingest_conversation(sample.sample_id, _conversation_to_turns(conv))

            run_ctx = run_ctx_cache[sample.sample_id]
            try:
                result = self.evaluator.evaluate_with_adapters(
                    sample=sample,
                    run_ctx=run_ctx,
                    encoding_adapter=adapter,
                    retrieval_adapter=adapter,
                    generation_adapter=adapter,
                    top_k=self.cfg.top_k,
                )
                results.append(result)
            except Exception as exc:
                errors.append(_build_error_record(sample, exc))

        summary = _build_summary(results)
        summary["errors"] = len(errors)
        summary["total"] = len(results) + len(errors)
        summary["ok"] = len(results)
        payload = {
            "config": {
                "dataset_path": self.cfg.dataset_path,
                "top_k": self.cfg.top_k,
                "limit": self.cfg.limit,
                "f_key_mode": self.cfg.f_key_mode,
                "evaluator_config": _redact_secrets(asdict(self.cfg.evaluator_config)),
            },
            "adapter_manifest": export_adapter_runtime_manifest(adapter),
            "summary": summary,
            "results": [r.to_dict() for r in results],
            "errors": errors,
        }

        out_path = Path(self.cfg.output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return payload
