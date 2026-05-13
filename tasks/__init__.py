"""
Tasks 模块

包含 Celery 任务定义和 GLOMAP 处理管道。
"""

from .celery_app import celery_app
from .pipeline import GlomapPipeline, PipelineConfig, StepStatus, process_video
from .tasks import (
    process_video_task,
    check_tools_task,
    submit_video_processing,
    get_task_status
)

__all__ = [
    # Celery 应用
    "celery_app",
    
    # Pipeline 类和配置
    "GlomapPipeline",
    "PipelineConfig",
    "StepStatus",
    "process_video",
    
    # Celery 任务
    "process_video_task",
    "check_tools_task",
    
    # 便捷函数
    "submit_video_processing",
    "get_task_status",
]