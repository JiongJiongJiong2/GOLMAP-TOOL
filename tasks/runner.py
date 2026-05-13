"""
命令执行工具

提供可执行文件查找和命令运行的工具函数。
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_executable(base_dir: Path, exe_name: str) -> Path:
    """
    查找可执行文件
    
    Args:
        base_dir: 基础目录
        exe_name: 可执行文件名
    
    Returns:
        可执行文件的完整路径
    
    Raises:
        FileNotFoundError: 找不到可执行文件
    """
    # 直接在目录下查找
    direct = base_dir / exe_name
    if direct.exists():
        return direct
    
    # 在 bin 子目录下查找
    in_bin = base_dir / "bin" / exe_name
    if in_bin.exists():
        return in_bin
    
    raise FileNotFoundError(f"找不到可执行文件: {exe_name}，在 {base_dir}")


def validate_tools(glomap_dir: Path, ffmpeg_dir: Path) -> dict:
    """
    验证所需工具是否存在
    
    Args:
        glomap_dir: GLOMAP 目录
        ffmpeg_dir: FFmpeg 目录
    
    Returns:
        包含各工具路径的字典
    
    Raises:
        FileNotFoundError: 缺少必要工具
    """
    tools = {
        "ffmpeg": find_executable(ffmpeg_dir, "ffmpeg.exe"),
        "colmap": find_executable(glomap_dir, "colmap.exe"),
        "glomap": find_executable(glomap_dir, "glomap.exe")
    }
    
    return tools


def run_command(
    cmd: list[str],
    step_name: str,
    cwd: Path,
    glomap_dir: Optional[Path] = None,
    env: Optional[dict] = None
) -> subprocess.CompletedProcess:
    """
    执行命令
    
    Args:
        cmd: 命令参数列表
        step_name: 步骤名称（用于日志）
        cwd: 工作目录
        glomap_dir: GLOMAP 目录（用于添加到 PATH）
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
    if glomap_dir:
        run_env["PATH"] = f"{glomap_dir};{glomap_dir / 'bin'};{run_env.get('PATH', '')}"
    
    logger.debug(f"执行命令: {' '.join(str(c) for c in cmd)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=run_env,
        cwd=str(cwd)
    )
    
    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "未知错误"
        logger.error(f"[{step_name}] 命令执行失败: {error_msg}")
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    
    return result