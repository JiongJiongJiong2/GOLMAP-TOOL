"""
处理步骤实现

包含 Pipeline 的各个处理步骤函数。
"""

import logging
from pathlib import Path
from typing import Dict, Any

from .runner import run_command

logger = logging.getLogger(__name__)


def extract_frames(
    video_path: Path,
    images_dir: Path,
    ffmpeg_exe: Path,
    ffmpeg_quality: int,
    scene_dir: Path,
    glomap_dir: Path
) -> Dict[str, Any]:
    """
    步骤 1: 使用 FFmpeg 从视频提取帧
    
    Args:
        video_path: 视频文件路径
        images_dir: 输出图像目录
        ffmpeg_exe: FFmpeg 可执行文件路径
        ffmpeg_quality: 帧质量参数 (1-31)
        scene_dir: 场景目录
        glomap_dir: GLOMAP 目录
    
    Returns:
        包含帧数量等信息的字典
    """
    logger.info(f"提取视频帧: {video_path} -> {images_dir}")
    
    output_pattern = images_dir / "frame_%06d.jpg"
    
    cmd = [
        str(ffmpeg_exe),
        "-loglevel", "error",
        "-stats",
        "-i", str(video_path),
        "-qscale:v", str(ffmpeg_quality),
        str(output_pattern)
    ]
    
    run_command(cmd, "extract_frames", scene_dir, glomap_dir)
    
    # 统计提取的帧数
    frames = list(images_dir.glob("*.jpg"))
    frame_count = len(frames)
    
    if frame_count == 0:
        raise RuntimeError("未能提取任何帧")
    
    logger.info(f"成功提取 {frame_count} 帧")
    
    return {"frame_count": frame_count}


def run_feature_extraction(
    database_path: Path,
    images_dir: Path,
    colmap_exe: Path,
    single_camera: bool,
    max_image_size: int,
    scene_dir: Path,
    glomap_dir: Path
) -> Dict[str, Any]:
    """
    步骤 2: 使用 COLMAP 进行特征提取
    
    Args:
        database_path: COLMAP 数据库路径
        images_dir: 图像目录
        colmap_exe: COLMAP 可执行文件路径
        single_camera: 是否假设单一相机
        max_image_size: 最大图像尺寸
        scene_dir: 场景目录
        glomap_dir: GLOMAP 目录
    
    Returns:
        特征提取相关信息
    """
    logger.info("运行 COLMAP 特征提取...")
    
    cmd = [
        str(colmap_exe),
        "feature_extractor",
        "--database_path", str(database_path),
        "--image_path", str(images_dir),
        "--ImageReader.single_camera", "1" if single_camera else "0",
        "--SiftExtraction.max_image_size", str(max_image_size)
    ]
    
    run_command(cmd, "feature_extraction", scene_dir, glomap_dir)
    
    return {"database_path": str(database_path)}


def run_sequential_matching(
    database_path: Path,
    colmap_exe: Path,
    sequential_overlap: int,
    scene_dir: Path,
    glomap_dir: Path
) -> Dict[str, Any]:
    """
    步骤 3: 使用 COLMAP 进行序列匹配
    
    Args:
        database_path: COLMAP 数据库路径
        colmap_exe: COLMAP 可执行文件路径
        sequential_overlap: 序列匹配重叠数
        scene_dir: 场景目录
        glomap_dir: GLOMAP 目录
    
    Returns:
        匹配相关信息
    """
    logger.info("运行 COLMAP 序列匹配...")
    
    cmd = [
        str(colmap_exe),
        "sequential_matcher",
        "--database_path", str(database_path),
        "--SequentialMatching.overlap", str(sequential_overlap)
    ]
    
    run_command(cmd, "sequential_matching", scene_dir, glomap_dir)
    
    return {"overlap": sequential_overlap}


def run_glomap_mapper(
    database_path: Path,
    images_dir: Path,
    sparse_dir: Path,
    glomap_exe: Path,
    scene_dir: Path,
    glomap_dir: Path
) -> Dict[str, Any]:
    """
    步骤 4: 使用 GLOMAP 进行稀疏重建
    
    Args:
        database_path: COLMAP 数据库路径
        images_dir: 图像目录
        sparse_dir: 稀疏重建输出目录
        glomap_exe: GLOMAP 可执行文件路径
        scene_dir: 场景目录
        glomap_dir: GLOMAP 目录
    
    Returns:
        重建相关信息
    """
    logger.info("运行 GLOMAP mapper...")
    
    cmd = [
        str(glomap_exe),
        "mapper",
        "--database_path", str(database_path),
        "--image_path", str(images_dir),
        "--output_path", str(sparse_dir)
    ]
    
    run_command(cmd, "glomap_mapper", scene_dir, glomap_dir)
    
    # 检查输出
    model_dir = sparse_dir / "0"
    if not model_dir.exists():
        raise RuntimeError("GLOMAP 未生成重建结果")
    
    return {"model_path": str(model_dir)}


def export_model(
    sparse_dir: Path,
    colmap_exe: Path,
    scene_dir: Path,
    glomap_dir: Path
) -> Dict[str, Any]:
    """
    步骤 5: 导出 TXT 格式模型
    
    将 BIN 格式转换为 TXT 格式，便于其他工具读取。
    
    Args:
        sparse_dir: 稀疏重建目录
        colmap_exe: COLMAP 可执行文件路径
        scene_dir: 场景目录
        glomap_dir: GLOMAP 目录
    
    Returns:
        导出相关信息
    """
    logger.info("导出 TXT 格式模型...")
    
    model_dir = sparse_dir / "0"
    
    if not model_dir.exists():
        raise RuntimeError(f"模型目录不存在: {model_dir}")
    
    # 导出到模型目录内
    cmd = [
        str(colmap_exe),
        "model_converter",
        "--input_path", str(model_dir),
        "--output_path", str(model_dir),
        "--output_type", "TXT"
    ]
    
    run_command(cmd, "export_model", scene_dir, glomap_dir)
    
    # 同时导出到 sparse 目录（兼容性）
    cmd_sparse = [
        str(colmap_exe),
        "model_converter",
        "--input_path", str(model_dir),
        "--output_path", str(sparse_dir),
        "--output_type", "TXT"
    ]
    
    try:
        run_command(cmd_sparse, "export_model_sparse", scene_dir, glomap_dir)
    except Exception:
        # 这个步骤失败不影响整体结果
        logger.warning("导出到 sparse 目录失败，但不影响主要结果")
    
    return {
        "model_dir": str(model_dir),
        "files": [f.name for f in model_dir.glob("*.txt")]
    }