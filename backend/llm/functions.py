import asyncio

from .client import query
from .constants import DAYS_OF_WEEK, EXERCISE_DB, MUSCLE_GROUPS
from .prompts import (
    build_complete_workout_messages,
    build_modify_messages,
    build_step1_messages,
    build_step_n_messages,
)
from .schemas import DayWorkout, ModifyRegimenOutput, WeeklyPlan, WorkoutLogEntry


# ── Create regimen (HTN expansion) ───────────────────────────────────────────

async def create_regimen(onboarding: dict) -> dict:
    """
    Two-phase HTN expansion:
      1. Generate a high-level weekly plan (muscle groups per day).
      2. In parallel, expand each workout day into a full exercise list.

    Returns a regimen dict ready to be stored in Regimen.plan_json:
      {
        "onboarding": {...},
        "schedule":   [ DayPlan, ... ],          # 7 entries
        "workouts":   { "Monday": [Exercise, ...], ... }  # workout days only
      }
    """
    # Step 1 — weekly overview
    system, user = build_step1_messages(onboarding)
    weekly_plan: WeeklyPlan = await query(system, user, WeeklyPlan)

    # Step N — parallel expansion of non-rest days
    workout_days = [d for d in weekly_plan.schedule if d.muscle_groups]

    async def _expand(day_plan):
        exercises = _filter_exercises(day_plan.muscle_groups)
        sys_msg, usr_msg = build_step_n_messages(onboarding, weekly_plan, day_plan, exercises)
        return await query(sys_msg, usr_msg, DayWorkout)

    day_workouts: list[DayWorkout] = await asyncio.gather(*[_expand(d) for d in workout_days])

    workouts_by_day = {
        dw.day: [e.model_dump() for e in dw.exercises]
        for dw in day_workouts
    }

    return {
        "onboarding": onboarding,
        "schedule": [d.model_dump() for d in weekly_plan.schedule],
        "workouts": workouts_by_day,
    }


def _filter_exercises(muscle_groups: list[str]) -> list[str]:
    """
    Return the subset of EXERCISE_DB relevant to the given muscle groups.
    Currently returns the full list; add a muscle_group → exercise mapping
    here once the exercise DB is annotated.
    """
    return EXERCISE_DB


# ── Modify regimen ───────────────────────────────────────────────────────────

async def modify_regimen(
    onboarding: dict,
    current_regimen: dict,
    feedback: str,
) -> dict:
    """
    Given user feedback, return RFC 6902 JSON Patch operations to update the regimen.

    Returns:
      { "patches": [...], "reasoning": "..." }

    The caller is responsible for validating and applying patches to current_regimen
    before persisting (e.g. using the `jsonpatch` library).
    """
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
) -> dict:
    """
    After a workout is finished, generate a log entry for today.

    Returns a WorkoutLogEntry dict:
      {
        "observations":  "...",        # free-text session summary
        "modifications": [RFC 6902 patches relative to tomorrow's workout object]
      }

    The caller appends this to the user's append-only daily log.
    Patches in modifications are relative to the tomorrow workout object
    (e.g. "/exercises/0/sets"), not to the full regimen — the Flask layer
    must resolve the absolute path before applying them.
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
    )
    result: WorkoutLogEntry = await query(system, user, WorkoutLogEntry)
    return result.model_dump()
