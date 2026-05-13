# COLMAP Pipeline

一个自动化的 3D 重建处理管道，用于从视频生成稀疏点云。

## 功能

- 从视频自动提取帧
- COLMAP 特征提取
- COLMAP 序列匹配
- GLOMAP 稀疏重建
- 导出 TXT 格式模型

## 目录结构

```
colmap-pipeline/
├── data/
│   ├── videos/          # 输入：放置视频文件
│   └── scenes/          # 输出：重建结果
├── tasks/
│   ├── pipeline.py      # 核心处理管道
│   └── __init__.py      # 模块导出
├── tools/
│   └── AutoTracker/
│       ├── 01 GLOMAP/   # COLMAP + GLOMAP 工具
│       ├── 03 FFMPEG/   # FFmpeg 工具
│       └── 05 SCRIPT/   # 原始批处理脚本（可选）
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## 安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 下载工具

本项目需要以下外部工具：

- **COLMAP**: 从 [colmap.github.io](https://colmap.github.io/) 下载
- **GLOMAP**: 从 [github.com/larsim/GLOMAP](https://github.com/larsim/GLOMAP) 下载
- **FFmpeg**: 从 [ffmpeg.org](https://ffmpeg.org/download.html) 下载

将工具放置到以下目录：

```
tools/AutoTracker/
├── 01 GLOMAP/
│   ├── colmap.exe
│   ├── glomap.exe
│   └── *.dll (依赖库)
└── 03 FFMPEG/
    └── bin/
        ├── ffmpeg.exe
        └── ffprobe.exe
```

## 使用方法

### 命令行

```bash
# 处理单个视频
python tasks/pipeline.py data/videos/your_video.mp4

# 处理多个视频（使用 Python）
from tasks import process_video

result = process_video("data/videos/your_video.mp4")
print(result)
```

### 作为模块使用

```python
from tasks import GlomapPipeline, PipelineConfig

# 自定义配置
config = PipelineConfig(
    ffmpeg_quality=2,         # 视频帧质量 (1-31, 越小越好)
    max_image_size=4096,      # 最大图像尺寸
    sequential_overlap=15     # 序列匹配重叠数
)

# 创建 Pipeline
pipeline = GlomapPipeline(
    video_path="data/videos/your_video.mp4",
    config=config,
    on_progress=lambda step, status, msg: print(f"[{step}] {status.value}: {msg}")
)

# 运行
result = pipeline.run()
```

## 输出结果

处理完成后，输出目录结构如下：

```
data/scenes/{scene_name}/
├── images/              # 提取的视频帧
│   ├── frame_000001.jpg
│   ├── frame_000002.jpg
│   └── ...
├── sparse/              # 稀疏重建结果
│   ├── 0/               # BIN 格式模型
│   │   ├── cameras.bin
│   │   ├── images.bin
│   │   └── points3D.bin
│   ├── cameras.txt      # TXT 格式相机参数
│   ├── images.txt       # TXT 格式图像信息
│   └── points3D.txt     # TXT 格式点云
├── database.db          # COLMAP 数据库
└── status.json          # 处理状态记录
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ffmpeg_quality` | 2 | FFmpeg 帧提取质量 (1-31, 越小质量越高) |
| `single_camera` | True | 是否假设所有帧来自同一相机 |
| `max_image_size` | 4096 | 特征提取最大图像尺寸 |
| `sequential_overlap` | 15 | 序列匹配时相邻帧的重叠数 |

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 致谢

- [COLMAP](https://colmap.github.io/) - Structure-from-Motion 工具
- [GLOMAP](https://github.com/larsim/GLOMAP) - Global Structure-from-Motion
- [FFmpeg](https://ffmpeg.org/) - 视频处理工具

## 原始脚本

本项目基于 polyfjord 的 AutoTracker 批处理脚本改写为 Python 自动化管道。

原始脚本位于 `tools/AutoTracker/05 SCRIPT/AutoTracker_v1.4.bat`。