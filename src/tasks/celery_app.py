"""
Celery 应用配置

Broker: Redis (复用已有的 Redis 服务)
结果后端: Redis (任务状态查询)
"""

import os

from celery import Celery

# Redis 连接地址（与 docker-compose 中保持一致）
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

app = Celery(
    "agent_dskf",
    broker=BROKER_URL,
    backend=BROKER_URL,  # 结果也存 Redis
    include=["src.tasks.document_tasks"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,          # 可追踪"已开始"状态
    task_acks_late=True,              # 任务完成后才确认（防丢失）
    worker_prefetch_multiplier=1,     # 每次只取一个任务（文件处理重）
)
