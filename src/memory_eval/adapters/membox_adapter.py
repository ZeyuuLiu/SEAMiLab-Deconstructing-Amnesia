from __future__ import annotations

import importlib.util
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory_eval.eval_core.models import AdapterTrace, RetrievedItem
from memory_eval.eval_core.utils import normalize_text, split_tokens, text_match


@dataclass(frozen=True)
class MemboxAdapterConfig:
    api_key: str = ""
    base_url: str = ""
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    membox_root: str = ""
    memory_dir: str = "outputs/membox_memory"
    run_id_prefix: str = "membox"
    top_k_retrieve: Optional[int] = None
    answer_top_n: int = 5
    text_modes: Optional[List[str]] = None


class MemboxAdapter:
    def __init__(self, config: Optional[MemboxAdapterConfig] = None):
        self.config = config or MemboxAdapterConfig()
        self._membox_root = self._resolve_membox_root(self.config.membox_root)
        self._module = self._load_membox_module()

    def ingest_conversation(self, sample_id: str, conversation: List[Dict[str, Any]]) -> Any:
        turns = self._normalize_turns(conversation)
        conv_payload = self._to_membox_conversation(turns)
        run_id = self._build_run_id(sample_id)
        output_root = (Path(self.config.memory_dir) / sample_id).resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        raw_data_path = output_root / "raw_data.json"
        raw_data_path.write_text(
            json.dumps([{"sample_id": sample_id, "conversation": conv_payload, "qa": []}], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        cfg = self._module.Config
        cfg.API_KEY = self.config.api_key
        cfg.BASE_URL = self.config.base_url
        cfg.LLM_MODEL = self.config.llm_model
        cfg.EMBEDDING_MODEL = self.config.embedding_model
        cfg.RAW_DATA_FILE = str(raw_data_path)
        cfg.OUTPUT_BASE_DIR = str(output_root)
        cfg.LIMIT_CONVERSATIONS = 1
        cfg.LIMIT_SESSIONS = None
        cfg.TOP_K_RETRIEVE = self.config.top_k_retrieve
        cfg.ANSWER_TOP_N = int(self.config.answer_top_n or 5)
        cfg.GEN_TEXT_MODES = list(self.config.text_modes or ["content_trace_event"])
        cfg.apply_run_id(run_id)

        worker = self._module.LLMWorker()
        builder = self._module.MemoryBuilder(worker)
        boxes = builder.build_all()
        if not cfg.CHECKPOINT_EVERY_SAMPLE:
            builder.save(boxes)
        builder.summarize_and_log()

        if any(m in {"content_trace_event", "trace_event"} for m in cfg.GEN_TEXT_MODES):
            linker = self._module.TraceLinker(worker, trace_metrics=cfg.TRACE_METRICS)
            linker.run()

        retriever = self._module.SimpleRetriever(worker, top_k=cfg.TOP_K_RETRIEVE)
        retriever.load()

        return {
            "sample_id": sample_id,
            "conversation": turns,
            "raw_data_path": str(raw_data_path),
            "output_root": str(output_root),
            "run_id": run_id,
            "worker": worker,
            "retriever": retriever,
            "config_snapshot": {
                "llm_model": cfg.LLM_MODEL,
                "embedding_model": cfg.EMBEDDING_MODEL,
                "output_dir": cfg.OUTPUT_DIR,
                "final_content_file": cfg.FINAL_CONTENT_FILE,
                "time_trace_file": cfg.TIME_TRACE_FILE,
            },
        }

    def build_trace_for_query(self, run_ctx: Any, query: str, oracle_context: str, top_k: int) -> AdapterTrace:
        memory_view = self.export_full_memory(run_ctx)
        raw_items = self.retrieve_original(run_ctx, query, top_k)
        retrieved_items = [
            RetrievedItem(
                id=str(item.get("id", "")),
                text=str(item.get("text", "")),
                score=float(item.get("score", 0.0) or 0.0),
                meta=dict(item.get("meta", {})) if isinstance(item.get("meta", {}), dict) else {},
            )
            for item in raw_items
        ]
        answer_oracle = self.generate_oracle_answer(run_ctx, query, oracle_context)
        answer_online = self.generate_online_answer(run_ctx, query, top_k)
        return AdapterTrace(
            memory_view=memory_view,
            retrieved_items=retrieved_items,
            answer_online=answer_online,
            answer_oracle=answer_oracle,
            raw_trace={
                "memory_system": "membox",
                "run_id": str(run_ctx.get("run_id", "")),
                "output_root": str(run_ctx.get("output_root", "")),
            },
        )

    def export_full_memory(self, run_ctx: Any) -> List[Dict[str, Any]]:
        boxes = self._load_boxes(run_ctx)
        out: List[Dict[str, Any]] = []
        for box in boxes:
            feat = box.get("features", {})
            content_text = str(feat.get("content_text", "")).strip()
            topic_kw_text = str(feat.get("topic_kw_text", "")).strip()
            events_text = str(feat.get("events_text", "")).strip()
            merged_text = "\n".join([x for x in [content_text, events_text, topic_kw_text] if x]).strip()
            if not merged_text:
                continue
            out.append(
                {
                    "id": f"box-{box.get('box_id')}",
                    "text": merged_text,
                    "meta": {
                        "source": "membox_final_box",
                        "box_id": box.get("box_id"),
                        "sample_id": box.get("sample_id"),
                        "start_time": box.get("start_time"),
                        "coverage": dict(box.get("coverage", {})) if isinstance(box.get("coverage", {}), dict) else {},
                        "events": list(feat.get("events", [])) if isinstance(feat.get("events", []), list) else [],
                        "content_text": content_text,
                        "events_text": events_text,
                        "topic_kw_text": topic_kw_text,
                    },
                }
            )
        return out

    def find_memory_records(
        self,
        run_ctx: Any,
        query: str,
        f_key: List[str],
        memory_corpus: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        signals = [query] + list(f_key or [])
        signal_tokens = set()
        for s in signals:
            signal_tokens.update(split_tokens(str(s)))

        scored: List[tuple[float, Dict[str, Any]]] = []
        for rec in memory_corpus:
            text = str(rec.get("text", ""))
            variants = [text]
            meta = rec.get("meta", {})
            if isinstance(meta, dict):
                variants.extend(
                    [
                        str(meta.get("content_text", "")),
                        str(meta.get("events_text", "")),
                        str(meta.get("topic_kw_text", "")),
                    ]
                )
            if any(text_match(fact, variant) for fact in f_key for variant in variants if fact):
                scored.append((10.0, rec))
                continue
            text_tokens = set(split_tokens(text))
            overlap = len(signal_tokens & text_tokens) if signal_tokens and text_tokens else 0
            if overlap > 0:
                scored.append((float(overlap), rec))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored]

    def hybrid_retrieve_candidates(
        self,
        run_ctx: Any,
        query: str,
        f_key: List[str],
        evidence_texts: List[str],
        top_n: int = 100,
    ) -> List[Dict[str, Any]]:
        rankings = self._score_and_rank(run_ctx, " ".join([query] + list(f_key or []) + list(evidence_texts or [])), [])
        box_map = {str(rec.get("id", "")): rec for rec in self.export_full_memory(run_ctx)}
        out: List[Dict[str, Any]] = []
        for rank, item in enumerate(rankings[: max(1, int(top_n or 1))]):
            rec = box_map.get(item["id"])
            if rec is None:
                continue
            cloned = dict(rec)
            meta = dict(cloned.get("meta", {})) if isinstance(cloned.get("meta", {}), dict) else {}
            meta["hybrid_rank"] = rank + 1
            meta["hybrid_score"] = float(item.get("score", 0.0))
            cloned["meta"] = meta
            out.append(cloned)
        return out

    def retrieve_original(self, run_ctx: Any, query: str, top_k: int) -> List[Dict[str, Any]]:
        rankings = self._score_and_rank(run_ctx, query, [])
        box_map = {str(rec.get("id", "")): rec for rec in self.export_full_memory(run_ctx)}
        out: List[Dict[str, Any]] = []
        for rank, item in enumerate(rankings[: max(1, int(top_k or 1))]):
            rec = box_map.get(item["id"])
            if rec is None:
                continue
            meta = dict(rec.get("meta", {})) if isinstance(rec.get("meta", {}), dict) else {}
            meta["source"] = "membox_native_retrieval"
            meta["native_rank"] = rank
            out.append(
                {
                    "id": rec["id"],
                    "text": str(rec.get("text", "")),
                    "score": float(item.get("score", 0.0)),
                    "meta": meta,
                }
            )
        return out

    def generate_online_answer(self, run_ctx: Any, query: str, top_k: int = 5) -> str:
        retrieved = self.retrieve_original(run_ctx, query, top_k)
        contexts = [str(item.get("text", "")).strip() for item in retrieved if str(item.get("text", "")).strip()]
        if not contexts:
            return ""
        prompt = self._module.Config.PROMPT_QA_ANSWER.format(memories="\n\n".join(contexts), question=query)
        return str(run_ctx["worker"].chat_completion(prompt, note="MemboxAdapter_OnlineAnswer")).strip()

    def generate_oracle_answer(self, run_ctx: Any, query: str, oracle_context: str) -> str:
        context = str(oracle_context or "").strip()
        if not context:
            return ""
        prompt = self._module.Config.PROMPT_QA_ANSWER.format(memories=context, question=query)
        return str(run_ctx["worker"].chat_completion(prompt, note="MemboxAdapter_OracleAnswer")).strip()

    def _load_boxes(self, run_ctx: Any) -> List[Dict[str, Any]]:
        path = Path(str(run_ctx["config_snapshot"]["final_content_file"]))
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def _score_and_rank(self, run_ctx: Any, query: str, evidence: List[str]) -> List[Dict[str, Any]]:
        retriever = run_ctx.get("retriever")
        if retriever is None:
            raise RuntimeError("membox run_ctx missing retriever")
        qa = {
            "question": query,
            "evidence": list(evidence or []),
            "id": normalize_text(query)[:80],
        }
        rankings, sim_map, _ = retriever._score_and_rank(0, qa)
        ordered = rankings.get("content_event_topic_kw", []) or []
        return [{"id": f"box-{bid}", "score": float(sim_map.get(bid, -1.0)), "box_id": bid} for bid in ordered]

    def _build_run_id(self, sample_id: str) -> str:
        prefix = normalize_text(self.config.run_id_prefix or "membox").replace(" ", "_")
        sid = normalize_text(sample_id).replace(" ", "_")
        return f"{prefix}_{sid}"[:80]

    def _resolve_membox_root(self, configured: str) -> Path:
        if configured:
            return Path(configured).resolve()
        return Path(__file__).resolve().parents[3] / "system" / "Membox"

    def _load_membox_module(self):
        module_path = self._membox_root / "membox.py"
        if not module_path.exists():
            raise FileNotFoundError(f"Membox entry file not found: {module_path}")
        spec = importlib.util.spec_from_file_location("memory_eval_membox_runtime", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"failed to load Membox module from {module_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules.setdefault("memory_eval_membox_runtime", mod)
        spec.loader.exec_module(mod)
        return mod

    def _normalize_turns(self, conversation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for idx, turn in enumerate(conversation):
            text = str(turn.get("text") or turn.get("content") or "").strip()
            if not text:
                continue
            out.append(
                {
                    "turn_index": int(turn.get("turn_index", idx)),
                    "speaker": str(turn.get("speaker") or turn.get("role") or "UNKNOWN").strip(),
                    "text": text,
                    "timestamp": str(turn.get("timestamp") or turn.get("time") or "").strip(),
                }
            )
        return out

    def _to_membox_conversation(self, turns: List[Dict[str, Any]]) -> Dict[str, Any]:
        speaker_a = self._guess_user_name(turns)
        speaker_b = self._guess_agent_name(turns, speaker_a)
        sessions: Dict[str, List[Dict[str, Any]]] = {}
        session_ts: Dict[str, str] = {}
        for turn in turns:
            session_id = self._timestamp_to_session(turn.get("timestamp", ""))
            sessions.setdefault(session_id, [])
            if session_id not in session_ts:
                session_ts[session_id] = str(turn.get("timestamp", "")).strip()
            sessions[session_id].append(
                {
                    "speaker": str(turn.get("speaker", "")).strip() or speaker_a,
                    "text": str(turn.get("text", "")).strip(),
                }
            )

        out: Dict[str, Any] = {"speaker_a": speaker_a, "speaker_b": speaker_b}
        for idx, session_name in enumerate(sorted(sessions.keys()), start=1):
            key = f"session_{idx}"
            out[key] = sessions[session_name]
            out[f"{key}_date_time"] = session_ts.get(session_name, "")
        return out

    def _timestamp_to_session(self, timestamp: str) -> str:
        ts = str(timestamp or "").strip()
        return ts or "session_unknown"

    def _guess_user_name(self, turns: List[Dict[str, Any]]) -> str:
        counts: Dict[str, int] = {}
        for turn in turns:
            speaker = str(turn.get("speaker", "")).strip()
            if not speaker:
                continue
            counts[speaker] = counts.get(speaker, 0) + 1
        if not counts:
            return "User"
        return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]

    def _guess_agent_name(self, turns: List[Dict[str, Any]], user_name: str) -> str:
        speakers = [str(turn.get("speaker", "")).strip() for turn in turns if str(turn.get("speaker", "")).strip()]
        for speaker in speakers:
            if speaker != user_name:
                return speaker
        return "Assistant"
