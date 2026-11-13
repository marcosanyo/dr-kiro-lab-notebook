"""Settings of the body-lab instrument (body-lab design 2-4).

The camera and start values are those of `body-lab/model/README.md`. Timing (control rate, trial length,
settle time) is read from the wiring file, never copied here.
"""

from dataclasses import dataclass
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[3] / "model"
MODEL_FILE = MODEL_DIR / "specimen_01.xml"
WIRING_FILE = MODEL_DIR / "specimen_01.wiring.json"


@dataclass(frozen=True)
class Settings:
    # Camera straight above the view centre (model README).
    camera_height_m: float = 2.0
    camera_fovy_deg: float = 40.0
    image_width: int = 1920
    image_height: int = 1080
    # The body starts this far behind the view centre, facing +x (model README).
    start_behind_m: float = 0.45
    # Rotation of the start pose about the forward axis; 180 starts the body turned over (tests only).
    start_roll_deg: float = 0.0
    # Servo targets move toward their command at no more than this rate (model README).
    servo_rate_deg_s: float = 600.0
    # Series sampling (body-lab Requirement 2.2).
    series_step_s: float = 0.1
    # Picture: frames every frame_step_s, laid out in rows (Requirement 4).
    # May change after the first session.
    frame_count: int = 10
    frame_step_s: float = 0.5
    frame_columns: int = 5
    frame_width: int = 320
    frame_height: int = 180
