from typing import Any, Literal, Optional
from pydantic import BaseModel


# ── Step 1: high-level weekly plan ──────────────────────────────────────────

class DayPlan(BaseModel):
    day: str                   # One of DAYS_OF_WEEK
    muscle_groups: list[str]   # Subset of MUSCLE_GROUPS; empty list = rest day
    reasoning: str             # Free-text rationale propagated to step N


class WeeklyPlan(BaseModel):
    schedule: list[DayPlan]    # Exactly 7 entries, Monday → Sunday


# ── Step N: per-day exercise expansion ──────────────────────────────────────

class ExerciseSpec(BaseModel):
    name: str         # Must come from EXERCISE_DB
    sets: int
    reps: int
    weight: float     # lbs
    rest_time: int    # seconds
    notes: str = ""


class DayWorkout(BaseModel):
    day: str
    exercises: list[ExerciseSpec]


# ── Modify regimen ───────────────────────────────────────────────────────────

class JsonPatch(BaseModel):
    """RFC 6902 JSON Patch operation."""
    op: Literal["add", "remove", "replace"]
    path: str              # JSON Pointer, e.g. "/workouts/Monday/0/sets"
    value: Optional[Any] = None   # Required for add/replace; omitted for remove


class ModifyRegimenOutput(BaseModel):
    patches: list[JsonPatch]
    reasoning: str         # Explain what changed and why


# ── Complete workout log entry ───────────────────────────────────────────────

class WorkoutLogEntry(BaseModel):
    observations: str            # Free-text summary of the session
    modifications: list[JsonPatch]  # RFC 6902 patches relative to tomorrow's workout object
