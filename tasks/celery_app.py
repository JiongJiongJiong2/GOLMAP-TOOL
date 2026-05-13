"""
Celery 应用配置

配置 Celery 用于异步任务处理，支持 GLOMAP 处理管道等长时间运行的任务。
"""

from celery import Celery
import os

# 从环境变量获取 Redis 配置，默认使用本地 Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 创建 Celery 应用
celery_app = Celery(
    "3dgs_app",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks.tasks"]  # 自动发现任务模块
)

# Celery 配置
celery_app.conf.update(
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 任务追踪
    task_track_started=True,
    task_time_limit=3600 * 4,  # 任务最长运行 4 小时
    task_soft_time_limit=3600 * 3.5,  # 3.5 小时后发送软超时信号
    
    # 结果过期时间
    result_expires=3600 * 24 * 7,  # 结果保留 7 天
    
    # Worker 配置
    worker_prefetch_multiplier=1,  # 每次只获取一个任务（适合长时间任务）
    worker_concurrency=1,  # 单 worker 并发数（GLOMAP 占用大量资源）
    
    # 任务路由（可选，未来扩展用）
    task_routes={
        "app.tasks.tasks.process_video_task": {"queue": "glomap"},
        "app.tasks.tasks.*": {"queue": "default"},
    },
    
    # 任务默认队列
    task_default_queue="default",
)

# 可选：配置任务优先级
celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5