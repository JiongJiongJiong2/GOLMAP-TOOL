"""
GLOMAP Pipeline - 3D 重建处理管道

该模块实现了从视频到稀疏点云的自动化处理流程：
1. 视频帧提取 (FFmpeg)
2. 特征提取 (COLMAP)
3. 特征匹配 (COLMAP)
4. 稀疏重建 (GLOMAP)
5. 模型导出 (COLMAP)
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
    GLOMAP 自动化处理管道
    
    处理流程：
    1. 从视频提取帧
    2. COLMAP 特征提取
    3. COLMAP 序列匹配
    4. GLOMAP 稀疏重建
    5. 导出 TXT 格式模型
    """
    
    def __init__(
        self,
        video_path: str,
        config: Optional[PipelineConfig] = None,
        on_progress: Optional[Callable[[str, StepStatus, str], None]] = None
    ):
        """
        初始化 Pipeline
        
        Args:
            video_path: 视频文件路径（绝对路径或相对于 videos_dir 的路径）
            config: Pipeline 配置
            on_progress: 进度回调函数 (step_name, status, message)
        """
        self.config = config or PipelineConfig()
        self.on_progress = on_progress
        self.results: list[StepResult] = []
        
        # 解析视频路径
        self._setup_paths(video_path)
        
        # 验证工具是否存在
        self._validate_tools()
    
    def _setup_paths(self, video_path: str):
        """设置所有相关路径"""
        base = Path(self.config.base_path)
        autotracker = base / self.config.autotracker_dir
        
        # 工具路径
        self.glomap_dir = autotracker / "01 GLOMAP"
        self.ffmpeg_dir = autotracker / "03 FFMPEG"
        
        # 数据路径
        self.videos_dir = base / self.config.videos_dir
        self.scenes_dir = base / self.config.scenes_dir
        
        # 视频文件路径
        video_path = Path(video_path)
        if video_path.is_absolute():
            self.video_path = video_path
        else:
            self.video_path = self.videos_dir / video_path
        
        # 场景名称（视频文件名，不含扩展名）
        self.scene_name = self.video_path.stem
        
        # 场景目录结构
        self.scene_dir = self.scenes_dir / self.scene_name
        self.images_dir = self.scene_dir / "images"
        self.sparse_dir = self.scene_dir / "sparse"
        self.database_path = self.scene_dir / "database.db"
        self.status_file = self.scene_dir / "status.json"
    
    def _validate_tools(self):
        """验证所需工具是否存在"""
        self.tools = validate_tools(self.glomap_dir, self.ffmpeg_dir)
        
        # 验证视频文件
        if not self.video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {self.video_path}")
    
    def _update_progress(self, step_name: str, status: StepStatus, message: str = ""):
        """更新进度"""
        logger.info(f"[{step_name}] {status.value}: {message}")
        if self.on_progress:
            self.on_progress(step_name, status, message)
    
    def _save_status(self):
        """保存当前状态到文件"""
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
        执行单个步骤
        
        Args:
            step_name: 步骤名称
            step_func: 步骤执行函数
        
        Returns:
            StepResult 对象
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
            result.message = "成功"
            result.details = details or {}
            result.end_time = datetime.now()
            self._update_progress(step_name, StepStatus.COMPLETED, "成功")
            
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
        执行完整的处理流程
        
        Args:
            resume: 是否从上次失败的步骤继续
        
        Returns:
            处理结果字典
        """
        logger.info(f"开始处理视频: {self.video_path}")
        logger.info(f"场景目录: {self.scene_dir}")
        
        # 检查是否已存在
        if self.scene_dir.exists() and not resume:
            logger.warning(f"场景目录已存在，将覆盖: {self.scene_dir}")
            shutil.rmtree(self.scene_dir)
        
        # 创建目录结构
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.sparse_dir.mkdir(parents=True, exist_ok=True)
        
        # 定义处理步骤
        step_funcs = [
            ("extract_frames", self._step_extract_frames),
            ("feature_extraction", self._step_feature_extraction),
            ("sequential_matching", self._step_sequential_matching),
            ("glomap_mapper", self._step_glomap_mapper),
            ("export_model", self._step_export_model),
        ]
        
        # 执行步骤
        for step_name, step_func in step_funcs:
            self._execute_step(step_name, step_func)
        
        logger.info(f"处理完成: {self.scene_name}")
        
        return {
            "success": True,
            "scene_name": self.scene_name,
            "scene_dir": str(self.scene_dir),
            "sparse_dir": str(self.sparse_dir),
            "images_dir": str(self.images_dir),
            "steps": [r.to_dict() for r in self.results]
        }
    
    # === 步骤包装方法 ===
    
    def _step_extract_frames(self) -> Dict[str, Any]:
        """步骤 1: 提取帧"""
        return steps.extract_frames(
            video_path=self.video_path,
            images_dir=self.images_dir,
            ffmpeg_exe=self.tools["ffmpeg"],
            ffmpeg_quality=self.config.ffmpeg_quality,
            scene_dir=self.scene_dir,
            glomap_dir=self.glomap_dir
        )
    
    def _step_feature_extraction(self) -> Dict[str, Any]:
        """步骤 2: 特征提取"""
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
        """步骤 3: 序列匹配"""
        return steps.run_sequential_matching(
            database_path=self.database_path,
            colmap_exe=self.tools["colmap"],
            sequential_overlap=self.config.sequential_overlap,
            scene_dir=self.scene_dir,
            glomap_dir=self.glomap_dir
        )
    
    def _step_glomap_mapper(self) -> Dict[str, Any]:
        """步骤 4: GLOMAP 重建"""
        return steps.run_glomap_mapper(
            database_path=self.database_path,
            images_dir=self.images_dir,
            sparse_dir=self.sparse_dir,
            glomap_exe=self.tools["glomap"],
            scene_dir=self.scene_dir,
            glomap_dir=self.glomap_dir
        )
    
    def _step_export_model(self) -> Dict[str, Any]:
        """步骤 5: 导出模型"""
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
    处理视频的便捷函数
    
    Args:
        video_path: 视频文件路径
        config: Pipeline 配置
        on_progress: 进度回调函数
    
    Returns:
        处理结果字典
    """
    pipeline = GlomapPipeline(video_path, config, on_progress)
    return pipeline.run()