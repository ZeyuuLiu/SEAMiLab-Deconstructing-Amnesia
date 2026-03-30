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


def _chat_json(cfg: LLMAssistConfig, prompt: str, *, must_succeed: bool = False) -> Dict[str, Any] | None:
    if not cfg.api_key or not cfg.base_url:
        if must_succeed:
            raise RuntimeError("LLM assist requires non-empty api_key and base_url")
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
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
        obj = json.loads(raw)
        content = str(obj["choices"][0]["message"]["content"]).strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        return json.loads(content)
    except Exception as exc:
        if must_succeed:
            raise RuntimeError(f"LLM chat/completions failed or returned non-JSON: {exc}") from exc
        return None


def llm_judge_retrieval_noise(
    cfg: LLMAssistConfig,
    query: str,
    retrieved_items: List[Dict[str, Any]],
    *,
    must_succeed: bool = False,
) -> Dict[str, Any] | None:
    prompt = (
        "You are judging retrieval noise for a NEG task.\n"
        "Return JSON: {\"is_noise\": true|false, \"reason\": \"...\"}\n"
        f"Query: {query}\n"
        "Retrieved items:\n"
        + "\n".join([f"- score={it.get('score', 0)} text={it.get('text', '')}" for it in retrieved_items[:5]])
    )
    return _chat_json(cfg, prompt, must_succeed=must_succeed)


def llm_judge_encoding_storage(
    cfg: LLMAssistConfig,
    query: str,
    f_key: List[str],
    evidence_texts: List[str],
    candidates: List[Dict[str, Any]],
    task_type: str,
    *,
    must_succeed: bool = False,
) -> Dict[str, Any] | None:
    prompt = (
        "You are a strict evaluator for memory encoding.\n"
        "Judge whether required evidence is truly stored.\n"
        "Task type is POS or NEG.\n"
        "For POS: decide if gold evidence content is present in memory (semantic match OK; minor formatting OK).\n"
        "For NEG: if any memory would wrongly support answering, use DIRTY with DMP.\n"
        "Return strict JSON:\n"
        "{\"encoding_state\":\"EXIST|MISS|CORRUPT_AMBIG|CORRUPT_WRONG|DIRTY\","
        "\"defects\":[\"EM|EA|EW|DMP\"],"
        "\"confidence\":0.0,"
        "\"matched_candidate_ids\":[],"
        "\"reasoning\":\"...\","
        "\"evidence_snippets\":[]}\n"
        f"TaskType: {task_type}\n"
        f"Query: {query}\n"
        f"F_key: {json.dumps(f_key, ensure_ascii=False)}\n"
        f"GoldEvidence: {json.dumps(evidence_texts, ensure_ascii=False)}\n"
        "Candidates (top 50):\n"
        + "\n".join(
            [
                "- id={id} text={text}".format(id=str(c.get("id", "")), text=str(c.get("text", "")))
                for c in candidates[:50]
            ]
        )
    )
    return _chat_json(cfg, prompt, must_succeed=must_succeed)


def llm_judge_retrieval_quality_pos(
    cfg: LLMAssistConfig,
    query: str,
    f_key: List[str],
    evidence_texts: List[str],
    retrieved_items: List[Dict[str, Any]],
    *,
    rank_index: int = -1,
    hit_indices: List[int] | None = None,
    snr: float = 0.0,
    tau_rank: int = 5,
    tau_snr: float = 0.2,
    must_succeed: bool = False,
) -> Dict[str, Any] | None:
    hit_indices = list(hit_indices or [])
    prompt = (
        "You are the retrieval probe for POS tasks.\n"
        "Your job is to compare the memory system's native retrieval output C_original against gold evidence.\n"
        "Use the retrieved texts as primary evidence, and use the computed metrics below as auxiliary diagnostic signals.\n"
        "Return strict JSON:\n"
        "{\"retrieval_state\":\"HIT|MISS|NOISE\","
        "\"defects\":[\"RF|LATE|NOI\"],"
        "\"matched_ids\":[],"
        "\"reasoning\":\"...\","
        "\"evidence_snippets\":[]}\n"
        "Rules:\n"
        f"- If gold evidence is not meaningfully present in any retrieved item -> retrieval_state MISS and include RF (unless encoding layer will gate RF separately).\n"
        f"- If present but ranked worse than position {tau_rank} (1-based best rank) -> include LATE.\n"
        f"- If retrieved context is dominated by irrelevant noise vs gold (SNR below {tau_snr} mentally) -> include NOI.\n"
        f"- ComputedDiagnostics: rank_index={rank_index}, hit_indices={json.dumps(hit_indices, ensure_ascii=False)}, snr={snr:.6f}\n"
        f"Query: {query}\n"
        f"F_key: {json.dumps(f_key, ensure_ascii=False)}\n"
        f"GoldEvidence: {json.dumps(evidence_texts, ensure_ascii=False)}\n"
        "Retrieved items:\n"
        + "\n".join([f"- id={it.get('id','')} score={it.get('score',0)} text={it.get('text','')}" for it in retrieved_items[:20]])
    )
    return _chat_json(cfg, prompt, must_succeed=must_succeed)


def llm_judge_retrieval_quality_neg(
    cfg: LLMAssistConfig,
    query: str,
    retrieved_items: List[Dict[str, Any]],
    *,
    must_succeed: bool = False,
) -> Dict[str, Any] | None:
    prompt = (
        "You are a strict retrieval evaluator for NEG tasks.\n"
        "Judge if retrieved contexts are misleading/noisy and may induce non-abstain answers.\n"
        "Return strict JSON:\n"
        "{\"retrieval_state\":\"NOISE|MISS\","
        "\"defects\":[\"NIR\"],"
        "\"reasoning\":\"...\","
        "\"evidence_snippets\":[]}\n"
        f"Query: {query}\n"
        "Retrieved items:\n"
        + "\n".join([f"- id={it.get('id','')} score={it.get('score',0)} text={it.get('text','')}" for it in retrieved_items[:20]])
    )
    return _chat_json(cfg, prompt, must_succeed=must_succeed)


def llm_judge_fact_match(
    cfg: LLMAssistConfig,
    question: str,
    fact: str,
    candidate_text: str,
    *,
    must_succeed: bool = False,
) -> Dict[str, Any] | None:
    prompt = (
        "You are matching a key fact against a memory text snippet.\n"
        "Return JSON: {\"match\": true|false, \"ambiguous\": true|false, \"reason\": \"...\"}\n"
        f"Question: {question}\n"
        f"Fact: {fact}\n"
        f"Candidate: {candidate_text}\n"
    )
    return _chat_json(cfg, prompt, must_succeed=must_succeed)


def llm_judge_generation_answer(
    cfg: LLMAssistConfig,
    question: str,
    oracle_context: str,
    answer_oracle: str,
    answer_gold: str,
    task_type: str,
    *,
    must_succeed: bool = False,
) -> Dict[str, Any] | None:
    """
    Judge generation result with optional subtype classification.
    LLM 判题并输出 FAIL 子类（GH/GF/GRF）。
    """
    prompt = (
        "You are the generation probe for a memory-system evaluation.\n"
        "This probe judges whether the oracle-context answer is correct, and if incorrect, what kind of generation failure it is.\n"
        "If the oracle answer is semantically equivalent to gold (same entities/dates), set correct=true.\n"
        "Return strict JSON only with schema:\n"
        "{\"correct\": true|false, \"substate\": \"GH|GF|GRF|NONE\", \"grounded\": true|false, \"reason\": \"...\"}\n"
        "Rules:\n"
        "- NEG incorrect should be GH.\n"
        "- POS incorrect and ungrounded should be GF.\n"
        "- POS incorrect but grounded should be GRF.\n"
        f"TaskType: {task_type}\n"
        f"Question: {question}\n"
        f"OracleContext: {oracle_context}\n"
        f"OracleAnswer: {answer_oracle}\n"
        f"GoldAnswer: {answer_gold}\n"
    )
    return _chat_json(cfg, prompt, must_succeed=must_succeed)


def llm_judge_generation_comparison(
    cfg: LLMAssistConfig,
    question: str,
    task_type: str,
    answer_gold: str,
    answer_online: str,
    answer_oracle: str,
    oracle_context: str,
    *,
    must_succeed: bool = False,
) -> Dict[str, Any] | None:
    prompt = (
        "You are the generation comparison probe.\n"
        "Compare online answer, oracle-context answer, and gold answer.\n"
        "Treat semantically equivalent answers as correct (e.g. same calendar date with different punctuation/spacing).\n"
        "Return strict JSON:\n"
        "{\"generation_state\":\"PASS|FAIL\","
        "\"defects\":[\"GH|GF|GRF\"],"
        "\"online_correct\":true,"
        "\"oracle_correct\":true,"
        "\"comparative_judgement\":{"
        "\"online_vs_gold\":\"...\","
        "\"oracle_vs_gold\":\"...\","
        "\"online_vs_oracle\":\"...\"},"
        "\"reasoning\":\"...\"}\n"
        f"TaskType: {task_type}\n"
        f"Question: {question}\n"
        f"GoldAnswer: {answer_gold}\n"
        f"OnlineAnswer: {answer_online}\n"
        f"OracleAnswer: {answer_oracle}\n"
        f"OracleContext: {oracle_context}\n"
    )
    return _chat_json(cfg, prompt, must_succeed=must_succeed)
