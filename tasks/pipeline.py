"""
GLOMAP Pipeline - 3D 重建处理管道

该模块实现了从视频到稀疏点云的自动化处理流程：
1. 视频帧提取 (FFmpeg)
2. 特征提取 (COLMAP)
3. 特征匹配 (COLMAP)
4. 稀疏重建 (GLOMAP)
5. 模型导出 (COLMAP)
"""

import os
import subprocess
import shutil
import json
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
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
            # 默认使用 backend/app 作为基础路径
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
        
        # 可执行文件路径
        self.ffmpeg_exe = self._find_executable(self.ffmpeg_dir, "ffmpeg.exe")
        self.colmap_exe = self._find_executable(self.glomap_dir, "colmap.exe")
        self.glomap_exe = self._find_executable(self.glomap_dir, "glomap.exe")
        
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
    
    def _find_executable(self, base_dir: Path, exe_name: str) -> Path:
        """查找可执行文件"""
        # 直接在目录下查找
        direct = base_dir / exe_name
        if direct.exists():
            return direct
        
        # 在 bin 子目录下查找
        in_bin = base_dir / "bin" / exe_name
        if in_bin.exists():
            return in_bin
        
        raise FileNotFoundError(f"找不到可执行文件: {exe_name}，在 {base_dir}")
    
    def _validate_tools(self):
        """验证所需工具是否存在"""
        tools = {
            "FFmpeg": self.ffmpeg_exe,
            "COLMAP": self.colmap_exe,
            "GLOMAP": self.glomap_exe
        }
        
        missing = []
        for name, path in tools.items():
            if not path.exists():
                missing.append(f"{name}: {path}")
        
        if missing:
            raise FileNotFoundError(f"缺少必要工具:\n" + "\n".join(missing))
        
        # 验证视频文件
        if not self.video_path.exists():
            raise FileNotFoundError(f"视频文件不存在: {self.video_path}")
    
    def _update_progress(self, step_name: str, status: StepStatus, message: str = ""):
        """更新进度"""
        logger.info(f"[{step_name}] {status.value}: {message}")
        if self.on_progress:
            self.on_progress(step_name, status, message)
    
    def _run_command(self, cmd: list[str], step_name: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
        """
        执行命令
        
        Args:
            cmd: 命令参数列表
            step_name: 步骤名称（用于日志）
            env: 额外的环境变量
        
        Returns:
            CompletedProcess 对象
        
        Raises:
            subprocess.CalledProcessError: 命令执行失败
        """
        # 合并环境变量
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        # 添加 GLOMAP 目录到 PATH
        run_env["PATH"] = f"{self.glomap_dir};{self.glomap_dir / 'bin'};{run_env.get('PATH', '')}"
        
        logger.debug(f"执行命令: {' '.join(str(c) for c in cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=run_env,
            cwd=str(self.scene_dir)
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "未知错误"
            logger.error(f"[{step_name}] 命令执行失败: {error_msg}")
            raise subprocess.CalledProcessError(
                result.returncode, cmd, result.stdout, result.stderr
            )
        
        return result
    
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
            # 清理旧数据
            shutil.rmtree(self.scene_dir)
        
        # 创建目录结构
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.sparse_dir.mkdir(parents=True, exist_ok=True)
        
        # 定义处理步骤
        steps = [
            ("extract_frames", self.extract_frames),
            ("feature_extraction", self.run_feature_extraction),
            ("sequential_matching", self.run_sequential_matching),
            ("glomap_mapper", self.run_glomap_mapper),
            ("export_model", self.export_model),
        ]
        
        # 执行步骤
        for step_name, step_func in steps:
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
    
    def extract_frames(self) -> Dict[str, Any]:
        """
        步骤 1: 使用 FFmpeg 从视频提取帧
        
        Returns:
            包含帧数量等信息的字典
        """
        logger.info(f"提取视频帧: {self.video_path} -> {self.images_dir}")
        
        output_pattern = self.images_dir / "frame_%06d.jpg"
        
        cmd = [
            str(self.ffmpeg_exe),
            "-loglevel", "error",
            "-stats",
            "-i", str(self.video_path),
            "-qscale:v", str(self.config.ffmpeg_quality),
            str(output_pattern)
        ]
        
        self._run_command(cmd, "extract_frames")
        
        # 统计提取的帧数
        frames = list(self.images_dir.glob("*.jpg"))
        frame_count = len(frames)
        
        if frame_count == 0:
            raise RuntimeError("未能提取任何帧")
        
        logger.info(f"成功提取 {frame_count} 帧")
        
        return {"frame_count": frame_count}
    
    def run_feature_extraction(self) -> Dict[str, Any]:
        """
        步骤 2: 使用 COLMAP 进行特征提取
        
        Returns:
            特征提取相关信息
        """
        logger.info("运行 COLMAP 特征提取...")
        
        cmd = [
            str(self.colmap_exe),
            "feature_extractor",
            "--database_path", str(self.database_path),
            "--image_path", str(self.images_dir),
            "--ImageReader.single_camera", "1" if self.config.single_camera else "0",
            "--SiftExtraction.max_image_size", str(self.config.max_image_size)
        ]
        
        self._run_command(cmd, "feature_extraction")
        
        return {"database_path": str(self.database_path)}
    
    def run_sequential_matching(self) -> Dict[str, Any]:
        """
        步骤 3: 使用 COLMAP 进行序列匹配
        
        Returns:
            匹配相关信息
        """
        logger.info("运行 COLMAP 序列匹配...")
        
        cmd = [
            str(self.colmap_exe),
            "sequential_matcher",
            "--database_path", str(self.database_path),
            "--SequentialMatching.overlap", str(self.config.sequential_overlap)
        ]
        
        self._run_command(cmd, "sequential_matching")
        
        return {"overlap": self.config.sequential_overlap}
    
    def run_glomap_mapper(self) -> Dict[str, Any]:
        """
        步骤 4: 使用 GLOMAP 进行稀疏重建
        
        Returns:
            重建相关信息
        """
        logger.info("运行 GLOMAP mapper...")
        
        cmd = [
            str(self.glomap_exe),
            "mapper",
            "--database_path", str(self.database_path),
            "--image_path", str(self.images_dir),
            "--output_path", str(self.sparse_dir)
        ]
        
        self._run_command(cmd, "glomap_mapper")
        
        # 检查输出
        model_dir = self.sparse_dir / "0"
        if not model_dir.exists():
            raise RuntimeError("GLOMAP 未生成重建结果")
        
        return {"model_path": str(model_dir)}
    
    def export_model(self) -> Dict[str, Any]:
        """
        步骤 5: 导出 TXT 格式模型
        
        将 BIN 格式转换为 TXT 格式，便于其他工具读取
        
        Returns:
            导出相关信息
        """
        logger.info("导出 TXT 格式模型...")
        
        model_dir = self.sparse_dir / "0"
        
        if not model_dir.exists():
            raise RuntimeError(f"模型目录不存在: {model_dir}")
        
        # 导出到模型目录内
        cmd = [
            str(self.colmap_exe),
            "model_converter",
            "--input_path", str(model_dir),
            "--output_path", str(model_dir),
            "--output_type", "TXT"
        ]
        
        self._run_command(cmd, "export_model")
        
        # 同时导出到 sparse 目录（兼容性）
        cmd_sparse = [
            str(self.colmap_exe),
            "model_converter",
            "--input_path", str(model_dir),
            "--output_path", str(self.sparse_dir),
            "--output_type", "TXT"
        ]
        
        try:
            self._run_command(cmd_sparse, "export_model_sparse")
        except subprocess.CalledProcessError:
            # 这个步骤失败不影响整体结果
            logger.warning("导出到 sparse 目录失败，但不影响主要结果")
        
        return {
            "model_dir": str(model_dir),
            "files": [f.name for f in model_dir.glob("*.txt")]
        }


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


# 用于直接测试
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python pipeline.py <视频文件路径>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    def progress_callback(step: str, status: StepStatus, message: str):
        print(f"[{step}] {status.value}: {message}")
    
    try:
        result = process_video(video_path, on_progress=progress_callback)
        print("\n处理完成!")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"\n处理失败: {e}")
        sys.exit(1)