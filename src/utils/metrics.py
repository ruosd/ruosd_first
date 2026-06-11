"""
Agent 可观测性 — 记录 LLM 调用、工具调用、意图识别的指标
"""

import time
import json
from typing import Optional
from ..utils import get_mysql_client
from ..utils.logger import get_logger

logger = get_logger("metrics")


class MetricsCollector:
    """轻量级指标采集器，记录到 MySQL"""

    @staticmethod
    def _db():
        mysql = get_mysql_client()
        return mysql if mysql.is_connected() else None

    @staticmethod
    def record_llm_call(
        agent_name: str,
        latency_ms: float,
        success: bool,
        session_id: Optional[str] = None,
        token_count: Optional[int] = None,
        error: Optional[str] = None,
    ):
        """记录 LLM 调用"""
        db = MetricsCollector._db()
        if db is None:
            return
        data = json.dumps({"token_count": token_count, "error": error}, ensure_ascii=False)
        db.execute_update(
            "INSERT INTO agent_metrics (event_type, agent_name, event_data, latency_ms, success, session_id) VALUES (%s, %s, %s, %s, %s, %s)",
            ("llm_call", agent_name, data, int(latency_ms), success, session_id),
        )

    @staticmethod
    def record_tool_call(
        agent_name: str,
        tool_name: str,
        latency_ms: float,
        success: bool,
        session_id: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """记录工具调用"""
        db = MetricsCollector._db()
        if db is None:
            return
        data = json.dumps({"tool_name": tool_name, "error": error}, ensure_ascii=False)
        db.execute_update(
            "INSERT INTO agent_metrics (event_type, agent_name, event_data, latency_ms, success, session_id) VALUES (%s, %s, %s, %s, %s, %s)",
            ("tool_call", agent_name, data, int(latency_ms), success, session_id),
        )

    @staticmethod
    def record_intent(
        agent_name: str,
        intent: str,
        session_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ):
        """记录意图识别结果"""
        db = MetricsCollector._db()
        if db is None:
            return
        data = json.dumps({"intent": intent}, ensure_ascii=False)
        db.execute_update(
            "INSERT INTO agent_metrics (event_type, agent_name, event_data, latency_ms, success, session_id) VALUES (%s, %s, %s, %s, %s, %s)",
            ("intent", agent_name, data, int(latency_ms) if latency_ms else 0, True, session_id),
        )

    @staticmethod
    def query_summary(days: int = 7) -> dict:
        """查询指标汇总"""
        db = MetricsCollector._db()
        if db is None:
            return {}

        llm_total = db.execute_query(
            "SELECT agent_name, COUNT(*) as count, AVG(latency_ms) as avg_latency, SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count FROM agent_metrics WHERE event_type='llm_call' AND created_at > NOW() - INTERVAL %s DAY GROUP BY agent_name",
            (days,),
        )
        tool_total = db.execute_query(
            "SELECT agent_name, event_data->>'$.tool_name' as tool_name, COUNT(*) as count, SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count FROM agent_metrics WHERE event_type='tool_call' AND created_at > NOW() - INTERVAL %s DAY GROUP BY agent_name, event_data->>'$.tool_name'",
            (days,),
        )
        intent_stats = db.execute_query(
            "SELECT event_data->>'$.intent' as intent, COUNT(*) as count FROM agent_metrics WHERE event_type='intent' AND created_at > NOW() - INTERVAL %s DAY GROUP BY event_data->>'$.intent'",
            (days,),
        )

        return {
            "llm_calls": llm_total or [],
            "tool_calls": tool_total or [],
            "intent_distribution": intent_stats or [],
        }
