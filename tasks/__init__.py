"""
Tasks 模块

包含 GLOMAP 处理管道的核心功能。
"""

from .config import PipelineConfig, StepStatus, StepResult
from .pipeline import GlomapPipeline, process_video

__all__ = [
    # Pipeline 类和配置
    "GlomapPipeline",
    "PipelineConfig",
    "StepStatus",
    "StepResult",
    "process_video",
]