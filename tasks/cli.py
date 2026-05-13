"""
命令行入口

提供 Pipeline 的交互式命令行接口。
"""

import os
import sys
import json
from pathlib import Path

from .config import PipelineConfig, StepStatus
from .pipeline import process_video

# 支持的视频格式
SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}

# ASCII 标题 (纯 ASCII 字符，兼容 Windows cmd)
BANNER = r"""
 ██████╗  ██████╗ ██╗     ███╗   ███╗ █████╗ ██████╗ 
██╔════╝ ██╔═══██╗██║     ████╗ ████║██╔══██╗██╔══██╗
██║  ███╗██║   ██║██║     ██╔████╔██║███████║██████╔╝
██║   ██║██║   ██║██║     ██║╚██╔╝██║██╔══██║██╔═══╝ 
╚██████╔╝╚██████╔╝███████╗██║ ╚═╝ ██║██║  ██║██║     
 ╚═════╝  ╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝     
                                                     
████████╗ ██████╗  ██████╗ ██╗                       
╚══██╔══╝██╔═══██╗██╔═══██╗██║                       
   ██║   ██║   ██║██║   ██║██║                       
   ██║   ██║   ██║██║   ██║██║                       
   ██║   ╚██████╔╝╚██████╔╝███████╗                  
   ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝                  
                                                                                
"""


def get_video_size(video_path: Path) -> str:
    """获取文件大小的可读字符串"""
    size = video_path.stat().st_size
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


def scan_videos(videos_dir: Path) -> list[Path]:
    """扫描目录中的视频文件"""
    if not videos_dir.exists():
        return []
    
    videos = []
    for ext in SUPPORTED_EXTENSIONS:
        videos.extend(videos_dir.glob(f"*{ext}"))
    
    # 按文件名排序
    videos.sort(key=lambda p: p.name.lower())
    return videos


def print_banner(config: PipelineConfig):
    """打印欢迎信息和路径说明"""
    base = Path(config.base_path)
    videos_dir = base / config.videos_dir
    scenes_dir = base / config.scenes_dir
    
    print(BANNER)
    print("  3D Reconstruction Pipeline - Video to Sparse Point Cloud")
    print()
    print(f"  Input:  Place your video files in: {videos_dir}")
    print(f"  Output: Reconstruction results in: {scenes_dir}")
    print()
    print(f"  Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    print()
    print("-" * 60)


def interactive_select(videos: list[Path], videos_dir: Path) -> Path | None:
    """
    交互式选择视频文件
    
    Args:
        videos: 视频文件列表
        videos_dir: 视频目录
    
    Returns:
        选中的视频路径，或 None 表示退出
    """
    if not videos:
        print()
        print("  No video files found in:", videos_dir)
        print()
        print("  Please place your video files in that directory.")
        print(f"  Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        print()
        print("  Press Enter to refresh, or 'q' to quit:")
        
        choice = safe_input().strip().lower()
        if choice == 'q':
            return None
        return None  # 返回 None 让主循环重新扫描
    
    print()
    print(f"  Videos found in {videos_dir}:")
    print()
    
    for i, video in enumerate(videos, 1):
        size_str = get_video_size(video)
        print(f"    [{i}] {video.name}  ({size_str})")
    
    print()
    print(f"  Select a video to process [1-{len(videos)}] or 'q' to quit:")
    
    while True:
        choice = safe_input("  > ").strip().lower()
        
        if choice == 'q':
            return None
        
        try:
            index = int(choice)
            if 1 <= index <= len(videos):
                return videos[index - 1]
            print(f"  Invalid selection. Please enter 1-{len(videos)}.")
        except ValueError:
            print("  Invalid input. Enter a number or 'q' to quit.")


def safe_input(prompt: str = "") -> str:
    """安全的 input()，处理 EOFError"""
    try:
        return input(prompt)
    except EOFError:
        return "q"


def main():
    """命令行主函数"""
    config = PipelineConfig()
    
    # 检查是否在交互终端中
    if not sys.stdin.isatty() and len(sys.argv) < 2:
        print("Error: Interactive mode requires a terminal.")
        print("Usage: python -m tasks <video_path>")
        sys.exit(1)
    
    # 如果传了参数，直接处理（跳过交互）
    if len(sys.argv) >= 2:
        video_path = sys.argv[1]
        
        def progress_callback(step: str, status: StepStatus, message: str):
            print(f"  [{step}] {status.value}: {message}")
        
        try:
            result = process_video(video_path, config=config, on_progress=progress_callback)
            print()
            print("  Processing complete!")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"\n  Processing failed: {e}")
            sys.exit(1)
        return
    
    # 交互式模式
    base = Path(config.base_path)
    videos_dir = base / config.videos_dir
    
    while True:
        print_banner(config)
        videos = scan_videos(videos_dir)
        
        selected = interactive_select(videos, videos_dir)
        
        if selected is None:
            # 检查是否用户输入了 'q'
            print()
            print("  Goodbye!")
            sys.exit(0)
        
        # 确认选择
        scene_name = selected.stem
        scenes_dir = base / config.scenes_dir / scene_name
        
        print()
        print(f"  Processing: {selected.name}")
        print(f"  Output:     {scenes_dir}")
        print()
        print("  Press Enter to start, or 'c' to cancel:")
        
        confirm = safe_input("  > ").strip().lower()
        if confirm == 'c':
            continue
        
        # 开始处理
        def progress_callback(step: str, status: StepStatus, message: str):
            print(f"  [{step}] {status.value}: {message}")
        
        try:
            result = process_video(str(selected), config=config, on_progress=progress_callback)
            print()
            print("  Processing complete!")
            print(f"  Results saved to: {scenes_dir}")
            print()
            print("  Press Enter to process another video, or 'q' to quit:")
            
            next_action = safe_input("  > ").strip().lower()
            if next_action == 'q':
                print()
                print("  Goodbye!")
                sys.exit(0)
        except Exception as e:
            print(f"\n  Processing failed: {e}")
            print()
            print("  Press Enter to try another video, or 'q' to quit:")
            
            next_action = safe_input("  > ").strip().lower()
            if next_action == 'q':
                print()
                print("  Goodbye!")
                sys.exit(0)


if __name__ == "__main__":
    main()