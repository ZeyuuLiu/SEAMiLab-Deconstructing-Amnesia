from __future__ import annotations

import json
from typing import Any, Dict, List


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


def build_encoding_pos_prompt(query: str, f_key: List[str], evidence_texts: List[str], candidates: List[Dict[str, Any]]) -> str:
    return (
        "你是 EncodingAgent，负责判断 POS 任务中记忆系统是否真实存储了回答当前问题所需的原文证据。\n"
        "POS 任务表示：当前 query 在原文中有证据支撑，系统应该存住相关事实。\n"
        "你的任务不是判断最终答案是否答对，而是判断证据是否存在于记忆中。\n"
        "请只依据给定候选记忆与 gold evidence 作判断，允许语义等价、时间格式变化、轻微改写和多条记录联合支撑。\n"
        "若找到相关记录但关键事实值错误，输出 CORRUPT_WRONG；若找到相关记录但关键主体/指代不清，输出 CORRUPT_AMBIG；若完全没有足够证据，输出 MISS；若足够支撑则输出 EXIST。\n"
        "返回严格 JSON："
        "{\"encoding_state\":\"EXIST|MISS|CORRUPT_AMBIG|CORRUPT_WRONG\","
        "\"defects\":[\"EM|EA|EW\"],"
        "\"confidence\":0.0,"
        "\"matched_candidate_ids\":[],"
        "\"reasoning\":\"...\","
        "\"evidence_snippets\":[],"
        "\"missing_facts\":[]}\n"
        f"Query: {query}\n"
        f"F_key: {_dump(f_key)}\n"
        f"GoldEvidence: {_dump(evidence_texts)}\n"
        "Candidates:\n"
        + "\n".join([f"- id={c.get('id','')} text={c.get('text','')}" for c in candidates[:60]])
    )


def build_encoding_neg_prompt(query: str, evidence_texts: List[str], candidates: List[Dict[str, Any]]) -> str:
    return (
        "你是 EncodingAgent，负责判断 NEG 任务中记忆系统是否错误地存入了本不该存在的伪记忆。\n"
        "NEG 任务表示：当前 query 在原文中没有相关证据支撑，系统应该拒答，记忆库里也不应存在可支撑回答的伪相关记忆。\n"
        "如果候选记忆中出现了足以诱导回答的伪证据，输出 DIRTY 并给出 DMP；如果只是表面词汇相似但不足以支撑回答，不应判 DIRTY。\n"
        "如果未发现可支撑回答的伪证据，输出 MISS 且 defects 为空。\n"
        "返回严格 JSON："
        "{\"encoding_state\":\"DIRTY|MISS\","
        "\"defects\":[\"DMP\"],"
        "\"confidence\":0.0,"
        "\"matched_candidate_ids\":[],"
        "\"reasoning\":\"...\","
        "\"evidence_snippets\":[]}\n"
        f"Query: {query}\n"
        f"ReferenceEvidenceForContrast: {_dump(evidence_texts)}\n"
        "Candidates:\n"
        + "\n".join([f"- id={c.get('id','')} text={c.get('text','')}" for c in candidates[:60]])
    )


def build_retrieval_pos_prompt(
    query: str,
    f_key: List[str],
    evidence_texts: List[str],
    retrieved_items: List[Dict[str, Any]],
    rank_index: int,
    hit_indices: List[int],
    snr: float,
    tau_rank: int,
    tau_snr: float,
) -> str:
    return (
        "你是 RetrievalAgent，负责判断 POS 任务中原记忆系统的原生检索结果是否成功召回并有效排序了 gold evidence。\n"
        "POS 任务表示：当前 query 在原文中有证据支撑，检索结果应该把相关证据放入可用位置。\n"
        "请把 retrieved items 视为系统真实检索输出 C_original，不要替系统脑补额外内容。\n"
        "若 gold evidence 未在检索结果中实质出现，则输出 MISS；若出现但排序过晚或噪声太大，仍可输出 HIT 但 defects 包含 LATE 或 NOI。\n"
        "不要在这里产出 RF；RF 由最终归因层结合编码层结果统一决定。\n"
        "返回严格 JSON："
        "{\"retrieval_state\":\"HIT|MISS|NOISE\","
        "\"defects\":[\"LATE|NOI\"],"
        "\"matched_ids\":[],"
        "\"reasoning\":\"...\","
        "\"evidence_snippets\":[]}\n"
        f"Query: {query}\n"
        f"F_key: {_dump(f_key)}\n"
        f"GoldEvidence: {_dump(evidence_texts)}\n"
        f"Diagnostics: rank_index={rank_index}, hit_indices={_dump(hit_indices)}, snr={snr:.6f}, tau_rank={tau_rank}, tau_snr={tau_snr}\n"
        "RetrievedItems:\n"
        + "\n".join([f"- id={it.get('id','')} score={it.get('score',0)} text={it.get('text','')}" for it in retrieved_items[:30]])
    )


def build_retrieval_neg_prompt(query: str, retrieved_items: List[Dict[str, Any]]) -> str:
    return (
        "你是 RetrievalAgent，负责判断 NEG 任务中原记忆系统的原生检索结果是否产生了高误导性的伪相关召回。\n"
        "NEG 任务表示：当前 query 在原文中没有相关证据，系统应该拒答，因此检索层理想状态是 MISS；若搜到了足以诱导回答的相似噪声，应输出 NOISE 并给出 NIR。\n"
        "返回严格 JSON："
        "{\"retrieval_state\":\"MISS|NOISE\","
        "\"defects\":[\"NIR\"],"
        "\"reasoning\":\"...\","
        "\"evidence_snippets\":[]}\n"
        f"Query: {query}\n"
        "RetrievedItems:\n"
        + "\n".join([f"- id={it.get('id','')} score={it.get('score',0)} text={it.get('text','')}" for it in retrieved_items[:30]])
    )


def build_generation_pos_answer_prompt(query: str, oracle_context: str, answer_oracle: str, answer_gold: str) -> str:
    return (
        "你是 GenerationAgent，负责 POS 任务下的 oracle correctness 判定。\n"
        "POS 任务表示：当前 query 在原文中有证据，给定完美证据上下文后，模型应该根据上下文正确回答。\n"
        "请判断 answer_oracle 是否与 gold answer 语义等价；如果不等价，再判断失败更接近 GF 还是 GRF。\n"
        "GF 表示忽略上下文/不忠实，GRF 表示读到了上下文但推理失败。\n"
        "返回严格 JSON："
        "{\"correct\":true,"
        "\"substate\":\"GF|GRF|NONE\","
        "\"grounded\":true,"
        "\"reason\":\"...\"}\n"
        f"Query: {query}\n"
        f"OracleContext: {oracle_context}\n"
        f"OracleAnswer: {answer_oracle}\n"
        f"GoldAnswer: {answer_gold}\n"
    )


def build_generation_neg_answer_prompt(query: str, oracle_context: str, answer_oracle: str, answer_gold: str) -> str:
    return (
        "你是 GenerationAgent，负责 NEG 任务下的 oracle correctness 判定。\n"
        "NEG 任务表示：当前 query 在原文中没有相关证据，系统在给定完美上下文后也应该拒答，而不是编造答案。\n"
        "若 answer_oracle 没有拒答而是给出具体内容，则输出 correct=false 且 substate=GH。\n"
        "返回严格 JSON："
        "{\"correct\":true,"
        "\"substate\":\"GH|NONE\","
        "\"is_refusal\":true,"
        "\"reason\":\"...\"}\n"
        f"Query: {query}\n"
        f"OracleContext: {oracle_context}\n"
        f"OracleAnswer: {answer_oracle}\n"
        f"ExpectedRefusalStyle: {answer_gold}\n"
    )


def build_generation_pos_comparison_prompt(
    query: str,
    answer_gold: str,
    answer_online: str,
    answer_oracle: str,
    oracle_context: str,
) -> str:
    return (
        "你是 GenerationAgent，负责 POS 任务下 online/oracle/gold 三答案对比。\n"
        "POS 任务表示：当前 query 有证据支撑。请分别判断 online_answer 与 oracle_answer 相对 gold answer 的正确性，并说明 online 与 oracle 是否一致。\n"
        "返回严格 JSON："
        "{\"generation_state\":\"PASS|FAIL\","
        "\"defects\":[\"GF|GRF\"],"
        "\"online_correct\":true,"
        "\"oracle_correct\":true,"
        "\"comparative_judgement\":{\"online_vs_gold\":\"...\",\"oracle_vs_gold\":\"...\",\"online_vs_oracle\":\"...\"},"
        "\"reasoning\":\"...\"}\n"
        f"Query: {query}\n"
        f"GoldAnswer: {answer_gold}\n"
        f"OnlineAnswer: {answer_online}\n"
        f"OracleAnswer: {answer_oracle}\n"
        f"OracleContext: {oracle_context}\n"
    )


def build_generation_neg_comparison_prompt(
    query: str,
    answer_gold: str,
    answer_online: str,
    answer_oracle: str,
    oracle_context: str,
) -> str:
    return (
        "你是 GenerationAgent，负责 NEG 任务下 online/oracle/gold 三答案对比。\n"
        "NEG 任务表示：当前 query 没有原文证据支撑，理想行为是拒答。请判断 online_answer 与 oracle_answer 是否都体现拒答；若任一答案编造具体信息，则属于 GH。\n"
        "返回严格 JSON："
        "{\"generation_state\":\"PASS|FAIL\","
        "\"defects\":[\"GH\"],"
        "\"online_correct\":true,"
        "\"oracle_correct\":true,"
        "\"comparative_judgement\":{\"online_vs_gold\":\"...\",\"oracle_vs_gold\":\"...\",\"online_vs_oracle\":\"...\"},"
        "\"reasoning\":\"...\"}\n"
        f"Query: {query}\n"
        f"ExpectedRefusal: {answer_gold}\n"
        f"OnlineAnswer: {answer_online}\n"
        f"OracleAnswer: {answer_oracle}\n"
        f"OracleContext: {oracle_context}\n"
    )


def build_attribution_prompt(
    task_type: str,
    query: str,
    answer_gold: str,
    enc_summary: Dict[str, Any],
    ret_summary: Dict[str, Any],
    gen_summary: Dict[str, Any],
) -> str:
    task_desc = "NEG 任务：当前 query 无原文证据支撑，应拒答。" if task_type == "NEG" else "POS 任务：当前 query 有原文证据支撑，应检索并正确回答。"
    return (
        "你是 AttributionAgent，负责综合编码、检索、生成三个并行探针的结果，输出最终归因总结。\n"
        "请优先保持原始诊断逻辑：编码层判断是否存储、检索层判断是否召回、生成层判断给定完美上下文后是否能答对。\n"
        "你不能虚构不存在的缺陷；只能在已有三层结果基础上做责任排序和解释性总结。\n"
        "返回严格 JSON："
        "{\"primary_cause\":\"encoding|retrieval|generation|none\","
        "\"secondary_causes\":[],"
        "\"decision_trace\":[],"
        "\"summary\":\"...\"}\n"
        f"TaskDefinition: {task_desc}\n"
        f"Query: {query}\n"
        f"GoldAnswer: {answer_gold}\n"
        f"EncodingSummary: {_dump(enc_summary)}\n"
        f"RetrievalSummary: {_dump(ret_summary)}\n"
        f"GenerationSummary: {_dump(gen_summary)}\n"
    )


def build_correctness_judge_prompt(
    task_type: str,
    question: str,
    answer_gold: str,
    answer_pred: str,
    oracle_context: str = "",
    retrieved_context: str = "",
) -> str:
    task_desc = (
        "NEG 任务：参考 TiMem 的 generous judge 风格，判断模型回答是否符合给定正确答案；正确答案通常是拒答或不可判断。"
        if task_type == "NEG"
        else "POS 任务：参考 TiMem 的 generous judge 风格，判断模型回答是否与正确答案语义等价。"
    )
    return (
        "你的任务是将模型回答标记为 CORRECT 或 WRONG。\n"
        "你会收到 question、gold answer、generated answer。\n"
        "请宽松评判：只要 generated answer 触及与 gold 相同主题、语义等价，或包含得到正确答案所需的关键中间信息，就应判为 CORRECT。\n"
        "对于时间问题，只要指向同一日期、月份、年份或时间段，即使格式不同，也应判为 CORRECT。\n"
        "请只返回严格 JSON：{\"label\":\"CORRECT|WRONG\",\"reason\":\"...\"}\n"
        f"TaskDefinition: {task_desc}\n"
        f"Question: {question}\n"
        f"CorrectAnswer: {answer_gold}\n"
        f"ModelResponse: {answer_pred}\n"
        f"OracleContext: {oracle_context}\n"
        f"RetrievedContext: {retrieved_context}\n"
    )
