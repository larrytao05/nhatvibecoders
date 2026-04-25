import os
import json
from typing import Any

import flask
from dotenv import load_dotenv

from db import Exercise, Regimen, User, Workout, get_session, init_db


load_dotenv()

app = flask.Flask(__name__)

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
        existing = session.query(User).filter_by(username=username).first()
        if existing is not None:
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
    current_weight = payload.get("current_weight")

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "not found"}, 404

        if "current_weight" in payload:
            user.current_weight = current_weight

        session.commit()

        return {
            "id": user.id,
            "username": user.username,
            "current_weight": user.current_weight,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

@app.post("/users/<username>/workouts")
def log_workout(username: str):
    payload = flask.request.get_json(silent=True) or {}
    mood = payload.get("mood")
    muscles_worked = payload.get("muscles_worked")
    exercises_payload = payload.get("exercises")

    muscles_list = [str(x).strip() for x in _as_list(muscles_worked) if str(x).strip()]
    if not muscles_list:
        return {"error": "muscles_worked is required (string or list)"}, 400

    if exercises_payload is None or not isinstance(exercises_payload, list) or len(exercises_payload) == 0:
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

        # Force-load exercises while session is open
        for w in workouts:
            _ = w.exercises

        return {"username": username, "workouts": [_serialize_workout(w) for w in workouts]}


@app.post("/users/<username>/regimens")
def create_regimen(username: str):
    payload = flask.request.get_json(silent=True) or {}
    name = payload.get("name")
    description = payload.get("description")
    theme = payload.get("theme")
    plan = payload.get("plan")

    if not isinstance(name, str) or not name.strip():
        return {"error": "name is required"}, 400

    plan_json = None
    if plan is not None:
        try:
            plan_json = json.dumps(plan)
        except TypeError:
            return {"error": "plan must be JSON-serializable"}, 400

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        regimen = Regimen(
            user_id=user.id,
            name=name.strip(),
            description=description if isinstance(description, str) else None,
            theme=theme if isinstance(theme, str) else None,
            plan_json=plan_json,
        )
        session.add(regimen)
        session.commit()

        return {
            "id": regimen.id,
            "user_id": regimen.user_id,
            "name": regimen.name,
            "description": regimen.description,
            "theme": regimen.theme,
            "plan": plan,
            "created_at": regimen.created_at.isoformat(),
            "updated_at": regimen.updated_at.isoformat(),
        }, 201

@app.patch("/users/<username>/regimens/<regimen_id>")
def modify_regimen(username: str):
    # call Claude to modify the regimen
    return {"ok": True}, 200

@app.post("/users/<username>/workouts/<workout_id>/complete")
def complete_workout(username: str):
    # call Claude to complete the workout
    return {"ok": True}, 200
if __name__ == "__main__":
    init_db()
    app.run(debug=bool(int(os.getenv("FLASK_DEBUG", "1"))))