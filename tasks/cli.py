"""
Command-line entry point

Provides an interactive command-line interface for the Pipeline.
"""

import os
import sys
import json
from pathlib import Path

from .config import PipelineConfig, StepStatus
from .pipeline import process_video

# Supported video formats
SUPPORTED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}

# ASCII banner (pure ASCII characters, compatible with Windows cmd)
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
    """Get human-readable file size string"""
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
    """Scan directory for video files"""
    if not videos_dir.exists():
        return []
    
    videos = []
    for ext in SUPPORTED_EXTENSIONS:
        videos.extend(videos_dir.glob(f"*{ext}"))
    
    # Sort by filename
    videos.sort(key=lambda p: p.name.lower())
    return videos


def print_banner(config: PipelineConfig):
    """Print welcome message and path instructions"""
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
    Interactive video file selection
    
    Args:
        videos: List of video files
        videos_dir: Video directory
    
    Returns:
        Selected video path, or None to quit
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
        return None  # Return None to let main loop re-scan
    
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
    """Safe input() that handles EOFError"""
    try:
        return input(prompt)
    except EOFError:
        return "q"


def main():
    """Command-line main function"""
    config = PipelineConfig()
    
    # Check if running in interactive terminal
    if not sys.stdin.isatty() and len(sys.argv) < 2:
        print("Error: Interactive mode requires a terminal.")
        print("Usage: python -m tasks <video_path>")
        sys.exit(1)
    
    # If arguments provided, process directly (skip interactive mode)
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
    
    # Interactive mode
    base = Path(config.base_path)
    videos_dir = base / config.videos_dir
    
    while True:
        print_banner(config)
        videos = scan_videos(videos_dir)
        
        selected = interactive_select(videos, videos_dir)
        
        if selected is None:
            # User entered 'q' to quit
            print()
            print("  Goodbye!")
            sys.exit(0)
        
        # Confirm selection
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
        
        # Start processing
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