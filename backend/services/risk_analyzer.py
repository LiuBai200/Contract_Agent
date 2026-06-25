from backend.db.models import ChatMessage
from backend.services.qwen_client import QwenClient


async def analyze_contract_risk(
    question: str,
    hits: list[dict],
    history: list[ChatMessage],
    review_rules: str | None = None,
) -> str:
    if not hits:
        return "我没有在你已上传的合同里检索到相关条款。请先上传合同，或换一种问法再试。"

    system_prompt = (
        "你是合同审查 RAG Agent。必须只基于给定合同片段回答，不能凭空编造。"
        "回答要包含：结论、风险点、原文依据、修改建议。"
        "引用原文时使用 [1]、[2] 这种编号。"
        "如果用户提供了自定义审查规则，必须优先按照这些规则识别风险和给出修改建议。"
    )
    user_prompt = _build_prompt(question, hits, history, review_rules)
    return await QwenClient().complete(system_prompt, user_prompt, temperature=0.2)


async def analyze_contract_risk_stream(
    question: str,
    hits: list[dict],
    history: list[ChatMessage],
    review_rules: str | None = None,
):
    if not hits:
        yield "我没有在你已上传的合同里检索到相关条款。请先上传合同，或换一种问法再试。"
        return

    system_prompt = (
        "你是合同审查 RAG Agent。必须只基于给定合同片段回答，不能凭空编造。"
        "回答要包含：结论、风险点、原文依据、修改建议。"
        "引用原文时使用 [1]、[2] 这种编号。"
        "如果用户提供了自定义审查规则，必须优先按照这些规则识别风险和给出修改建议。"
    )
    user_prompt = _build_prompt(question, hits, history, review_rules)
    async for chunk in QwenClient().complete_stream(system_prompt, user_prompt, temperature=0.2):
        yield chunk


def _build_prompt(
    question: str,
    hits: list[dict],
    history: list[ChatMessage],
    review_rules: str | None = None,
) -> str:
    history_text = "\n".join([f"{message.role}: {message.content}" for message in history[-6:]])
    rules_text = (review_rules or "").strip()
    clauses = []
    for index, hit in enumerate(hits, start=1):
        metadata = hit["metadata"]
        source = metadata.get("filename", "unknown")
        location = metadata.get("clause_title") or metadata.get("page") or metadata.get("paragraph") or metadata.get("slide")
        clauses.append(f"[{index}] 来源: {source}, 位置: {location}\n{hit['content']}")

    return (
        f"历史对话：\n{history_text or '无'}\n\n"
        f"自定义审查规则：\n{rules_text or '无'}\n\n"
        f"用户问题：{question}\n\n"
        f"检索到的合同片段：\n\n" + "\n\n".join(clauses)
    )
