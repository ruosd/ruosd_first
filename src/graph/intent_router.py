"""
LLM 意图路由器 — 用语义理解替代关键词匹配

原理:
  将用户问题发给 LLM，让 LLM 判断意图属于哪一类。
  LLM 能理解"上次买的那个到哪了" = 订单查询，
  而关键词匹配只能识别包含"订单"二字的句子。

节点签名:
  LangGraph 节点函数的标准格式：
    def node(state: AgentState) -> dict
  接收完整 State，返回部分更新（只写改动的字段）。
"""

import time

from ..utils.logger import get_logger
from ..utils.metrics import MetricsCollector
from .state import AgentState

logger = get_logger("intent_router")

# ── 意图分类提示词 ──
INTENT_PROMPT = """你是一个电商客服意图识别器。请分析用户的问题，判断它属于以下哪一类。

类别:
- order:   订单查询、物流跟踪、退换货、退款、修改订单、发票
- product: 产品信息、参数、价格、推荐、对比、使用问题
- service: 一般咨询、投诉、账号问题、其他不属上述两类的

只回复一个单词: order、product 或 service。

用户问题: {query}
意图:"""

# ── 关键词回退表（LLM 不可用时的降级方案）──
KEYWORD_MAP = {
    "order": ["订单", "物流", "快递", "退款", "退货", "换货", "发货", "收货", "发票", "运单", "配送"],
    "product": ["产品", "商品", "价格", "多少钱", "参数", "配置", "推荐", "对比", "型号", "规格", "功能", "性能"],
}


def classify_intent(state: AgentState) -> dict:
    """
    LangGraph 节点: 识别用户意图

    从 state["user_query"] 读取问题，
    写入 state["intent"]: "order" / "product" / "service"

    Args:
        state: AgentState（自动注入）

    Returns:
        {"intent": "order"|"product"|"service"}
    """
    query = state.get("user_query", "").strip()

    if not query:
        logger.warning("用户查询为空，默认路由到客服")
        return {"intent": "service"}

    return {"intent": _keyword_fallback(query)}


def _keyword_fallback(query: str) -> str:
    """
    关键词匹配降级方案

    当 LLM 不可用时，用此函数兜底。
    当前作为过渡方案，第三步接入 LLM 后会优先使用 LLM。
    """
    for intent, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in query:
                logger.info(f"关键词匹配: '{kw}' → {intent}")
                return intent

    logger.info("未匹配到关键词，默认路由到客服")
    return "service"


def create_intent_classifier(llm):
    """
    创建带 LLM 的意图分类器

    优化: 意图分类 max_tokens=10, temperature=0，节省约 90% 推理时间
    """
    from langchain_openai import ChatOpenAI

    from ..utils.settings import settings

    intent_llm = ChatOpenAI(
        model=settings.ALIYUN_MODEL_NAME,
        openai_api_key=settings.ALIYUN_API_KEY,
        openai_api_base=settings.ALIYUN_API_BASE,
        temperature=0,
        max_tokens=10,
    )

    async def _llm_classify(state: AgentState) -> dict:
        query = state.get("user_query", "").strip()

        if not query:
            return {"intent": "service"}

        try:
            prompt = INTENT_PROMPT.format(query=query)
            start = time.time()
            response = await intent_llm.ainvoke(prompt)
            latency = (time.time() - start) * 1000
            raw = response.content.strip().lower() if hasattr(response, "content") else str(response).strip().lower()
            logger.info(f"LLM 意图识别: query='{query[:40]}' → raw='{raw}'")

            # 提取第一个匹配的意图词
            for word in ("order", "product", "service"):
                if word in raw:
                    logger.info(f"意图结果: {word}")
                    MetricsCollector.record_intent(word, word, latency_ms=latency)
                    return {"intent": word}

            logger.warning(f"LLM 返回无法解析: '{raw}'，回退关键词")
            fallback = _keyword_fallback(query)
            MetricsCollector.record_intent(fallback, fallback, latency_ms=latency)
            return {"intent": fallback}
        except Exception as e:
            logger.warning(f"LLM 意图识别失败: {e}，回退关键词匹配")
            fallback = _keyword_fallback(query)
            MetricsCollector.record_intent(fallback, fallback, success=False)
            return {"intent": fallback}

    return _llm_classify
