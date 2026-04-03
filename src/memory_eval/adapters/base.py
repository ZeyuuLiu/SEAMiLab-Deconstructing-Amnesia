from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory_eval.eval_core.high_recall import EncodingHighRecallRetriever

from memory_eval.eval_core.utils import normalize_text


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_keys_path() -> Path:
    return project_root() / "configs" / "keys.local.json"


def load_runtime_credentials(keys_path: Optional[str] = None, require_complete: bool = False) -> Dict[str, str]:
    path_api_key = ""
    path_base_url = ""
    path_model = ""
    candidate = Path(keys_path).resolve() if keys_path else default_keys_path()
    if candidate.exists():
        raw = json.loads(candidate.read_text(encoding="utf-8-sig"))
        path_api_key = str(raw.get("api_key", "")).strip()
        path_base_url = str(raw.get("base_url", "")).strip()
        path_model = str(raw.get("model", "")).strip()

    api_key = os.getenv("MEMORY_EVAL_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip() or path_api_key
    base_url = os.getenv("MEMORY_EVAL_BASE_URL", "").strip() or os.getenv("OPENAI_BASE_URL", "").strip() or path_base_url
    model = os.getenv("MEMORY_EVAL_MODEL", "").strip() or path_model
    if require_complete and (not api_key or not base_url):
        raise ValueError(
            "缺少 API 凭据：请设置 MEMORY_EVAL_API_KEY/MEMORY_EVAL_BASE_URL（或 OPENAI_API_KEY/OPENAI_BASE_URL），"
            "或提供本地 keys 文件。"
        )
    return {"api_key": api_key, "base_url": base_url, "model": model, "keys_path": str(candidate)}


class BaseMemoryAdapter:
    family: str = "unknown"
    flavor: str = "default"

    def __init__(self) -> None:
        self._project_root = project_root()
        self._external_high_recall_retriever: EncodingHighRecallRetriever | None = None

    def capabilities(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "flavor": self.flavor,
            "supports_full_memory_export": True,
            "supports_native_retrieval": True,
            "supports_oracle_generation": True,
            "supports_online_generation": True,
            "supports_high_recall_candidates": True,
        }

    def runtime_manifest(self) -> Dict[str, Any]:
        return {"family": self.family, "flavor": self.flavor, "capabilities": self.capabilities()}

    def set_external_high_recall_retriever(self, retriever: EncodingHighRecallRetriever | None) -> None:
        self._external_high_recall_retriever = retriever

    def get_external_high_recall_retriever(self) -> EncodingHighRecallRetriever | None:
        return self._external_high_recall_retriever

    def merge_runtime_credentials(
        self,
        *,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        keys_path: str = "",
        require_complete: bool = False,
    ) -> Dict[str, str]:
        creds = load_runtime_credentials(keys_path or None, require_complete=require_complete)
        return {
            "api_key": str(api_key or creds.get("api_key", "")).strip(),
            "base_url": str(base_url or creds.get("base_url", "")).strip(),
            "model": str(model or creds.get("model", "")).strip(),
            "keys_path": str(keys_path or creds.get("keys_path", "")),
        }

    def normalize_turns(self, conversation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

    def guess_user_name(self, turns: List[Dict[str, Any]]) -> str:
        counts: Dict[str, int] = {}
        for turn in turns:
            speaker = str(turn.get("speaker", "")).strip()
            if not speaker:
                continue
            counts[speaker] = counts.get(speaker, 0) + 1
        if not counts:
            return "User"
        return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[0][0]

    def guess_agent_name(self, turns: List[Dict[str, Any]], user_name: str) -> str:
        speakers = [str(turn.get("speaker", "")).strip() for turn in turns if str(turn.get("speaker", "")).strip()]
        for speaker in speakers:
            if speaker != user_name:
                return speaker
        return "Assistant"

    def build_run_id(self, prefix: str, sample_id: str) -> str:
        norm_prefix = normalize_text(prefix or self.family).replace(" ", "_")
        norm_sample = normalize_text(sample_id).replace(" ", "_")
        return f"{norm_prefix}_{norm_sample}"[:80]
