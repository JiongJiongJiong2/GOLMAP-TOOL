"""
GLOMAP Pipeline - 3D Reconstruction Pipeline

This module implements an automated processing pipeline from video to sparse point cloud:
1. Video frame extraction (FFmpeg)
2. Feature extraction (COLMAP)
3. Feature matching (COLMAP)
4. Sparse reconstruction (GLOMAP)
5. Model export (COLMAP)
"""

import json
import shutil
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from .config import PipelineConfig, StepStatus, StepResult
from .runner import validate_tools
from . import steps

logger = logging.getLogger(__name__)


class GlomapPipeline:
    """
    GLOMAP Automated Processing Pipeline
    
    Processing flow:
    1. Extract frames from video
    2. COLMAP feature extraction
    3. COLMAP sequential matching
    4. GLOMAP sparse reconstruction
    5. Export TXT format model
    """
    
    def __init__(
        self,
        video_path: str,
        config: Optional[PipelineConfig] = None,
        on_progress: Optional[Callable[[str, StepStatus, str], None]] = None
    ):
        """
        Initialize Pipeline
        
        Args:
            video_path: Video file path (absolute or relative to videos_dir)
            config: Pipeline configuration
            on_progress: Progress callback function (step_name, status, message)
        """
        self.config = config or PipelineConfig()
        self.on_progress = on_progress
        self.results: list[StepResult] = []
        
        # Parse video path
        self._setup_paths(video_path)
        
        # Validate tools exist
        self._validate_tools()
    
    def _setup_paths(self, video_path: str):
        """Set up all related paths"""
        base = Path(self.config.base_path)
        autotracker = base / self.config.autotracker_dir
        
        # Tool paths
        self.glomap_dir = autotracker / "01 GLOMAP"
        self.ffmpeg_dir = autotracker / "03 FFMPEG"
        
        # Data paths
        self.videos_dir = base / self.config.videos_dir
        self.scenes_dir = base / self.config.scenes_dir
        
        # Video file path
        video_path = Path(video_path)
        if video_path.is_absolute():
            self.video_path = video_path
        else:
            self.video_path = self.videos_dir / video_path
        
        # Scene name (video filename without extension)
        self.scene_name = self.video_path.stem
        
        # Scene directory structure
        self.scene_dir = self.scenes_dir / self.scene_name
        self.images_dir = self.scene_dir / "images"
        self.sparse_dir = self.scene_dir / "sparse"
        self.database_path = self.scene_dir / "database.db"
        self.status_file = self.scene_dir / "status.json"
    
    def _validate_tools(self):
        """Validate required tools exist"""
        self.tools = validate_tools(self.glomap_dir, self.ffmpeg_dir)
        
        # Validate video file
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")
    
    def _update_progress(self, step_name: str, status: StepStatus, message: str = ""):
        """Update progress"""
        logger.info(f"[{step_name}] {status.value}: {message}")
        if self.on_progress:
            self.on_progress(step_name, status, message)
    
    def _save_status(self):
        """Save current status to file"""
        status = {
            "scene_name": self.scene_name,
            "video_path": str(self.video_path),
            "last_updated": datetime.now().isoformat(),
            "steps": [r.to_dict() for r in self.results]
        }
        
        self.scene_dir.mkdir(parents=True, exist_ok=True)
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
    
    def _execute_step(self, step_name: str, step_func: Callable) -> StepResult:
        """
        Execute a single step
        
        Args:
            step_name: Step name
            step_func: Step execution function
        
        Returns:
            StepResult object
        """
        result = StepResult(
            step_name=step_name,
            status=StepStatus.RUNNING,
            start_time=datetime.now()
        )
        
        self._update_progress(step_name, StepStatus.RUNNING)
        
        try:
            details = step_func()
            result.status = StepStatus.COMPLETED
            result.message = "Success"
            result.details = details or {}
            result.end_time = datetime.now()
            self._update_progress(step_name, StepStatus.COMPLETED, "Success")
            
        except Exception as e:
            result.status = StepStatus.FAILED
            result.message = str(e)
            result.end_time = datetime.now()
            self._update_progress(step_name, StepStatus.FAILED, str(e))
            raise
        
        finally:
            self.results.append(result)
            self._save_status()
        
        return result
    
    def run(self, resume: bool = False) -> Dict[str, Any]:
        """
        Execute the complete processing pipeline
        
        Args:
            resume: Whether to resume from last failed step
        
        Returns:
            Processing result dictionary
        """
        logger.info(f"Starting video processing: {self.video_path}")
        logger.info(f"Scene directory: {self.scene_dir}")
        
        # Check if already exists
        if self.scene_dir.exists() and not resume:
            logger.warning(f"Scene directory already exists, will overwrite: {self.scene_dir}")
            shutil.rmtree(self.scene_dir)
        
        # Create directory structure
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.sparse_dir.mkdir(parents=True, exist_ok=True)
        
        # Define processing steps
        step_funcs = [
            ("extract_frames", self._step_extract_frames),
            ("feature_extraction", self._step_feature_extraction),
            ("sequential_matching", self._step_sequential_matching),
            ("glomap_mapper", self._step_glomap_mapper),
            ("export_model", self._step_export_model),
        ]
        
        # Execute steps
        for step_name, step_func in step_funcs:
            self._execute_step(step_name, step_func)
        
        logger.info(f"Processing complete: {self.scene_name}")
        
        return {
            "success": True,
            "scene_name": self.scene_name,
            "scene_dir": str(self.scene_dir),
            "sparse_dir": str(self.sparse_dir),
            "images_dir": str(self.images_dir),
            "steps": [r.to_dict() for r in self.results]
        }
    
    # === Step wrapper methods ===
    
    def _step_extract_frames(self) -> Dict[str, Any]:
        """Step 1: Extract frames"""
        return steps.extract_frames(
            video_path=self.video_path,
            images_dir=self.images_dir,
            ffmpeg_exe=self.tools["ffmpeg"],
            ffmpeg_quality=self.config.ffmpeg_quality,
            scene_dir=self.scene_dir,
            glomap_dir=self.glomap_dir
        )
    
    def _step_feature_extraction(self) -> Dict[str, Any]:
        """Step 2: Feature extraction"""
        return steps.run_feature_extraction(
            database_path=self.database_path,
            images_dir=self.images_dir,
            colmap_exe=self.tools["colmap"],
            single_camera=self.config.single_camera,
            max_image_size=self.config.max_image_size,
            scene_dir=self.scene_dir,
            glomap_dir=self.glomap_dir
        )
    
    def _step_sequential_matching(self) -> Dict[str, Any]:
        """Step 3: Sequential matching"""
        return steps.run_sequential_matching(
            database_path=self.database_path,
            colmap_exe=self.tools["colmap"],
            sequential_overlap=self.config.sequential_overlap,
            scene_dir=self.scene_dir,
            glomap_dir=self.glomap_dir
        )
    
    def _step_glomap_mapper(self) -> Dict[str, Any]:
        """Step 4: GLOMAP reconstruction"""
        return steps.run_glomap_mapper(
            database_path=self.database_path,
            images_dir=self.images_dir,
            sparse_dir=self.sparse_dir,
            glomap_exe=self.tools["glomap"],
            scene_dir=self.scene_dir,
            glomap_dir=self.glomap_dir
        )
    
    def _step_export_model(self) -> Dict[str, Any]:
        """Step 5: Export model"""
        return steps.export_model(
            sparse_dir=self.sparse_dir,
            colmap_exe=self.tools["colmap"],
            scene_dir=self.scene_dir,
            glomap_dir=self.glomap_dir
        )


def process_video(
    video_path: str,
    config: Optional[PipelineConfig] = None,
    on_progress: Optional[Callable[[str, StepStatus, str], None]] = None
) -> Dict[str, Any]:
    """
    Convenience function for processing video
    
    Args:
        video_path: Video file path
        config: Pipeline configuration
        on_progress: Progress callback function
    
    Returns:
        Processing result dictionary
    """
    pipeline = GlomapPipeline(video_path, config, on_progress)
    return pipeline.run()