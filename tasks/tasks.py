"""
Celery 任务定义

定义异步任务，包括视频处理管道任务。
"""

from celery import current_task
from typing import Optional, Dict, Any
import logging

from .celery_app import celery_app
from .pipeline import GlomapPipeline, PipelineConfig, StepStatus

logger = logging.getLogger(__name__)


def update_task_state(step_name: str, status: StepStatus, message: str = ""):
    """
    更新 Celery 任务状态
    
    将处理进度同步到 Celery 任务元数据，前端可以通过查询任务状态获取进度。
    """
    if current_task:
        current_task.update_state(
            state="PROGRESS",
            meta={
                "current_step": step_name,
                "step_status": status.value,
                "message": message
            }
        )


@celery_app.task(bind=True, name="app.tasks.tasks.process_video_task")
def process_video_task(
    self,
    video_path: str,
    config_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    处理视频的 Celery 任务
    
    Args:
        video_path: 视频文件路径（相对于 videos_dir 或绝对路径）
        config_overrides: 可选的配置覆盖项
    
    Returns:
        处理结果字典
    
    Raises:
        Exception: 处理过程中的任何错误
    """
    logger.info(f"开始处理视频任务: {video_path}")
    
    # 创建配置
    config = PipelineConfig()
    if config_overrides:
        for key, value in config_overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    # 定义进度回调
    def on_progress(step_name: str, status: StepStatus, message: str):
        update_task_state(step_name, status, message)
    
    try:
        # 创建并运行 Pipeline
        pipeline = GlomapPipeline(
            video_path=video_path,
            config=config,
            on_progress=on_progress
        )
        
        result = pipeline.run()
        
        logger.info(f"视频处理完成: {video_path}")
        return result
        
    except Exception as e:
        logger.error(f"视频处理失败: {video_path}, 错误: {e}")
        # 更新任务状态为失败
        self.update_state(
            state="FAILURE",
            meta={
                "error": str(e),
                "video_path": video_path
            }
        )
        raise


@celery_app.task(bind=True, name="app.tasks.tasks.check_tools_task")
def check_tools_task(self) -> Dict[str, Any]:
    """
    检查工具是否可用的任务
    
    用于验证 GLOMAP、COLMAP、FFmpeg 等工具是否正确配置。
    
    Returns:
        工具检查结果
    """
    from pathlib import Path
    
    config = PipelineConfig()
    base = Path(config.base_path)
    autotracker = base / config.autotracker_dir
    
    tools = {
        "ffmpeg": autotracker / "03 FFMPEG" / "bin" / "ffmpeg.exe",
        "colmap": autotracker / "01 GLOMAP" / "colmap.exe",
        "glomap": autotracker / "01 GLOMAP" / "glomap.exe",
    }
    
    results = {}
    all_available = True
    
    for name, path in tools.items():
        exists = path.exists()
        results[name] = {
            "path": str(path),
            "available": exists
        }
        if not exists:
            all_available = False
    
    return {
        "all_available": all_available,
        "tools": results,
        "autotracker_dir": str(autotracker)
    }


# 便捷函数：提交任务
def submit_video_processing(
    video_path: str,
    config_overrides: Optional[Dict[str, Any]] = None
) -> str:
    """
    提交视频处理任务
    
    Args:
        video_path: 视频文件路径
        config_overrides: 可选的配置覆盖项
    
    Returns:
        任务 ID
    """
    task = process_video_task.delay(video_path, config_overrides)
    return task.id


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取任务状态
    
    Args:
        task_id: 任务 ID
    
    Returns:
        任务状态信息
    """
    task = process_video_task.AsyncResult(task_id)
    
    result = {
        "task_id": task_id,
        "status": task.status,
    }
    
    if task.status == "PROGRESS":
        result["progress"] = task.info
    elif task.status == "SUCCESS":
        result["result"] = task.result
    elif task.status == "FAILURE":
        result["error"] = str(task.info) if task.info else "Unknown error"
    
    return result