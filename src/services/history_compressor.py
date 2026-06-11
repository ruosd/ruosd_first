"""
对话历史压缩器 — 超长对话自动摘要归档

原理:
  当对话历史 token 数超过阈值时，将最早的消息压缩为一段摘要，
  LLM 只需处理 [摘要] + [最近 N 轮对话]，大幅节省 token。

使用:
  from src.services.history_compressor import compress_history
  compressed = await compress_history(messages, llm)
"""


import tiktoken

# 阈值：超过此 token 数触发压缩
MAX_HISTORY_TOKENS = 3000
# 压缩后保留的最近消息数
KEEP_RECENT = 6


def count_tokens(text: str) -> int:
    """估算文本的 token 数"""
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return len(text) // 2  # 粗略估算：中文约 2 字符/token


def _messages_to_text(messages: list[dict[str, str]]) -> str:
    """消息列表转文本"""
    lines = []
    for m in messages:
        role = "用户" if m.get("role") == "user" else "客服"
        content = m.get("content", "")[:500]  # 每条截取前500字符
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


async def compress_history(
    messages: list[dict[str, str]],
    llm=None,
    max_tokens: int = MAX_HISTORY_TOKENS,
    keep_recent: int = KEEP_RECENT,
) -> list[dict[str, str]]:
    """
    压缩对话历史

    Args:
        messages: 完整对话历史 [{"role": "user/assistant", "content": "..."}]
        llm: LLM 实例（用于生成摘要）
        max_tokens: 触发压缩的 token 阈值
        keep_recent: 保留最近的消息数

    Returns:
        压缩后的消息列表
    """
    if not messages:
        return messages

    # 计算总 token 数
    full_text = _messages_to_text(messages)
    total_tokens = count_tokens(full_text)

    if total_tokens <= max_tokens:
        return messages  # 无需压缩

    # 分割：旧消息 + 最近消息
    split_point = max(0, len(messages) - keep_recent)
    old_messages = messages[:split_point]
    recent_messages = messages[split_point:]

    if not old_messages:
        return recent_messages

    # 生成摘要
    old_text = _messages_to_text(old_messages)
    summary = await _generate_summary(old_text, llm)

    # 构建压缩后的消息列表
    compressed = [{
        "role": "system",
        "content": f"[对话历史摘要] {summary}"
    }]
    compressed.extend(recent_messages)

    return compressed


async def _generate_summary(text: str, llm=None) -> str:
    """用 LLM 生成对话摘要"""
    if llm is None:
        # 无 LLM 时的降级方案：截取前200字符
        return f"之前的对话内容（共{count_tokens(text)} tokens）：{text[:200]}..."

    try:
        prompt = f"""请用1-2句话总结以下客服对话的关键信息，保留用户的诉求和已解决的问题：

{text}

摘要："""

        response = await llm.ainvoke(prompt)
        return response.content.strip() if hasattr(response, 'content') else str(response).strip()
    except Exception:
        return f"（共{count_tokens(text)} tokens 的历史对话）"
