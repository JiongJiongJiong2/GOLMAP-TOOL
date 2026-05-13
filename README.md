```
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
  
```

An automated 3D reconstruction pipeline that generates sparse point clouds from videos.

## Features

- Automatic frame extraction from videos (FFmpeg)
- COLMAP feature extraction
- COLMAP sequential matching
- GLOMAP sparse reconstruction
- Export models in TXT format

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Download Tools

This project requires the following external tools:

- **COLMAP**: Download from [colmap.github.io](https://colmap.github.io/)
- **GLOMAP**: Download from [github.com/colmap/glomap](https://github.com/colmap/glomap)
- **FFmpeg**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

Place the tools in the following directory structure:

```
tools/AutoTracker/
├── 01 GLOMAP/
│   ├── colmap.exe
│   ├── glomap.exe
│   └── *.dll (dependency libraries)
└── 03 FFMPEG/
    └── bin/
        ├── ffmpeg.exe
        └── ffprobe.exe
```

### 3. Place Your Video

Put your video files in the `data/videos/` directory:

```
data/videos/
├── your_video.mp4
├── another_video.mov
└── ...
```

Supported formats: `.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`, `.flv`, `.webm`

### 4. Run the Pipeline

**Important**: You must run from the project root directory!

```bash
# Navigate to project root
cd E:\github\colmap pipline

# Interactive mode (select video from list)
python -m tasks

# Or directly specify a video
python -m tasks data/videos/your_video.mp4
```

### Interactive Mode

When you run `python -m tasks` without arguments, you'll see an interactive menu:

```
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
  
  3D Reconstruction Pipeline - Video to Sparse Point Cloud

  Input:  Place your video files in: data/videos/
  Output: Reconstruction results in: data/scenes/

  Supported formats: .avi, .flv, .mkv, .mov, .mp4, .webm, .wmv
------------------------------------------------------------

  Videos found in data/videos/:

    [1] my_video.mp4  (125.3 MB)
    [2] drone_footage.mp4  (2.1 GB)

  Select a video to process [1-2] or 'q' to quit:
  > 
```

## Output Structure

After processing, results are saved to `data/scenes/{scene_name}/`:

```
data/scenes/{scene_name}/
├── images/              # Extracted video frames
│   ├── frame_000001.jpg
│   ├── frame_000002.jpg
│   └── ...
├── sparse/              # Sparse reconstruction results
│   ├── 0/               # BIN format model
│   │   ├── cameras.bin
│   │   ├── images.bin
│   │   └── points3D.bin
│   ├── cameras.txt      # TXT format camera parameters
│   ├── images.txt       # TXT format image info
│   └── points3D.txt     # TXT format point cloud
├── database.db          # COLMAP database
└── status.json          # Processing status log
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `ffmpeg_quality` | 2 | FFmpeg frame extraction quality (1-31, lower = better quality) |
| `single_camera` | True | Assume all frames from the same camera |
| `max_image_size` | 4096 | Maximum image size for feature extraction |
| `sequential_overlap` | 15 | Overlap count for sequential matching |

## Programmatic Usage

```python
from tasks import GlomapPipeline, PipelineConfig

# Custom configuration
config = PipelineConfig(
    ffmpeg_quality=2,         # Frame quality (1-31, lower = better)
    max_image_size=4096,      # Max image size
    sequential_overlap=15     # Sequential matching overlap
)

# Create pipeline
pipeline = GlomapPipeline(
    video_path="data/videos/your_video.mp4",
    config=config,
    on_progress=lambda step, status, msg: print(f"[{step}] {status.value}: {msg}")
)

# Run
result = pipeline.run()
```

## Project Structure

```
colmap-pipeline/
├── data/
│   ├── videos/          # Input: place video files here
│   └── scenes/          # Output: reconstruction results
├── tasks/
│   ├── __init__.py      # Module exports
│   ├── __main__.py      # Module entry point
│   ├── cli.py           # Command-line interface
│   ├── config.py        # Configuration and data classes
│   ├── pipeline.py      # Core pipeline class
│   ├── runner.py        # Command execution utilities
│   └── steps.py         # Individual step implementations
├── tools/
│   └── AutoTracker/
│       ├── 01 GLOMAP/   # COLMAP + GLOMAP executables
│       ├── 03 FFMPEG/   # FFmpeg executables
│       └── 05 SCRIPT/   # Original batch scripts (optional)
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- [COLMAP](https://colmap.github.io/) - Structure-from-Motion tool
- [GLOMAP](https://github.com/colmap/glomap) - Global Structure-from-Motion
- [FFmpeg](https://ffmpeg.org/) - Video processing tool

## Original Scripts

This project is based on polyfjord's AutoTracker batch scripts, rewritten as a Python automation pipeline.

Original scripts located at `tools/AutoTracker/05 SCRIPT/AutoTracker_v1.4.bat`.