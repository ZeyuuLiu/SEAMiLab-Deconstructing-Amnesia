from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class LLMAssistConfig:
    api_key: str
    base_url: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.0


def _chat_json(cfg: LLMAssistConfig, prompt: str) -> Dict[str, Any] | None:
    if not cfg.api_key or not cfg.base_url:
        return None
    payload = {
        "model": cfg.model,
        "temperature": cfg.temperature,
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request(
        url=f"{cfg.base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg.api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
        obj = json.loads(raw)
        content = obj["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        return None


def llm_judge_retrieval_noise(
    cfg: LLMAssistConfig,
    query: str,
    retrieved_items: List[Dict[str, Any]],
) -> Dict[str, Any] | None:
    prompt = (
        "You are judging retrieval noise for a NEG task.\n"
        "Return JSON: {\"is_noise\": true|false, \"reason\": \"...\"}\n"
        f"Query: {query}\n"
        "Retrieved items:\n"
        + "\n".join([f"- score={it.get('score', 0)} text={it.get('text', '')}" for it in retrieved_items[:5]])
    )
    return _chat_json(cfg, prompt)


def llm_judge_fact_match(
    cfg: LLMAssistConfig,
    question: str,
    fact: str,
    candidate_text: str,
) -> Dict[str, Any] | None:
    prompt = (
        "You are matching a key fact against a memory text snippet.\n"
        "Return JSON: {\"match\": true|false, \"ambiguous\": true|false, \"reason\": \"...\"}\n"
        f"Question: {question}\n"
        f"Fact: {fact}\n"
        f"Candidate: {candidate_text}\n"
    )
    return _chat_json(cfg, prompt)
