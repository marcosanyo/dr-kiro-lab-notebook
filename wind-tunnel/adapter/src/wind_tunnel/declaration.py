"""What Dr. Kiro is told about the wind tunnel (wind-tunnel Requirements 1, 3, 4, 11; design 1).

The knob texts are those of Requirement 3.2 and `measured_by` is that of Requirement 4.2. The plate thickness
in the `splitter` text is written from the model settings, so the number exists once. Every sentence here
is a definition; none says what a knob does.
"""

from bench.adapter import Declaration, Measurement, NumberKnob
from wind_tunnel_model.settings import Settings

BUDGET = 24

GOAL = "Find the setting of the four knobs with the lowest cd among the settings where shedding is 0."

ASPECT_TEXT = (
    "The length of the body, in body heights. The height of the body is 1, so this is the length divided "
    "by the height."
)

CORNER_TEXT = (
    "The rounding of the body's corners: the radius of each corner arc, as a fraction of half of the "
    "body's shorter side. 0 gives square corners; 1 gives the largest radius that fits."
)

# {thickness} is filled from the model settings (`f"{t:g}"`).
SPLITTER_TEXT = (
    "The length of the thin plate attached to the back of the body, the end facing away from the "
    "oncoming flow, in body heights. The length is counted from the rearmost point of the body without the "
    "plate. The plate lies along the line through the middle of the body along its length, is attached with "
    "no gap, and is {thickness} body heights thick. 0 means there is no plate."
)

ANGLE_TEXT = (
    "The angle of attack, in degrees: the angle between the body's length direction and the direction of "
    "the oncoming flow, which goes in the +x direction. 0 means the two directions are the same. The body "
    "is turned about its centre, the middle of its length and of its height, and the plate turns with it. "
    "A positive angle moves the front end of the body, the end facing the oncoming flow, toward +y, and the "
    "back end toward -y."
)

MEASURED_BY = (
    "The oncoming flow goes in the +x direction, and the lift is the force along +y. Forces are per unit "
    "depth and are divided by one half of the density times the square of the free-stream speed times the "
    "height; the height is a fixed length that no knob changes; lengths are in units of the height and "
    "speeds in units of the free-stream speed. "
    "cd is the drag coefficient: the force along the flow on the whole body, taken as the mean over the "
    "settled part of the trial. "
    "cl_mean is the mean of the lift coefficient over the settled part. "
    "cl_amp is half of the difference between the largest and the smallest lift coefficient over the "
    "settled part (half the peak-to-peak value). "
    "strouhal is the frequency of the lift coefficient's oscillation, times the height, divided by the "
    "free-stream speed. "
    "shedding is 1 when cl_amp is above 0.01 and 0 otherwise. "
    "When the flow has not settled within the trial, none of the five is measured: each is the not-measured "
    "outcome not_settled, and the picture is still returned. This says nothing about whether a longer "
    "trial would settle."
)

# The not-measured outcome of a trial whose flow has not settled within the trial (Requirement 4.5). It is
# declared for all five measurements; `strouhal` has `not_shedding` as well (Requirement 4.4).
NOT_SETTLED = "not_settled"


def knob_texts(settings: Settings) -> dict[str, str]:
    """The four knob texts, with the plate thickness taken from the settings."""
    return {
        "aspect": ASPECT_TEXT,
        "corner": CORNER_TEXT,
        "splitter": SPLITTER_TEXT.format(thickness=f"{settings.body.thickness:g}"),
        "angle": ANGLE_TEXT,
    }


def build_declaration(settings: Settings | None = None) -> Declaration:
    """The declaration of the wind tunnel; the same for the adapter and for the scan."""
    texts = knob_texts(settings or Settings.load())
    knobs = (
        NumberKnob("aspect", 0.5, 3.0, texts["aspect"]),
        NumberKnob("corner", 0.0, 1.0, texts["corner"]),
        NumberKnob("splitter", 0.0, 3.0, texts["splitter"]),
        NumberKnob("angle", 0.0, 15.0, texts["angle"]),
    )
    measurements = (
        Measurement("cd", "1", "scalar", (NOT_SETTLED,)),
        Measurement("cl_mean", "1", "scalar", (NOT_SETTLED,)),
        Measurement("cl_amp", "1", "scalar", (NOT_SETTLED,)),
        Measurement("strouhal", "1", "scalar", ("not_shedding", NOT_SETTLED)),
        Measurement("shedding", "1", "scalar", (NOT_SETTLED,)),
    )
    return Declaration(
        knobs=knobs,
        measurements=measurements,
        picture="image/png",
        budget=BUDGET,
        fake=False,
        goal=GOAL,
        measured_by=MEASURED_BY,
    )


class ScanAdapter:
    """The declaration only: no environment check and no `run_trial` (design 1)."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._declaration = build_declaration(settings)

    def declaration(self) -> Declaration:
        return self._declaration


def scan_adapter() -> ScanAdapter:
    return ScanAdapter()
