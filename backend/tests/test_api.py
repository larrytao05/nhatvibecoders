"""API endpoint tests — Flask test client + in-memory SQLite + mocked LLM."""
import pytest
from unittest.mock import AsyncMock, patch

from tests.data import SAMPLE_EXERCISES_PAYLOAD, SAMPLE_ONBOARDING, SAMPLE_PLAN


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_user(client, username, weight=175.0):
    return client.post("/users", json={"username": username, "current_weight": weight})


def _create_regimen(client, username, plan=None):
    plan = plan or SAMPLE_PLAN
    with patch("app.llm_create_regimen", new=AsyncMock(return_value=plan)):
        return client.post(f"/users/{username}/regimens", json={
            "name": "Test Regimen",
            "onboarding": SAMPLE_ONBOARDING,
        })


def _log_workout(client, username):
    return client.post(f"/users/{username}/workouts", json={
        "mood": "good",
        "muscles_worked": ["chest"],
        "exercises": SAMPLE_EXERCISES_PAYLOAD,
    })


# ── Health check ──────────────────────────────────────────────────────────────

def test_health_check(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


# ── Users ─────────────────────────────────────────────────────────────────────

def test_create_user_success(client):
    r = _create_user(client, "alice")
    assert r.status_code == 201
    data = r.get_json()
    assert data["username"] == "alice"
    assert data["current_weight"] == 175.0
    assert "id" in data
    assert "created_at" in data


def test_create_user_missing_username(client):
    r = client.post("/users", json={"current_weight": 150})
    assert r.status_code == 400


def test_create_user_empty_username(client):
    r = client.post("/users", json={"username": "   "})
    assert r.status_code == 400


def test_create_user_duplicate(client):
    _create_user(client, "bob")
    r = _create_user(client, "bob")
    assert r.status_code == 409


def test_get_user(client):
    _create_user(client, "carol")
    r = client.get("/users/carol")
    assert r.status_code == 200
    assert r.get_json()["username"] == "carol"


def test_get_user_not_found(client):
    r = client.get("/users/nobody")
    assert r.status_code == 404


def test_update_user_weight(client):
    _create_user(client, "dave", weight=180.0)
    r = client.patch("/users/dave", json={"current_weight": 170.0})
    assert r.status_code == 200
    assert r.get_json()["current_weight"] == 170.0


def test_update_user_not_found(client):
    r = client.patch("/users/ghost", json={"current_weight": 170.0})
    assert r.status_code == 404


# ── Workouts ──────────────────────────────────────────────────────────────────

def test_log_workout_success(client):
    _create_user(client, "eve")
    r = _log_workout(client, "eve")
    assert r.status_code == 201
    data = r.get_json()
    assert data["mood"] == "good"
    assert len(data["exercises"]) == 1
    assert data["exercises"][0]["name"] == "Barbell Bench Press"
    assert data["exercises"][0]["sets"] == 4


def test_log_workout_aggregates_workout_muscles_from_exercises(client):
    _create_user(client, "eve_plus")
    r = client.post("/users/eve_plus/workouts", json={
        "mood": "good",
        "muscles_worked": ["Upper Chest"],
        "exercises": [
            {
                "name": "Barbell Bench Press",
                "sets": 4,
                "reps": 8,
                "weight": 135,
                "rest_time": 120,
                "muscles_worked": ["Upper Chest", "Triceps"],
            },
            {
                "name": "Face Pull",
                "sets": 3,
                "reps": 15,
                "weight": 40,
                "rest_time": 45,
                "muscles_worked": ["Rear Delt", "Traps"],
            },
        ],
    })
    assert r.status_code == 201
    assert r.get_json()["muscles_worked"] == "Upper Chest, Triceps, Rear Delt, Traps"


def test_log_workout_missing_muscles(client):
    _create_user(client, "frank")
    r = client.post("/users/frank/workouts", json={"exercises": SAMPLE_EXERCISES_PAYLOAD})
    assert r.status_code == 201
    assert r.get_json()["muscles_worked"] == "chest, triceps"


def test_log_workout_empty_exercises(client):
    _create_user(client, "grace")
    r = client.post("/users/grace/workouts", json={
        "muscles_worked": ["chest"],
        "exercises": [],
    })
    assert r.status_code == 400


def test_log_workout_invalid_exercise_fields(client):
    _create_user(client, "henry")
    r = client.post("/users/henry/workouts", json={
        "muscles_worked": ["chest"],
        "exercises": [{"name": "Bench Press", "sets": -1, "reps": 8, "weight": 135, "rest_time": 90, "muscles_worked": ["chest"]}],
    })
    assert r.status_code == 400


def test_log_workout_user_not_found(client):
    r = _log_workout(client, "nobody")
    assert r.status_code == 404


def test_get_workouts(client):
    _create_user(client, "iris")
    _log_workout(client, "iris")
    _log_workout(client, "iris")
    r = client.get("/users/iris/workouts")
    assert r.status_code == 200
    assert len(r.get_json()["workouts"]) == 2


def test_get_workouts_empty(client):
    _create_user(client, "jack")
    r = client.get("/users/jack/workouts")
    assert r.status_code == 200
    assert r.get_json()["workouts"] == []


def test_get_workouts_user_not_found(client):
    r = client.get("/users/nobody/workouts")
    assert r.status_code == 404


# ── Regimens ──────────────────────────────────────────────────────────────────

def test_create_regimen_success(client):
    _create_user(client, "kate")
    r = _create_regimen(client, "kate")
    assert r.status_code == 201
    data = r.get_json()
    assert data["name"] == "Test Regimen"
    assert data["goals"] == "muscle gain, strength"
    assert data["plan"]["onboarding"] == SAMPLE_ONBOARDING
    assert len(data["plan"]["schedule"]) == 7
    assert "Monday" in data["plan"]["workouts"]
    assert data["plan"]["workouts"]["Monday"][0]["muscles_worked"] == ["Upper Chest", "Front Delt", "Triceps"]


def test_create_regimen_missing_name(client):
    _create_user(client, "leo")
    r = client.post("/users/leo/regimens", json={"onboarding": SAMPLE_ONBOARDING})
    assert r.status_code == 400


def test_create_regimen_missing_onboarding(client):
    _create_user(client, "mia")
    r = client.post("/users/mia/regimens", json={"name": "My Plan"})
    assert r.status_code == 400


def test_create_regimen_user_not_found(client):
    r = _create_regimen(client, "nobody")
    assert r.status_code == 404


def test_create_regimen_llm_failure_returns_502(client):
    _create_user(client, "ned")
    with patch("app.llm_create_regimen", new=AsyncMock(side_effect=RuntimeError("API down"))):
        r = client.post("/users/ned/regimens", json={"name": "Plan", "onboarding": SAMPLE_ONBOARDING})
    assert r.status_code == 502


def test_create_regimen_stores_description_and_theme(client):
    _create_user(client, "olivia")
    with patch("app.llm_create_regimen", new=AsyncMock(return_value=SAMPLE_PLAN)):
        r = client.post("/users/olivia/regimens", json={
            "name": "PPL",
            "description": "Classic push/pull/legs",
            "theme": "science-based",
            "onboarding": SAMPLE_ONBOARDING,
        })
    assert r.status_code == 201
    data = r.get_json()
    assert data["description"] == "Classic push/pull/legs"
    assert data["theme"] == "science-based"


def test_modify_regimen_applies_patches(client):
    _create_user(client, "pete")
    regimen_id = _create_regimen(client, "pete").get_json()["id"]

    patches = [{"op": "replace", "path": "/workouts/Monday/0/sets", "value": 6}]
    with patch("app.llm_modify_regimen", new=AsyncMock(return_value={
        "patches": patches, "reasoning": "More volume",
    })):
        r = client.patch(f"/users/pete/regimens/{regimen_id}", json={"feedback": "more sets"})

    assert r.status_code == 200
    data = r.get_json()
    assert data["plan"]["workouts"]["Monday"][0]["sets"] == 6
    assert data["reasoning"] == "More volume"


def test_modify_regimen_missing_feedback(client):
    _create_user(client, "quinn")
    regimen_id = _create_regimen(client, "quinn").get_json()["id"]
    r = client.patch(f"/users/quinn/regimens/{regimen_id}", json={})
    assert r.status_code == 400


def test_modify_regimen_not_found(client):
    _create_user(client, "rosa")
    with patch("app.llm_modify_regimen", new=AsyncMock(return_value={"patches": [], "reasoning": ""})):
        r = client.patch("/users/rosa/regimens/9999", json={"feedback": "test"})
    assert r.status_code == 404


def test_modify_regimen_invalid_patch_path_returns_422(client):
    _create_user(client, "sam")
    regimen_id = _create_regimen(client, "sam").get_json()["id"]

    bad_patches = [{"op": "replace", "path": "/nonexistent/deeply/nested/key", "value": 5}]
    with patch("app.llm_modify_regimen", new=AsyncMock(return_value={
        "patches": bad_patches, "reasoning": "bad",
    })):
        r = client.patch(f"/users/sam/regimens/{regimen_id}", json={"feedback": "test"})
    assert r.status_code == 422


def test_apply_patches_success(client):
    _create_user(client, "tina")
    regimen_id = _create_regimen(client, "tina").get_json()["id"]

    patches = [{"op": "replace", "path": "/workouts/Monday/0/reps", "value": 12}]
    r = client.post(f"/users/tina/regimens/{regimen_id}/apply-patches", json={"patches": patches})
    assert r.status_code == 200
    assert r.get_json()["plan"]["workouts"]["Monday"][0]["reps"] == 12


def test_apply_patches_not_a_list(client):
    _create_user(client, "uma")
    regimen_id = _create_regimen(client, "uma").get_json()["id"]
    r = client.post(f"/users/uma/regimens/{regimen_id}/apply-patches", json={"patches": "bad"})
    assert r.status_code == 400


def test_apply_patches_invalid_path_returns_422(client):
    _create_user(client, "vic")
    regimen_id = _create_regimen(client, "vic").get_json()["id"]
    bad = [{"op": "replace", "path": "/does/not/exist", "value": 1}]
    r = client.post(f"/users/vic/regimens/{regimen_id}/apply-patches", json={"patches": bad})
    assert r.status_code == 422


# ── Complete workout / logs ───────────────────────────────────────────────────

def test_complete_workout_creates_log(client):
    _create_user(client, "wendy")
    regimen_id = _create_regimen(client, "wendy").get_json()["id"]
    workout_id = _log_workout(client, "wendy").get_json()["id"]

    mock_entry = {
        "observations": "Strong session. All sets completed.",
        "modifications": [{"op": "replace", "path": "/exercises/0/sets", "value": 3}],
    }
    with patch("app.llm_complete_workout", new=AsyncMock(return_value=mock_entry)):
        r = client.post(f"/users/wendy/workouts/{workout_id}/complete", json={
            "regimen_id": regimen_id,
            "today_day": "Monday",
            "health_metrics": {"resting_hr": 58},
        })

    assert r.status_code == 201
    data = r.get_json()
    assert data["observations"] == "Strong session. All sets completed."
    assert data["modifications"][0]["op"] == "replace"
    assert data["regimen_id"] == regimen_id
    assert data["workout_id"] == workout_id
    assert data["day"] == "Monday"


def test_complete_workout_missing_regimen_id(client):
    _create_user(client, "xena")
    workout_id = _log_workout(client, "xena").get_json()["id"]
    r = client.post(f"/users/xena/workouts/{workout_id}/complete", json={"today_day": "Monday"})
    assert r.status_code == 400


def test_complete_workout_missing_today_day(client):
    _create_user(client, "yara")
    regimen_id = _create_regimen(client, "yara").get_json()["id"]
    workout_id = _log_workout(client, "yara").get_json()["id"]
    r = client.post(f"/users/yara/workouts/{workout_id}/complete", json={"regimen_id": regimen_id})
    assert r.status_code == 400


def test_complete_workout_llm_failure_returns_502(client):
    _create_user(client, "zara")
    regimen_id = _create_regimen(client, "zara").get_json()["id"]
    workout_id = _log_workout(client, "zara").get_json()["id"]

    with patch("app.llm_complete_workout", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
        r = client.post(f"/users/zara/workouts/{workout_id}/complete", json={
            "regimen_id": regimen_id,
            "today_day": "Tuesday",
        })
    assert r.status_code == 502


def test_get_logs_returns_entries(client):
    _create_user(client, "arya")
    regimen_id = _create_regimen(client, "arya").get_json()["id"]
    workout_id = _log_workout(client, "arya").get_json()["id"]

    mock_entry = {"observations": "Good workout", "modifications": []}
    with patch("app.llm_complete_workout", new=AsyncMock(return_value=mock_entry)):
        client.post(f"/users/arya/workouts/{workout_id}/complete", json={
            "regimen_id": regimen_id,
            "today_day": "Wednesday",
        })

    r = client.get("/users/arya/logs")
    assert r.status_code == 200
    logs = r.get_json()["logs"]
    assert len(logs) == 1
    assert logs[0]["observations"] == "Good workout"
    assert logs[0]["day"] == "Wednesday"


def test_get_logs_empty(client):
    _create_user(client, "bran")
    r = client.get("/users/bran/logs")
    assert r.status_code == 200
    assert r.get_json()["logs"] == []


def test_get_logs_user_not_found(client):
    r = client.get("/users/nobody/logs")
    assert r.status_code == 404
