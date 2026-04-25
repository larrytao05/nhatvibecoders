"""Isolation tests for llm/functions.py.

query() is mocked throughout — these tests verify orchestration logic:
HTN expansion, day filtering, tomorrow computation, output shape.
"""
import pytest
from unittest.mock import AsyncMock, patch

from llm.constants import DAYS_OF_WEEK
from llm.schemas import (
    DayPlan, DayWorkout, ExerciseSpec, JsonPatch,
    ModifyRegimenOutput, WeeklyPlan, WorkoutLogEntry,
)
from tests.data import SAMPLE_ONBOARDING, SAMPLE_PLAN

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_weekly_plan(workout_days: list[str]) -> WeeklyPlan:
    schedule = []
    for day in DAYS_OF_WEEK:
        if day in workout_days:
            schedule.append(DayPlan(day=day, muscle_groups=["Upper Chest"], reasoning="Push"))
        else:
            schedule.append(DayPlan(day=day, muscle_groups=[], reasoning="Rest"))
    return WeeklyPlan(schedule=schedule)


def _make_day_workout(day: str) -> DayWorkout:
    return DayWorkout(
        day=day,
        exercises=[ExerciseSpec(name="Barbell Bench Press", sets=4, reps=8, weight=135.0, rest_time=120)],
    )


# ── create_regimen ────────────────────────────────────────────────────────────

async def test_create_regimen_expands_only_workout_days():
    workout_days = ["Monday", "Wednesday", "Friday"]
    weekly = _make_weekly_plan(workout_days)
    day_workouts = [_make_day_workout(d) for d in workout_days]

    with patch("llm.functions.query", new=AsyncMock(side_effect=[weekly, *day_workouts])):
        result = await _import_create()

    assert set(result["workouts"].keys()) == set(workout_days)
    for rest_day in ["Tuesday", "Thursday", "Saturday", "Sunday"]:
        assert rest_day not in result["workouts"]


async def test_create_regimen_all_rest_days():
    all_rest = _make_weekly_plan([])

    with patch("llm.functions.query", new=AsyncMock(return_value=all_rest)):
        result = await _import_create()

    assert result["workouts"] == {}


async def test_create_regimen_output_has_required_keys():
    weekly = _make_weekly_plan(["Monday"])

    with patch("llm.functions.query", new=AsyncMock(side_effect=[weekly, _make_day_workout("Monday")])):
        result = await _import_create()

    assert "onboarding" in result
    assert "schedule" in result
    assert "workouts" in result


async def test_create_regimen_enriches_exercises_with_muscles_worked():
    weekly = _make_weekly_plan(["Monday"])

    with patch("llm.functions.query", new=AsyncMock(side_effect=[weekly, _make_day_workout("Monday")])):
        result = await _import_create()

    assert result["workouts"]["Monday"][0]["muscles_worked"] == ["Upper Chest", "Front Delt", "Triceps"]


async def test_create_regimen_injects_onboarding_into_output():
    all_rest = _make_weekly_plan([])

    with patch("llm.functions.query", new=AsyncMock(return_value=all_rest)):
        result = await _import_create()

    assert result["onboarding"] == SAMPLE_ONBOARDING


async def test_create_regimen_schedule_has_seven_entries():
    all_rest = _make_weekly_plan([])

    with patch("llm.functions.query", new=AsyncMock(return_value=all_rest)):
        result = await _import_create()

    assert len(result["schedule"]) == 7


async def test_create_regimen_step1_called_once():
    all_rest = _make_weekly_plan([])

    with patch("llm.functions.query", new=AsyncMock(return_value=all_rest)) as mock_q:
        await _import_create()

    # One call for step 1, zero for workout days (all rest)
    assert mock_q.call_count == 1


async def test_create_regimen_parallel_expansion_call_count():
    """Step 1 + one call per workout day."""
    workout_days = ["Monday", "Tuesday", "Thursday"]
    weekly = _make_weekly_plan(workout_days)
    day_workouts = [_make_day_workout(d) for d in workout_days]

    with patch("llm.functions.query", new=AsyncMock(side_effect=[weekly, *day_workouts])) as mock_q:
        await _import_create()

    assert mock_q.call_count == 1 + len(workout_days)


# ── modify_regimen ────────────────────────────────────────────────────────────

async def test_modify_regimen_returns_patches_and_reasoning():
    from llm.functions import modify_regimen

    mock_output = ModifyRegimenOutput(
        patches=[JsonPatch(op="replace", path="/workouts/Monday/0/sets", value=5)],
        reasoning="User wants more volume",
    )
    with patch("llm.functions.query", new=AsyncMock(return_value=mock_output)):
        result = await modify_regimen(SAMPLE_ONBOARDING, SAMPLE_PLAN, "more sets please")

    assert result["patches"][0]["op"] == "replace"
    assert result["patches"][0]["path"] == "/workouts/Monday/0/sets"
    assert result["patches"][0]["value"] == 5
    assert result["reasoning"] == "User wants more volume"


async def test_modify_regimen_empty_patches():
    from llm.functions import modify_regimen

    mock_output = ModifyRegimenOutput(patches=[], reasoning="No changes needed")
    with patch("llm.functions.query", new=AsyncMock(return_value=mock_output)):
        result = await modify_regimen(SAMPLE_ONBOARDING, SAMPLE_PLAN, "looks good")

    assert result["patches"] == []


# ── complete_workout ──────────────────────────────────────────────────────────

async def test_complete_workout_passes_correct_tomorrow():
    """Monday's tomorrow is Tuesday — verify it appears in the prompt."""
    from llm.functions import complete_workout

    mock_output = WorkoutLogEntry(observations="Good session", modifications=[])
    with patch("llm.functions.query", new=AsyncMock(return_value=mock_output)) as mock_q:
        await complete_workout(SAMPLE_ONBOARDING, SAMPLE_PLAN, {}, {}, "Monday")

    user_prompt = mock_q.call_args.args[1]
    assert "Tuesday" in user_prompt


async def test_complete_workout_sunday_wraps_to_monday():
    from llm.functions import complete_workout

    mock_output = WorkoutLogEntry(observations="Rest day", modifications=[])
    with patch("llm.functions.query", new=AsyncMock(return_value=mock_output)) as mock_q:
        await complete_workout(SAMPLE_ONBOARDING, SAMPLE_PLAN, {}, {}, "Sunday")

    user_prompt = mock_q.call_args.args[1]
    assert "Monday" in user_prompt


async def test_complete_workout_saturday_wraps_to_sunday():
    from llm.functions import complete_workout

    mock_output = WorkoutLogEntry(observations="Done", modifications=[])
    with patch("llm.functions.query", new=AsyncMock(return_value=mock_output)) as mock_q:
        await complete_workout(SAMPLE_ONBOARDING, SAMPLE_PLAN, {}, {}, "Saturday")

    user_prompt = mock_q.call_args.args[1]
    assert "Sunday" in user_prompt


async def test_complete_workout_returns_observations_and_modifications():
    from llm.functions import complete_workout

    mods = [JsonPatch(op="replace", path="/exercises/0/sets", value=3)]
    mock_output = WorkoutLogEntry(observations="Feeling fatigued today", modifications=mods)
    with patch("llm.functions.query", new=AsyncMock(return_value=mock_output)):
        result = await complete_workout(SAMPLE_ONBOARDING, SAMPLE_PLAN, {}, {}, "Monday")

    assert result["observations"] == "Feeling fatigued today"
    assert result["modifications"][0]["op"] == "replace"
    assert result["modifications"][0]["value"] == 3


async def test_complete_workout_no_modifications():
    from llm.functions import complete_workout

    mock_output = WorkoutLogEntry(observations="Great session", modifications=[])
    with patch("llm.functions.query", new=AsyncMock(return_value=mock_output)):
        result = await complete_workout(SAMPLE_ONBOARDING, SAMPLE_PLAN, {}, {}, "Friday")

    assert result["modifications"] == []


# ── Helper ────────────────────────────────────────────────────────────────────

async def _import_create():
    from llm.functions import create_regimen
    return await create_regimen(SAMPLE_ONBOARDING)
