"""Full pipeline integration tests.

LLM calls are mocked (no real API calls). Everything else — Flask routing,
SQLAlchemy persistence, JSON patch application — runs for real against the
in-memory SQLite database.
"""
import pytest
from unittest.mock import AsyncMock, patch

from tests.data import SAMPLE_ONBOARDING, SAMPLE_PLAN


# ── Pipeline helpers ──────────────────────────────────────────────────────────

def _create_user(client, username):
    r = client.post("/users", json={"username": username, "current_weight": 175.0})
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _create_regimen(client, username, plan=None):
    plan = plan or SAMPLE_PLAN
    with patch("app.llm_create_regimen", new=AsyncMock(return_value=plan)):
        r = client.post(f"/users/{username}/regimens", json={
            "name": "My Plan",
            "theme": "science-based",
            "onboarding": SAMPLE_ONBOARDING,
        })
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _log_workout(client, username):
    r = client.post(f"/users/{username}/workouts", json={
        "mood": "energetic",
        "muscles_worked": ["chest", "triceps"],
        "exercises": [
            {"name": "Barbell Bench Press", "sets": 4, "reps": 8, "weight": 135.0,
             "rest_time": 120, "muscles_worked": ["chest"]},
        ],
    })
    assert r.status_code == 201, r.get_json()
    return r.get_json()


def _complete_workout(client, username, workout_id, regimen_id, today_day, mock_entry):
    with patch("app.llm_complete_workout", new=AsyncMock(return_value=mock_entry)):
        r = client.post(f"/users/{username}/workouts/{workout_id}/complete", json={
            "regimen_id": regimen_id,
            "today_day": today_day,
        })
    assert r.status_code == 201, r.get_json()
    return r.get_json()


# ── Pipeline tests ────────────────────────────────────────────────────────────

def test_regimen_creation_pipeline(client):
    """Create user → generate regimen → verify full plan persisted correctly."""
    _create_user(client, "p_create")
    regimen = _create_regimen(client, "p_create")

    assert regimen["name"] == "My Plan"
    assert regimen["theme"] == "science-based"
    assert regimen["goals"] == "muscle gain, strength"

    plan = regimen["plan"]
    assert plan["onboarding"] == SAMPLE_ONBOARDING
    assert len(plan["schedule"]) == 7
    assert "Monday" in plan["workouts"]
    assert plan["workouts"]["Monday"][0]["name"] == "Barbell Bench Press"


def test_regimen_modify_pipeline(client):
    """Create regimen → apply feedback → verify patch reflected in stored plan."""
    _create_user(client, "p_modify")
    regimen = _create_regimen(client, "p_modify")
    regimen_id = regimen["id"]

    baseline_sets = regimen["plan"]["workouts"]["Monday"][0]["sets"]
    assert baseline_sets == 4

    patches = [{"op": "replace", "path": "/workouts/Monday/0/sets", "value": 6}]
    with patch("app.llm_modify_regimen", new=AsyncMock(return_value={
        "patches": patches,
        "reasoning": "Increasing volume for progressive overload",
    })):
        r = client.patch(f"/users/p_modify/regimens/{regimen_id}",
                         json={"feedback": "I want more sets on Monday bench"})

    assert r.status_code == 200
    data = r.get_json()
    assert data["plan"]["workouts"]["Monday"][0]["sets"] == 6
    assert "progressive overload" in data["reasoning"]


def test_workout_completion_creates_log(client):
    """Log workout → complete it → verify log entry persisted with correct fields."""
    _create_user(client, "p_complete")
    regimen = _create_regimen(client, "p_complete")
    workout = _log_workout(client, "p_complete")

    mock_entry = {
        "observations": "Strong session. Hit all target sets.",
        "modifications": [{"op": "replace", "path": "/exercises/0/weight", "value": 95.0}],
    }
    log = _complete_workout(client, "p_complete", workout["id"], regimen["id"], "Monday", mock_entry)

    assert log["observations"] == "Strong session. Hit all target sets."
    assert log["modifications"][0]["value"] == 95.0
    assert log["day"] == "Monday"
    assert log["regimen_id"] == regimen["id"]
    assert log["workout_id"] == workout["id"]


def test_accept_suggestions_pipeline(client):
    """Complete workout → client accepts modifications → verify regimen updated."""
    _create_user(client, "p_accept")
    regimen = _create_regimen(client, "p_accept")
    regimen_id = regimen["id"]
    workout = _log_workout(client, "p_accept")

    # LLM suggests reducing Tuesday's Pull-Up weight (relative path)
    mock_entry = {
        "observations": "Feeling tired, reduce Tuesday weight.",
        "modifications": [{"op": "replace", "path": "/exercises/0/weight", "value": 0.0}],
    }
    _complete_workout(client, "p_accept", workout["id"], regimen_id, "Monday", mock_entry)

    # Client translates relative path → absolute regimen path and applies
    abs_patches = [{"op": "replace", "path": "/workouts/Tuesday/0/weight", "value": 0.0}]
    r = client.post(f"/users/p_accept/regimens/{regimen_id}/apply-patches",
                    json={"patches": abs_patches})
    assert r.status_code == 200
    assert r.get_json()["plan"]["workouts"]["Tuesday"][0]["weight"] == 0.0


def test_multiple_logs_accumulate(client):
    """Two separate workout completions produce two log entries."""
    _create_user(client, "p_multi")
    regimen = _create_regimen(client, "p_multi")
    regimen_id = regimen["id"]

    for day, obs in [("Monday", "Great push day"), ("Tuesday", "Solid pull day")]:
        workout = _log_workout(client, "p_multi")
        _complete_workout(client, "p_multi", workout["id"], regimen_id, day,
                          {"observations": obs, "modifications": []})

    r = client.get("/users/p_multi/logs")
    assert r.status_code == 200
    logs = r.get_json()["logs"]
    assert len(logs) == 2
    observations = {log["observations"] for log in logs}
    assert "Great push day" in observations
    assert "Solid pull day" in observations


def test_full_end_to_end_pipeline(client):
    """
    Complete multi-step flow:
    create user → create regimen → log workout → complete workout →
    accept modifications → apply feedback → verify logs.
    """
    _create_user(client, "p_full")
    regimen = _create_regimen(client, "p_full")
    regimen_id = regimen["id"]

    # 1. Log and complete a workout
    workout = _log_workout(client, "p_full")
    mock_entry = {
        "observations": "Good energy. All sets hit.",
        "modifications": [{"op": "replace", "path": "/exercises/0/sets", "value": 3}],
    }
    log = _complete_workout(client, "p_full", workout["id"], regimen_id, "Monday", mock_entry)
    assert log["observations"] == "Good energy. All sets hit."

    # 2. Accept modifications (translate to absolute path for Tuesday)
    abs_patches = [{"op": "replace", "path": "/workouts/Tuesday/0/sets", "value": 3}]
    apply_r = client.post(f"/users/p_full/regimens/{regimen_id}/apply-patches",
                          json={"patches": abs_patches})
    assert apply_r.status_code == 200
    assert apply_r.get_json()["plan"]["workouts"]["Tuesday"][0]["sets"] == 3

    # 3. User also sends explicit feedback
    feedback_patches = [{"op": "replace", "path": "/workouts/Thursday/0/reps", "value": 10}]
    with patch("app.llm_modify_regimen", new=AsyncMock(return_value={
        "patches": feedback_patches,
        "reasoning": "Higher reps for hypertrophy focus",
    })):
        modify_r = client.patch(f"/users/p_full/regimens/{regimen_id}",
                                json={"feedback": "more reps on leg day"})
    assert modify_r.status_code == 200
    assert modify_r.get_json()["plan"]["workouts"]["Thursday"][0]["reps"] == 10

    # 4. Verify the log exists
    logs_r = client.get("/users/p_full/logs")
    logs = logs_r.get_json()["logs"]
    assert len(logs) == 1
    assert logs[0]["observations"] == "Good energy. All sets hit."

    # 5. Verify final regimen state has all patches applied
    final_plan = modify_r.get_json()["plan"]
    assert final_plan["workouts"]["Tuesday"][0]["sets"] == 3
    assert final_plan["workouts"]["Thursday"][0]["reps"] == 10
