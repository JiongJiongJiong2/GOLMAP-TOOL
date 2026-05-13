"""
命令行入口

提供 Pipeline 的命令行接口。
"""

import sys
import json

from .config import PipelineConfig, StepStatus
from .pipeline import process_video


def main():
    """命令行主函数"""
    if len(sys.argv) < 2:
        print("用法: python -m tasks.cli <视频文件路径>")
        print("   或: python tasks/cli.py <视频文件路径>")
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


if __name__ == "__main__":
    main()