"""
Pipeline configuration and data classes

Contains configuration parameters and data structures required for Pipeline execution.
"""

import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    """Processing step status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineConfig:
    """Pipeline configuration"""
    # Base path
    base_path: str = ""
    
    # Tool paths (relative to base_path)
    autotracker_dir: str = "tools/AutoTracker"
    
    # Data paths (relative to base_path)
    videos_dir: str = "data/videos"
    scenes_dir: str = "data/scenes"
    
    # FFmpeg parameters
    ffmpeg_quality: int = 2  # -qscale:v parameter, 1-31, lower = better quality
    
    # COLMAP feature extraction parameters
    single_camera: bool = True
    max_image_size: int = 4096
    
    # COLMAP sequential matching parameters
    sequential_overlap: int = 15
    
    def __post_init__(self):
        if not self.base_path:
            # Default to project root directory as base path
            self.base_path = str(Path(__file__).parent.parent)


@dataclass
class StepResult:
    """Step execution result"""
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