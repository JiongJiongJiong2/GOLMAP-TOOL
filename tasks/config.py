"""
Pipeline 配置和数据类

包含 Pipeline 运行所需的配置参数和数据结构。
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """处理步骤状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineConfig:
    """Pipeline 配置"""
    # 基础路径
    base_path: str = ""
    
    # 工具路径（相对于 base_path）
    autotracker_dir: str = "tools/AutoTracker"
    
    # 数据路径（相对于 base_path）
    videos_dir: str = "data/videos"
    scenes_dir: str = "data/scenes"
    
    # FFmpeg 参数
    ffmpeg_quality: int = 2  # -qscale:v 参数，1-31，越小质量越高
    
    # COLMAP 特征提取参数
    single_camera: bool = True
    max_image_size: int = 4096
    
    # COLMAP 序列匹配参数
    sequential_overlap: int = 15
    
    def __post_init__(self):
        if not self.base_path:
            # 默认使用项目根目录作为基础路径
            self.base_path = str(Path(__file__).parent.parent)


@dataclass
class StepResult:
    """步骤执行结果"""
    step_name: str
    status: StepStatus
    message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "step_name": self.step_name,
            "status": self.status.value,
            "message": self.message,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "details": self.details
        }