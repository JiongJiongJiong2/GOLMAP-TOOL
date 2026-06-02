"""
Basic tests for the pipeline module.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tasks.config import PipelineConfig, StepStatus, StepResult


class TestStepStatus:
    """Tests for StepStatus enum."""

    def test_pending_value(self):
        """Test PENDING status value."""
        assert StepStatus.PENDING.value == "pending"

    def test_running_value(self):
        """Test RUNNING status value."""
        assert StepStatus.RUNNING.value == "running"

    def test_completed_value(self):
        """Test COMPLETED status value."""
        assert StepStatus.COMPLETED.value == "completed"

    def test_failed_value(self):
        """Test FAILED status value."""
        assert StepStatus.FAILED.value == "failed"

    def test_skipped_value(self):
        """Test SKIPPED status value."""
        assert StepStatus.SKIPPED.value == "skipped"


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_default_ffmpeg_quality(self):
        """Test default ffmpeg_quality value."""
        config = PipelineConfig()
        assert config.ffmpeg_quality == 2

    def test_default_single_camera(self):
        """Test default single_camera value."""
        config = PipelineConfig()
        assert config.single_camera is True

    def test_default_max_image_size(self):
        """Test default max_image_size value."""
        config = PipelineConfig()
        assert config.max_image_size == 4096

    def test_default_sequential_overlap(self):
        """Test default sequential_overlap value."""
        config = PipelineConfig()
        assert config.sequential_overlap == 15

    def test_default_autotracker_dir(self):
        """Test default autotracker_dir value."""
        config = PipelineConfig()
        assert config.autotracker_dir == "tools/AutoTracker"

    def test_default_videos_dir(self):
        """Test default videos_dir value."""
        config = PipelineConfig()
        assert config.videos_dir == "data/videos"

    def test_default_scenes_dir(self):
        """Test default scenes_dir value."""
        config = PipelineConfig()
        assert config.scenes_dir == "data/scenes"

    def test_base_path_is_set(self):
        """Test that base_path is set in __post_init__."""
        config = PipelineConfig()
        assert config.base_path != ""
        assert Path(config.base_path).exists()


class TestStepResult:
    """Tests for StepResult dataclass."""

    def test_step_result_creation(self):
        """Test basic StepResult creation."""
        result = StepResult(
            step_name="test_step",
            status=StepStatus.COMPLETED
        )
        assert result.step_name == "test_step"
        assert result.status == StepStatus.COMPLETED
        assert result.message == ""
        assert result.details == {}

    def test_step_result_with_message(self):
        """Test StepResult with message."""
        result = StepResult(
            step_name="test_step",
            status=StepStatus.FAILED,
            message="Error occurred"
        )
        assert result.message == "Error occurred"

    def test_step_result_to_dict(self):
        """Test StepResult serialization to dict."""
        result = StepResult(
            step_name="extract_frames",
            status=StepStatus.COMPLETED,
            message="Success",
            details={"frame_count": 100}
        )
        d = result.to_dict()
        
        assert d["step_name"] == "extract_frames"
        assert d["status"] == "completed"
        assert d["message"] == "Success"
        assert d["details"] == {"frame_count": 100}
        assert d["start_time"] is None
        assert d["end_time"] is None