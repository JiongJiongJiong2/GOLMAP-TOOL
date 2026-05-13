"""
Processing step implementations

Contains individual processing step functions for the Pipeline.
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
    Step 1: Extract frames from video using FFmpeg
    
    Args:
        video_path: Video file path
        images_dir: Output image directory
        ffmpeg_exe: FFmpeg executable path
        ffmpeg_quality: Frame quality parameter (1-31)
        scene_dir: Scene directory
        glomap_dir: GLOMAP directory
    
    Returns:
        Dictionary containing frame count and other info
    """
    logger.info(f"Extracting video frames: {video_path} -> {images_dir}")
    
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
    
    # Count extracted frames
    frames = list(images_dir.glob("*.jpg"))
    frame_count = len(frames)
    
    if frame_count == 0:
        raise RuntimeError("No frames were extracted")
    
    logger.info(f"Successfully extracted {frame_count} frames")
    
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
    Step 2: Run COLMAP feature extraction
    
    Args:
        database_path: COLMAP database path
        images_dir: Image directory
        colmap_exe: COLMAP executable path
        single_camera: Whether to assume single camera
        max_image_size: Maximum image size
        scene_dir: Scene directory
        glomap_dir: GLOMAP directory
    
    Returns:
        Feature extraction related info
    """
    logger.info("Running COLMAP feature extraction...")
    
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
    Step 3: Run COLMAP sequential matching
    
    Args:
        database_path: COLMAP database path
        colmap_exe: COLMAP executable path
        sequential_overlap: Sequential matching overlap count
        scene_dir: Scene directory
        glomap_dir: GLOMAP directory
    
    Returns:
        Matching related info
    """
    logger.info("Running COLMAP sequential matching...")
    
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
    Step 4: Run GLOMAP sparse reconstruction
    
    Args:
        database_path: COLMAP database path
        images_dir: Image directory
        sparse_dir: Sparse reconstruction output directory
        glomap_exe: GLOMAP executable path
        scene_dir: Scene directory
        glomap_dir: GLOMAP directory
    
    Returns:
        Reconstruction related info
    """
    logger.info("Running GLOMAP mapper...")
    
    cmd = [
        str(glomap_exe),
        "mapper",
        "--database_path", str(database_path),
        "--image_path", str(images_dir),
        "--output_path", str(sparse_dir)
    ]
    
    run_command(cmd, "glomap_mapper", scene_dir, glomap_dir)
    
    # Check output
    model_dir = sparse_dir / "0"
    if not model_dir.exists():
        raise RuntimeError("GLOMAP did not generate reconstruction results")
    
    return {"model_path": str(model_dir)}


def export_model(
    sparse_dir: Path,
    colmap_exe: Path,
    scene_dir: Path,
    glomap_dir: Path
) -> Dict[str, Any]:
    """
    Step 5: Export model in TXT format
    
    Converts BIN format to TXT format for easier reading by other tools.
    
    Args:
        sparse_dir: Sparse reconstruction directory
        colmap_exe: COLMAP executable path
        scene_dir: Scene directory
        glomap_dir: GLOMAP directory
    
    Returns:
        Export related info
    """
    logger.info("Exporting TXT format model...")
    
    model_dir = sparse_dir / "0"
    
    if not model_dir.exists():
        raise RuntimeError(f"Model directory does not exist: {model_dir}")
    
    # Export to model directory
    cmd = [
        str(colmap_exe),
        "model_converter",
        "--input_path", str(model_dir),
        "--output_path", str(model_dir),
        "--output_type", "TXT"
    ]
    
    run_command(cmd, "export_model", scene_dir, glomap_dir)
    
    # Also export to sparse directory (for compatibility)
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
        # This step failing doesn't affect the main result
        logger.warning("Export to sparse directory failed, but main result is unaffected")
    
    return {
        "model_dir": str(model_dir),
        "files": [f.name for f in model_dir.glob("*.txt")]
    }