from .client import query
from .constants import DAYS_OF_WEEK, filter_exercises_by_muscles, get_exercise_muscles
from .prompts import (
    build_complete_workout_messages,
    build_modify_messages,
    build_step1_messages,
    build_step_n_messages,
)
from .schemas import DayPlan, DayWorkout, ModifyRegimenOutput, WeeklyPlan, WorkoutLogEntry


# ── Primitive building blocks (also exported for streaming use) ──────────────

async def generate_weekly_plan(onboarding: dict) -> WeeklyPlan:
    """Step 1 of HTN: generate the high-level weekly skeleton."""
    system, user = build_step1_messages(onboarding)
    return await query(system, user, WeeklyPlan)


async def expand_day(onboarding: dict, weekly_plan: WeeklyPlan, day_plan: DayPlan) -> DayWorkout:
    """Step N of HTN: expand one workout day into a full exercise list."""
    exercises = _filter_exercises(day_plan.muscle_groups)
    sys_msg, usr_msg = build_step_n_messages(onboarding, weekly_plan, day_plan, exercises)
    return await query(sys_msg, usr_msg, DayWorkout)


# ── Create regimen (HTN expansion) ───────────────────────────────────────────

async def create_regimen(onboarding: dict) -> dict:
    """
    Full HTN expansion used by the Flask endpoint.
    Calls generate_weekly_plan then expand_day sequentially for each workout day.

    Returns:
      { "onboarding": {...}, "schedule": [...], "workouts": { "Monday": [...], ... } }
    """
    print("  [LLM call 1] Generating weekly schedule...")
    weekly_plan = await generate_weekly_plan(onboarding)
    print("  [LLM call 1] Done.")

    workout_days = [d for d in weekly_plan.schedule if d.muscle_groups]
    rest_days = [d.day for d in weekly_plan.schedule if not d.muscle_groups]
    print(f"  Workout days: {[d.day for d in workout_days]}")
    print(f"  Rest days:    {rest_days}")

    workouts_by_day = {}
    for i, day_plan in enumerate(workout_days, start=2):
        print(f"  [LLM call {i}] Expanding {day_plan.day} ({', '.join(day_plan.muscle_groups)})...")
        dw = _hydrate_day_workout(await expand_day(onboarding, weekly_plan, day_plan))
        workouts_by_day[dw.day] = [e.model_dump() for e in dw.exercises]
        print(f"  [LLM call {i}] Done — {len(dw.exercises)} exercises.")

    return {
        "onboarding": onboarding,
        "schedule": [d.model_dump() for d in weekly_plan.schedule],
        "workouts": workouts_by_day,
    }


def _filter_exercises(muscle_groups: list[str]) -> list[str]:
    """Return the exercises tagged for the requested muscle groups."""
    return filter_exercises_by_muscles(muscle_groups)


def _hydrate_day_workout(day_workout: DayWorkout) -> DayWorkout:
    """Backfill muscle coverage from constants so plans stay exercise-driven."""
    exercises = [
        ex.model_copy(update={"muscles_worked": get_exercise_muscles(ex.name, ex.muscles_worked)})
        for ex in day_workout.exercises
    ]
    return day_workout.model_copy(update={"exercises": exercises})


# ── Modify regimen ───────────────────────────────────────────────────────────

async def modify_regimen(
    onboarding: dict,
    current_regimen: dict,
    feedback: str,
) -> dict:
    system, user = build_modify_messages(onboarding, current_regimen, feedback)
    result: ModifyRegimenOutput = await query(system, user, ModifyRegimenOutput)
    return result.model_dump()


# ── Complete workout ─────────────────────────────────────────────────────────

async def complete_workout(
    onboarding: dict,
    current_regimen: dict,
    completed_workout: dict,
    health_metrics: dict,
    today_day: str,
    past_logs: list[dict] = None,
) -> dict:
    """
    Generate a log entry after a workout is finished.

    past_logs: previous WorkoutLog entries for this user (newest first).
               Injected as context so the LLM can identify trends and inform
               tomorrow's modification with historical performance data.

    Returns:
      { "observations": "...", "modifications": [RFC 6902 patches vs tomorrow workout] }
    """
    tomorrow_day = DAYS_OF_WEEK[(DAYS_OF_WEEK.index(today_day) + 1) % 7]
    tomorrow_workout = {
        "day": tomorrow_day,
        "exercises": current_regimen.get("workouts", {}).get(tomorrow_day, []),
    }

    system, user = build_complete_workout_messages(
        onboarding,
        current_regimen,
        completed_workout,
        health_metrics,
        today_day,
        tomorrow_workout,
        past_logs=past_logs or [],
    )
    result: WorkoutLogEntry = await query(system, user, WorkoutLogEntry)
    return result.model_dump()
