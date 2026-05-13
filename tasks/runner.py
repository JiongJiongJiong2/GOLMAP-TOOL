"""
Command execution utilities

Provides utility functions for finding executables and running commands.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def find_executable(base_dir: Path, exe_name: str) -> Path:
    """
    Find an executable file
    
    Args:
        base_dir: Base directory
        exe_name: Executable file name
    
    Returns:
        Full path to the executable
    
    Raises:
        FileNotFoundError: Executable not found
    """
    # Search directly in the directory
    direct = base_dir / exe_name
    if direct.exists():
        return direct
    
    # Search in bin subdirectory
    in_bin = base_dir / "bin" / exe_name
    if in_bin.exists():
        return in_bin
    
    raise FileNotFoundError(f"Executable not found: {exe_name} in {base_dir}")


def validate_tools(glomap_dir: Path, ffmpeg_dir: Path) -> dict:
    """
    Validate that required tools exist
    
    Args:
        glomap_dir: GLOMAP directory
        ffmpeg_dir: FFmpeg directory
    
    Returns:
        Dictionary containing paths to each tool
    
    Raises:
        FileNotFoundError: Missing required tool
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
    Execute a command
    
    Args:
        cmd: Command argument list
        step_name: Step name (for logging)
        cwd: Working directory
        glomap_dir: GLOMAP directory (to add to PATH)
        env: Additional environment variables
    
    Returns:
        CompletedProcess object
    
    Raises:
        subprocess.CalledProcessError: Command execution failed
    """
    # Merge environment variables
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    
    # Add GLOMAP directory to PATH
    if glomap_dir:
        run_env["PATH"] = f"{glomap_dir};{glomap_dir / 'bin'};{run_env.get('PATH', '')}"
    
    logger.debug(f"Executing command: {' '.join(str(c) for c in cmd)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=run_env,
        cwd=str(cwd)
    )
    
    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "Unknown error"
        logger.error(f"[{step_name}] Command failed: {error_msg}")
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    
    return result