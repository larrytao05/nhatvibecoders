"""Isolation tests for llm/prompts.py — prompt builder functions."""
import pytest

from llm.constants import DAYS_OF_WEEK, MUSCLE_GROUPS
from llm.prompts import (
    build_complete_workout_messages,
    build_modify_messages,
    build_step1_messages,
    build_step_n_messages,
)
from llm.schemas import DayPlan, WeeklyPlan
from tests.data import SAMPLE_ONBOARDING

_WEEKLY_PLAN = WeeklyPlan(schedule=[
    DayPlan(day="Monday",    muscle_groups=["Upper Chest", "Triceps"], reasoning="Push day — chest/tri volume"),
    *[DayPlan(day=d, muscle_groups=[], reasoning="Rest") for d in DAYS_OF_WEEK[1:]]
])
_MONDAY = _WEEKLY_PLAN.schedule[0]


# ── Step 1 ────────────────────────────────────────────────────────────────────

def test_step1_system_contains_instructor_role():
    system, _ = build_step1_messages(SAMPLE_ONBOARDING)
    assert "fitness instructor" in system.lower()


def test_step1_user_contains_all_seven_days():
    _, user = build_step1_messages(SAMPLE_ONBOARDING)
    for day in DAYS_OF_WEEK:
        assert day in user


def test_step1_user_contains_muscle_group_list():
    _, user = build_step1_messages(SAMPLE_ONBOARDING)
    # Spot-check a few muscle groups from the constant list
    for mg in ["Upper Chest", "Quads", "Lats", "Triceps", "Glutes"]:
        assert mg in user


def test_step1_user_contains_onboarding_data():
    _, user = build_step1_messages({"goals": ["fat loss"], "weight": 200})
    assert "fat loss" in user


def test_step1_user_mentions_rest_days():
    _, user = build_step1_messages(SAMPLE_ONBOARDING)
    assert "rest" in user.lower()


# ── Step N ────────────────────────────────────────────────────────────────────

def test_step_n_user_contains_target_day():
    _, user = build_step_n_messages(SAMPLE_ONBOARDING, _WEEKLY_PLAN, _MONDAY, [])
    assert "Monday" in user


def test_step_n_user_contains_target_muscle_groups():
    _, user = build_step_n_messages(SAMPLE_ONBOARDING, _WEEKLY_PLAN, _MONDAY, [])
    assert "Upper Chest" in user
    assert "Triceps" in user


def test_step_n_user_contains_planning_reasoning():
    _, user = build_step_n_messages(SAMPLE_ONBOARDING, _WEEKLY_PLAN, _MONDAY, [])
    assert "Push day" in user


def test_step_n_user_contains_exercise_list():
    exercises = ["Barbell Bench Press", "Cable Fly", "Tricep Pushdown"]
    _, user = build_step_n_messages(SAMPLE_ONBOARDING, _WEEKLY_PLAN, _MONDAY, exercises)
    for ex in exercises:
        assert ex in user


def test_step_n_user_exercise_list_only_constraint():
    _, user = build_step_n_messages(SAMPLE_ONBOARDING, _WEEKLY_PLAN, _MONDAY, ["Bench Press"])
    assert "only select exercises" in user.lower() or "available_exercises" in user


def test_step_n_system_contains_instructor_role():
    system, _ = build_step_n_messages(SAMPLE_ONBOARDING, _WEEKLY_PLAN, _MONDAY, [])
    assert "fitness instructor" in system.lower()


# ── Modify regimen ────────────────────────────────────────────────────────────

def test_modify_user_contains_feedback():
    _, user = build_modify_messages(SAMPLE_ONBOARDING, {}, "I want more leg volume")
    assert "I want more leg volume" in user


def test_modify_user_contains_current_regimen():
    regimen = {"workouts": {"Monday": [{"name": "Bench Press", "sets": 3}]}}
    _, user = build_modify_messages(SAMPLE_ONBOARDING, regimen, "feedback")
    assert "Bench Press" in user


def test_modify_user_mentions_rfc6902():
    _, user = build_modify_messages(SAMPLE_ONBOARDING, {}, "feedback")
    assert "RFC 6902" in user


def test_modify_user_mentions_patch_ops():
    _, user = build_modify_messages(SAMPLE_ONBOARDING, {}, "feedback")
    assert "replace" in user and "add" in user


# ── Complete workout ──────────────────────────────────────────────────────────

def test_complete_workout_user_contains_today_day():
    tomorrow = {"day": "Tuesday", "exercises": []}
    _, user = build_complete_workout_messages(SAMPLE_ONBOARDING, {}, {}, {}, "Monday", tomorrow)
    assert "Monday" in user


def test_complete_workout_user_contains_tomorrow_workout():
    tomorrow = {"day": "Tuesday", "exercises": [{"name": "Pull-Up", "sets": 4}]}
    _, user = build_complete_workout_messages(SAMPLE_ONBOARDING, {}, {}, {}, "Monday", tomorrow)
    assert "Tuesday" in user
    assert "Pull-Up" in user


def test_complete_workout_user_contains_health_metrics():
    tomorrow = {"day": "Tuesday", "exercises": []}
    health = {"resting_hr": 58, "sleep_hours": 7.5}
    _, user = build_complete_workout_messages(SAMPLE_ONBOARDING, {}, {}, health, "Monday", tomorrow)
    assert "resting_hr" in user or "58" in user


def test_complete_workout_user_empty_modifications_constraint():
    tomorrow = {"day": "Tuesday", "exercises": []}
    _, user = build_complete_workout_messages(SAMPLE_ONBOARDING, {}, {}, {}, "Monday", tomorrow)
    assert "empty" in user.lower()
