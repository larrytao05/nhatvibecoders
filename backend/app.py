import asyncio
import json
import os
from datetime import date as date_type
from typing import Any

import flask
import jsonpatch
from dotenv import load_dotenv

from db import Exercise, Regimen, User, Workout, WorkoutLog, get_session, init_db
from llm import (
    complete_workout as llm_complete_workout,
    create_regimen as llm_create_regimen,
    modify_regimen as llm_modify_regimen,
)


load_dotenv()

app = flask.Flask(__name__)


# ── Serializers ──────────────────────────────────────────────────────────────

def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _serialize_exercise(ex: Exercise) -> dict[str, Any]:
    return {
        "id": ex.id,
        "name": ex.name,
        "sets": ex.sets,
        "reps": ex.reps,
        "weight": ex.weight,
        "rest_time": ex.rest_time,
        "muscles_worked": ex.muscles_worked,
    }


def _serialize_workout(w: Workout) -> dict[str, Any]:
    return {
        "id": w.id,
        "user_id": w.user_id,
        "mood": w.mood,
        "muscles_worked": w.muscles_worked,
        "exercises": [_serialize_exercise(e) for e in (w.exercises or [])],
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
    }


def _serialize_regimen(r: Regimen) -> dict[str, Any]:
    plan = json.loads(r.plan_json) if r.plan_json else None
    return {
        "id": r.id,
        "user_id": r.user_id,
        "name": r.name,
        "goals": r.goals,
        "description": r.description,
        "theme": r.theme,
        "plan": plan,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


def _serialize_log(log: WorkoutLog) -> dict[str, Any]:
    modifications = json.loads(log.modifications_json) if log.modifications_json else []
    return {
        "id": log.id,
        "user_id": log.user_id,
        "regimen_id": log.regimen_id,
        "workout_id": log.workout_id,
        "log_date": log.log_date.isoformat() if log.log_date else None,
        "day": log.day,
        "observations": log.observations,
        "modifications": modifications,
        "created_at": log.created_at.isoformat(),
    }


# ── Users ────────────────────────────────────────────────────────────────────

@app.get("/")
def home():
    return {"ok": True, "service": "nhatvibecoders-backend"}


@app.post("/users")
def create_user():
    payload = flask.request.get_json(silent=True) or {}
    username = payload.get("username")
    current_weight = payload.get("current_weight")

    if not isinstance(username, str) or not username.strip():
        return {"error": "username is required"}, 400

    username = username.strip()

    with get_session() as session:
        if session.query(User).filter_by(username=username).first() is not None:
            return {"error": "username already exists"}, 409

        user = User(username=username, current_weight=current_weight)
        session.add(user)
        session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "current_weight": user.current_weight,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }, 201


@app.get("/users/<username>")
def get_user(username: str):
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "not found"}, 404

        return {
            "id": user.id,
            "username": user.username,
            "current_weight": user.current_weight,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }


@app.patch("/users/<username>")
def update_user(username: str):
    payload = flask.request.get_json(silent=True) or {}

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "not found"}, 404

        if "current_weight" in payload:
            user.current_weight = payload["current_weight"]

        session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "current_weight": user.current_weight,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }


# ── Workouts ─────────────────────────────────────────────────────────────────

@app.post("/users/<username>/workouts")
def log_workout(username: str):
    payload = flask.request.get_json(silent=True) or {}
    mood = payload.get("mood")
    muscles_worked = payload.get("muscles_worked")
    exercises_payload = payload.get("exercises")

    muscles_list = [str(x).strip() for x in _as_list(muscles_worked) if str(x).strip()]
    if not muscles_list:
        return {"error": "muscles_worked is required (string or list)"}, 400

    if not isinstance(exercises_payload, list) or len(exercises_payload) == 0:
        return {"error": "exercises must be a non-empty list"}, 400

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        workout = Workout(user_id=user.id, mood=mood, muscles_worked=", ".join(muscles_list))

        for idx, ex in enumerate(exercises_payload):
            if not isinstance(ex, dict):
                return {"error": f"exercises[{idx}] must be an object"}, 400
            name = ex.get("name")
            sets = ex.get("sets")
            reps = ex.get("reps")
            weight = ex.get("weight")
            rest_time = ex.get("rest_time")
            ex_muscles = ex.get("muscles_worked", muscles_worked)
            ex_muscles_list = [str(x).strip() for x in _as_list(ex_muscles) if str(x).strip()]

            if not isinstance(name, str) or not name.strip():
                return {"error": f"exercises[{idx}].name is required"}, 400
            if not isinstance(sets, int) or sets <= 0:
                return {"error": f"exercises[{idx}].sets must be a positive int"}, 400
            if not isinstance(reps, int) or reps <= 0:
                return {"error": f"exercises[{idx}].reps must be a positive int"}, 400
            if not isinstance(rest_time, int) or rest_time < 0:
                return {"error": f"exercises[{idx}].rest_time must be an int >= 0"}, 400
            if not isinstance(weight, (int, float)):
                return {"error": f"exercises[{idx}].weight must be a number"}, 400
            if not ex_muscles_list:
                return {"error": f"exercises[{idx}].muscles_worked is required"}, 400

            workout.exercises.append(
                Exercise(
                    name=name.strip(),
                    sets=sets,
                    reps=reps,
                    weight=float(weight),
                    rest_time=rest_time,
                    muscles_worked=", ".join(ex_muscles_list),
                )
            )

        session.add(workout)
        session.commit()
        session.refresh(workout)

        return _serialize_workout(workout), 201


@app.get("/users/<username>/workouts")
def get_user_workouts(username: str):
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        workouts = (
            session.query(Workout)
            .filter_by(user_id=user.id)
            .order_by(Workout.created_at.desc())
            .all()
        )
        for w in workouts:
            _ = w.exercises  # eager-load while session is open

        return {"username": username, "workouts": [_serialize_workout(w) for w in workouts]}


@app.post("/users/<username>/workouts/<int:workout_id>/complete")
def complete_workout(username: str, workout_id: int):
    """
    Mark a workout complete and generate an LLM log entry.

    Body:
      regimen_id    int       — which regimen is active
      today_day     str       — e.g. "Monday"
      health_metrics dict     — optional biometric signals (HR, sleep, etc.)

    Returns the created WorkoutLog (observations + modification suggestions).
    Modifications are NOT auto-applied; the client applies them via
    POST /users/<username>/regimens/<id>/apply-patches if accepted.
    """
    payload = flask.request.get_json(silent=True) or {}
    regimen_id = payload.get("regimen_id")
    today_day = payload.get("today_day")
    health_metrics = payload.get("health_metrics") or {}

    if not isinstance(regimen_id, int):
        return {"error": "regimen_id (int) is required"}, 400
    if not isinstance(today_day, str) or not today_day.strip():
        return {"error": "today_day is required (e.g. 'Monday')"}, 400

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        workout = session.query(Workout).filter_by(id=workout_id, user_id=user.id).first()
        if workout is None:
            return {"error": "workout not found"}, 404

        regimen = session.query(Regimen).filter_by(id=regimen_id, user_id=user.id).first()
        if regimen is None:
            return {"error": "regimen not found"}, 404
        if not regimen.plan_json:
            return {"error": "regimen has no plan"}, 400

        _ = workout.exercises  # eager-load

        plan = json.loads(regimen.plan_json)
        onboarding = plan.get("onboarding", {})
        completed_workout_dict = _serialize_workout(workout)

        # Fetch past logs so the LLM has historical context for trend-aware modifications
        past_log_rows = (
            session.query(WorkoutLog)
            .filter_by(user_id=user.id)
            .order_by(WorkoutLog.created_at.desc())
            .limit(10)
            .all()
        )
        past_logs = [_serialize_log(row) for row in past_log_rows]

        try:
            log_entry = asyncio.run(
                llm_complete_workout(
                    onboarding, plan, completed_workout_dict,
                    health_metrics, today_day.strip(), past_logs,
                )
            )
        except Exception as exc:
            return {"error": f"LLM call failed: {exc}"}, 502

        log = WorkoutLog(
            user_id=user.id,
            regimen_id=regimen_id,
            workout_id=workout_id,
            log_date=date_type.today(),
            day=today_day.strip(),
            observations=log_entry["observations"],
            modifications_json=json.dumps(log_entry["modifications"]),
        )
        session.add(log)
        session.commit()

        return _serialize_log(log), 201


# ── Regimens ─────────────────────────────────────────────────────────────────

@app.post("/users/<username>/regimens")
def create_regimen(username: str):
    """
    Generate a new regimen via LLM (HTN expansion) and persist it.

    Body:
      name          str   — display name for the regimen
      description   str   — optional
      theme         str   — optional (e.g. "bro", "powerlifting")
      onboarding    dict  — biometrics, goals, commitment, equipment, existing_plans
    """
    payload = flask.request.get_json(silent=True) or {}
    name = payload.get("name")
    description = payload.get("description")
    theme = payload.get("theme")
    onboarding = payload.get("onboarding")

    if not isinstance(name, str) or not name.strip():
        return {"error": "name is required"}, 400
    if not isinstance(onboarding, dict) or not onboarding:
        return {"error": "onboarding (dict) is required"}, 400

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        try:
            plan = asyncio.run(llm_create_regimen(onboarding))
        except Exception as exc:
            return {"error": f"LLM call failed: {exc}"}, 502

        raw_goals = onboarding.get("goals", "")
        goals_str = ", ".join(raw_goals) if isinstance(raw_goals, list) else str(raw_goals)

        regimen = Regimen(
            user_id=user.id,
            name=name.strip(),
            goals=goals_str,
            description=description if isinstance(description, str) else None,
            theme=theme if isinstance(theme, str) else None,
            plan_json=json.dumps(plan),
        )
        session.add(regimen)
        session.commit()

        return _serialize_regimen(regimen), 201


@app.patch("/users/<username>/regimens/<int:regimen_id>")
def modify_regimen(username: str, regimen_id: int):
    """
    Apply user feedback to a regimen via LLM and persist the updated plan.

    Body:
      feedback  str   — free-text feedback from the user

    Patches are computed by the LLM and applied immediately.
    Returns the updated regimen along with the LLM's reasoning.
    """
    payload = flask.request.get_json(silent=True) or {}
    feedback = payload.get("feedback")

    if not isinstance(feedback, str) or not feedback.strip():
        return {"error": "feedback (str) is required"}, 400

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        regimen = session.query(Regimen).filter_by(id=regimen_id, user_id=user.id).first()
        if regimen is None:
            return {"error": "regimen not found"}, 404
        if not regimen.plan_json:
            return {"error": "regimen has no plan"}, 400

        plan = json.loads(regimen.plan_json)
        onboarding = plan.get("onboarding", {})

        try:
            result = asyncio.run(llm_modify_regimen(onboarding, plan, feedback.strip()))
        except Exception as exc:
            return {"error": f"LLM call failed: {exc}"}, 502

        try:
            updated_plan = jsonpatch.apply_patch(plan, result["patches"])
        except (jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as exc:
            return {"error": f"patch application failed: {exc}", "patches": result["patches"]}, 422

        regimen.plan_json = json.dumps(updated_plan)
        session.commit()

        return {**_serialize_regimen(regimen), "reasoning": result["reasoning"]}


@app.post("/users/<username>/regimens/<int:regimen_id>/apply-patches")
def apply_patches(username: str, regimen_id: int):
    """
    Apply pre-computed RFC 6902 patches to a regimen (e.g. when a user
    accepts the modifications suggested after completing a workout).

    Body:
      patches  list  — RFC 6902 patch operations
    """
    payload = flask.request.get_json(silent=True) or {}
    patches = payload.get("patches")

    if not isinstance(patches, list):
        return {"error": "patches must be a list of RFC 6902 patch operations"}, 400

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        regimen = session.query(Regimen).filter_by(id=regimen_id, user_id=user.id).first()
        if regimen is None:
            return {"error": "regimen not found"}, 404
        if not regimen.plan_json:
            return {"error": "regimen has no plan"}, 400

        plan = json.loads(regimen.plan_json)

        try:
            updated_plan = jsonpatch.apply_patch(plan, patches)
        except (jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as exc:
            return {"error": f"patch application failed: {exc}"}, 422

        regimen.plan_json = json.dumps(updated_plan)
        session.commit()

        return _serialize_regimen(regimen)


# ── Workout logs ─────────────────────────────────────────────────────────────

@app.get("/users/<username>/logs")
def get_user_logs(username: str):
    """Return all workout log entries for a user, newest first."""
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        logs = (
            session.query(WorkoutLog)
            .filter_by(user_id=user.id)
            .order_by(WorkoutLog.created_at.desc())
            .all()
        )

        return {"username": username, "logs": [_serialize_log(log) for log in logs]}


if __name__ == "__main__":
    init_db()
    app.run(debug=bool(int(os.getenv("FLASK_DEBUG", "1"))))
