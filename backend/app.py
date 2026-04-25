import asyncio
import copy
import json
import os
from datetime import date as date_type
from typing import Any
import re
import urllib.error
import urllib.request
from typing import Any, Optional

import flask
import jsonpatch
from dotenv import load_dotenv

from db import Exercise, Regimen, User, Workout, WorkoutLog, get_session, init_db
from llm import (
    complete_workout as llm_complete_workout,
    create_regimen as llm_create_regimen,
    expand_day as llm_expand_day,
    generate_weekly_plan as llm_generate_weekly_plan,
    modify_regimen as llm_modify_regimen,
)
from llm.schemas import DayPlan, WeeklyPlan
from llm.constants import DAYS_OF_WEEK


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
        "regimen_id": w.regimen_id,
        "source_log_id": w.source_log_id,
        "mood": w.mood,
        "muscles_worked": w.muscles_worked,
        "scheduled_day": w.scheduled_day,
        "status": w.status,
        "exercises": [_serialize_exercise(e) for e in (w.exercises or [])],
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
    }


def _safe_json_loads(raw: Optional[str]) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _parse_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _next_day_name(today_day: str) -> str:
    return DAYS_OF_WEEK[(DAYS_OF_WEEK.index(today_day) + 1) % 7]


def _find_schedule_day(plan: dict[str, Any], day_name: str) -> dict[str, Any]:
    schedule = plan.get("schedule")
    if not isinstance(schedule, list):
        return {}
    return next((day for day in schedule if isinstance(day, dict) and day.get("day") == day_name), {})


def _exercise_muscles(exercise_payload: dict[str, Any], fallback_muscles: list[str]) -> str:
    explicit = exercise_payload.get("muscles_worked")
    if isinstance(explicit, list):
        muscles = [str(item).strip() for item in explicit if str(item).strip()]
    elif isinstance(explicit, str):
        muscles = _parse_csv(explicit)
    else:
        muscles = fallback_muscles
    return ", ".join(muscles or fallback_muscles or ["general"])


def _workout_muscles(muscle_groups: list[str], exercises: list[dict[str, Any]]) -> str:
    if not exercises:
        return "Recovery"
    if muscle_groups:
        return ", ".join(muscle_groups)

    exercise_muscles = sorted(
        {
            muscle
            for exercise in exercises
            for muscle in _parse_csv(str(exercise.get("muscles_worked", "")))
            if muscle
        }
    )
    return ", ".join(exercise_muscles or ["general"])


def _build_next_workout_payload(
    plan: dict[str, Any],
    today_day: str,
    modifications: list[dict[str, Any]],
) -> dict[str, Any]:
    tomorrow_day = _next_day_name(today_day)
    schedule_day = _find_schedule_day(plan, tomorrow_day)
    muscle_groups = [str(item).strip() for item in _as_list(schedule_day.get("muscle_groups")) if str(item).strip()]
    base_exercises = copy.deepcopy(plan.get("workouts", {}).get(tomorrow_day, []))
    tomorrow_workout = {"day": tomorrow_day, "exercises": base_exercises}

    patched_workout = jsonpatch.apply_patch(tomorrow_workout, modifications, in_place=False)
    if not isinstance(patched_workout, dict):
        raise ValueError("tomorrow_workout must be an object")

    patched_exercises = patched_workout.get("exercises", [])
    if patched_exercises is None:
        patched_exercises = []
    if isinstance(patched_exercises, str) and patched_exercises.strip().lower() in {"", "rest", "recovery"}:
        patched_exercises = []
    if not isinstance(patched_exercises, list):
        raise ValueError("tomorrow_workout.exercises must be a list")

    normalized_exercises = []
    for idx, exercise_payload in enumerate(patched_exercises):
        if not isinstance(exercise_payload, dict):
            raise ValueError(f"tomorrow_workout.exercises[{idx}] must be an object")
        normalized_exercises.append(
            {
                "name": str(exercise_payload["name"]).strip(),
                "sets": int(exercise_payload["sets"]),
                "reps": int(exercise_payload["reps"]),
                "weight": float(exercise_payload["weight"]),
                "rest_time": int(exercise_payload["rest_time"]),
                "muscles_worked": _exercise_muscles(exercise_payload, muscle_groups),
            }
        )

    return {
        "scheduled_day": tomorrow_day,
        "status": "scheduled",
        "muscles_worked": _workout_muscles(muscle_groups, normalized_exercises),
        "exercises": normalized_exercises,
    }


def _workout_instance_from_payload(
    user_id: int,
    regimen_id: int,
    payload: dict[str, Any],
) -> Workout:
    workout = Workout(
        user_id=user_id,
        regimen_id=regimen_id,
        mood="scheduled",
        muscles_worked=payload["muscles_worked"],
        scheduled_day=payload["scheduled_day"],
        status="scheduled",
    )

    for exercise_payload in payload["exercises"]:
        workout.exercises.append(
            Exercise(
                name=exercise_payload["name"],
                sets=exercise_payload["sets"],
                reps=exercise_payload["reps"],
                weight=exercise_payload["weight"],
                rest_time=exercise_payload["rest_time"],
                muscles_worked=exercise_payload["muscles_worked"],
            )
        )

    return workout


def _build_scheduled_workout_instance(
    user_id: int,
    regimen_id: int,
    plan: dict[str, Any],
    today_day: str,
    modifications: list[dict[str, Any]],
) -> Workout | None:
    payload = _build_next_workout_payload(plan, today_day, modifications)
    return _workout_instance_from_payload(user_id, regimen_id, payload)


def _build_research_context(username: str) -> Optional[dict[str, Any]]:
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return None

        regimen = (
            session.query(Regimen)
            .filter_by(user_id=user.id)
            .order_by(Regimen.created_at.desc())
            .first()
        )
        workouts = (
            session.query(Workout)
            .filter_by(user_id=user.id)
            .order_by(Workout.created_at.desc())
            .limit(10)
            .all()
        )

        regimen_plan = _safe_json_loads(regimen.plan_json) if regimen else None
        days = []
        if isinstance(regimen_plan, dict):
            maybe_days = regimen_plan.get("days")
            if isinstance(maybe_days, list):
                for day in maybe_days:
                    if not isinstance(day, dict):
                        continue
                    days.append(
                        {
                            "day_index": day.get("day_index"),
                            "title": day.get("title"),
                            "focus": day.get("focus"),
                            "workout_id": day.get("workout_id"),
                        }
                    )

        recent_workouts = []
        for workout in workouts:
            exercises = workout.exercises or []
            recent_workouts.append(
                {
                    "id": workout.id,
                    "date": workout.created_at.date().isoformat(),
                    "mood": workout.mood,
                    "muscles_worked": _parse_csv(workout.muscles_worked),
                    "exercise_stats": [
                        {
                            "name": ex.name,
                            "sets": ex.sets,
                            "reps": ex.reps,
                            "weight": ex.weight,
                            "rest_time": ex.rest_time,
                            "muscles_worked": _parse_csv(ex.muscles_worked),
                        }
                        for ex in exercises
                    ],
                }
            )

        training_days = [day for day in days if day.get("workout_id")]
        adherence = {
            "recent_workout_count": len(recent_workouts),
            "planned_training_days": len(training_days),
            "possible_missed_days": max(0, len(training_days) - len(recent_workouts)),
            "streak_days": min(len(recent_workouts), 4),
            "skipped_exercises_estimate": 0,
        }

        return {
            "user_profile": {
                "username": user.username,
                "weight": user.current_weight,
                "goal": regimen.description if regimen and regimen.description else "build strength and muscle",
                "experience_level": "intermediate",
            },
            "constraints": {
                "equipment": ["barbell", "dumbbells"],
                "injuries": [],
                "time_per_session_mins": 60,
            },
            "regimen": {
                "name": regimen.name if regimen else None,
                "theme": regimen.theme if regimen else None,
                "weekly_schedule": days,
                "target_muscle_groups": sorted(
                    {
                        muscle
                        for workout in recent_workouts
                        for muscle in workout.get("muscles_worked", [])
                    }
                ),
            },
            "latest_workouts": recent_workouts,
            "adherence": adherence,
        }


def _build_citations(context: dict[str, Any]) -> list[str]:
    citations: list[str] = []
    regimen = context.get("regimen", {})
    latest_workouts = context.get("latest_workouts", [])

    if regimen.get("name"):
        citations.append(f"Using regimen '{regimen['name']}'")
    if regimen.get("theme"):
        citations.append(f"Plan theme: {regimen['theme']}")
    if latest_workouts:
        first = latest_workouts[0]
        muscles = ", ".join(first.get("muscles_worked", []))
        citations.append(f"Most recent workout focus: {muscles or 'not specified'} on {first.get('date')}")
    return citations


def _category_for_question(question: str) -> str:
    q = question.lower()
    if any(word in q for word in ["injury", "pain", "hurt", "strain", "ache"]):
        return "recovery"
    if any(word in q for word in ["progress", "increase", "load", "weight", "rep", "set"]):
        return "progression"
    if any(word in q for word in ["swap", "replace", "dumbbell", "equipment", "travel"]):
        return "exercise_swaps"
    if any(word in q for word in ["form", "technique", "cue", "brace"]):
        return "technique"
    if any(word in q for word in ["overtrain", "balance", "missed", "schedule", "next workout"]):
        return "program_balance"
    if any(word in q for word in ["protein", "hydration", "nutrition", "carb"]):
        return "nutrition"
    return "general"


def _suggest_questions_from_context(context: dict[str, Any]) -> list[str]:
    latest_workouts = context.get("latest_workouts", [])
    base = [
        "Based on my last workout, what should I train next?",
        "How much should I increase weight for compound lifts next week?",
        "What rest times should I use for strength vs hypertrophy?",
        "Can you swap today's workout for dumbbells only?",
        "I only have 35 minutes today - how should I modify this session?",
    ]
    if latest_workouts:
        muscles = latest_workouts[0].get("muscles_worked", [])
        if "quads" in muscles or "hamstrings" in muscles:
            base.insert(0, "How should I recover after my last leg day?")
        if "chest" in muscles or "shoulders" in muscles:
            base.insert(0, "How do I protect shoulders on pressing days?")
    return base[:8]


def _compose_answer(question: str, context: dict[str, Any], style: str) -> dict[str, Any]:
    category = _category_for_question(question)
    lower_q = question.lower()
    safety_flags = []
    if any(word in lower_q for word in ["injury", "pain", "hurt", "sharp"]):
        safety_flags.append("possible_injury_language")

    profile = context.get("user_profile", {})
    weight = profile.get("weight")
    latest_workouts = context.get("latest_workouts", [])

    answer = "Prioritize consistent training quality this week."
    why = [
        "Consistency and progressive overload drive measurable gains.",
        "Your current context suggests balancing hard sessions with recovery.",
    ]
    do_next = [
        "Keep your next 2 sessions within RPE 7-8 on compounds.",
        "Log all sets so progression decisions stay data-driven.",
    ]

    if category == "progression":
        answer = "Increase load by 2.5-5 lb only after you hit all target reps with clean form."
        why = [
            "Small load jumps preserve technique while maintaining overload.",
            "Using logged reps prevents chasing weight on low-readiness days.",
        ]
        do_next = [
            "For each main lift, keep weight the same until all sets hit target reps.",
            "If you clear all reps twice, add 2.5-5 lb next week.",
            "If you miss reps twice, keep load and add one rep per set first.",
        ]
    elif category == "recovery":
        answer = "Use a conservative recovery day and reduce peak effort until symptoms settle."
        why = [
            "Fatigue and discomfort improve with reduced intensity and better sleep/hydration.",
            "Guardrails lower injury risk while you keep training momentum.",
        ]
        do_next = [
            "Use 2-3 min rest for heavy work and 60-90s for accessories.",
            "Sleep 7-9 hours and hydrate with 2-3L water today.",
            "If pain is sharp or worsening, stop that lift and seek medical guidance.",
        ]
    elif category == "exercise_swaps":
        answer = "Swap barbell compounds for dumbbell or machine variants while keeping movement intent."
        why = [
            "Pattern-matched substitutions preserve progression with available equipment.",
            "Keeping volume similar avoids losing weekly stimulus.",
        ]
        do_next = [
            "Replace barbell bench with dumbbell bench for same sets/reps.",
            "Replace barbell row with chest-supported row.",
            "Keep session time by capping accessories to 2 sets if needed.",
        ]
    elif category == "technique":
        answer = "Prioritize controlled eccentric tempo and bracing cues before increasing intensity."
        why = [
            "Technique consistency improves force output and reduces breakdown.",
            "Good reps create safer long-term progression.",
        ]
        do_next = [
            "Use 2-3 sec eccentric on first two sets.",
            "Film one top set and check bar path or joint position.",
            "Stop sets 1-2 reps before form breakdown.",
        ]
    elif category == "program_balance":
        answer = "Train the under-served pattern next and avoid stacking similar high-fatigue days."
        why = [
            "Balanced push/pull/lower distribution reduces overload spikes.",
            "Even weekly muscle distribution supports recovery and adherence.",
        ]
        do_next = [
            "If last workout was upper push, make next day pull or lower-body.",
            "Keep total hard sets per muscle in the 10-16 weekly range.",
            "Use one low-fatigue accessory day if you missed sessions.",
        ]
    elif category == "nutrition":
        target_protein = None
        if isinstance(weight, (float, int)):
            target_protein = int(round(float(weight) * 0.8))
        answer = "Center nutrition around protein and hydration near training."
        why = [
            "Protein supports muscle repair and adaptation from training stress.",
            "Hydration quality correlates with performance and recovery.",
        ]
        do_next = [
            f"Target roughly {target_protein}g protein/day." if target_protein else "Target 0.7-1.0g protein per lb bodyweight.",
            "Drink 500-750ml water in the 2 hours before training.",
            "Have a protein + carb meal within 2 hours post-workout.",
        ]

    if style == "concise":
        do_next = do_next[:2]
        why = why[:1]
    elif style == "coach":
        answer = f"Coach call: {answer}"

    follow_ups = _suggest_questions_from_context(context)[:3]
    citations = _build_citations(context)
    return {
        "category": category,
        "direct_answer": answer,
        "why": why,
        "do_this_next": do_next,
        "follow_ups": follow_ups,
        "citations": citations,
        "safety_flags": safety_flags,
    }


def _extract_json_object(raw_text: str) -> Optional[dict[str, Any]]:
    text = raw_text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _compose_answer_with_claude(question: str, context: dict[str, Any], style: str) -> Optional[dict[str, Any]]:
    api_key = os.getenv("CLAUDE_API_KEY")
    if not api_key:
        return None

    model = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest")
    system_prompt = (
        "You are a fitness coaching assistant. Return ONLY a JSON object with keys: "
        "direct_answer (string), why (array of 1-3 strings), do_this_next (array of 2-4 strings), "
        "follow_ups (array of 3 strings), citations (array of 1-3 strings), safety_flags (array of strings), "
        "category (one of progression,recovery,exercise_swaps,technique,program_balance,nutrition,general). "
        "Keep advice practical, short, and grounded in provided context. "
        "If injury/pain language appears, include safety flag 'possible_injury_language'."
    )

    user_prompt = (
        f"Question: {question}\n"
        f"Style: {style}\n"
        f"Context JSON:\n{json.dumps(context, ensure_ascii=True)}"
    )

    payload = {
        "model": model,
        "max_tokens": 900,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body_raw = response.read().decode("utf-8")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None

    try:
        parsed = json.loads(body_raw)
    except json.JSONDecodeError:
        return None

    content_chunks = parsed.get("content", [])
    text_parts = []
    if isinstance(content_chunks, list):
        for chunk in content_chunks:
            if isinstance(chunk, dict) and chunk.get("type") == "text":
                text_value = chunk.get("text")
                if isinstance(text_value, str):
                    text_parts.append(text_value)

    combined_text = "\n".join(text_parts).strip()
    answer = _extract_json_object(combined_text)
    if not answer:
        return None

    required_keys = ["direct_answer", "why", "do_this_next", "follow_ups", "citations", "safety_flags", "category"]
    if any(key not in answer for key in required_keys):
        return None
    if not isinstance(answer.get("direct_answer"), str):
        return None
    if not isinstance(answer.get("why"), list):
        return None
    if not isinstance(answer.get("do_this_next"), list):
        return None
    if not isinstance(answer.get("follow_ups"), list):
        return None
    if not isinstance(answer.get("citations"), list):
        return None
    if not isinstance(answer.get("safety_flags"), list):
        return None
    if not isinstance(answer.get("category"), str):
        return None

    return {
        "category": str(answer["category"]),
        "direct_answer": str(answer["direct_answer"]),
        "why": [str(item) for item in answer["why"]][:3],
        "do_this_next": [str(item) for item in answer["do_this_next"]][:4],
        "follow_ups": [str(item) for item in answer["follow_ups"]][:3],
        "citations": [str(item) for item in answer["citations"]][:3],
        "safety_flags": [str(item) for item in answer["safety_flags"]][:3],
    }


def _generate_research_answer(question: str, context: dict[str, Any], style: str) -> dict[str, Any]:
    if not os.getenv("CLAUDE_API_KEY"):
        raise RuntimeError("Claude API key is missing")

    llm_answer = _compose_answer_with_claude(question, context, style)
    if llm_answer is None:
        raise RuntimeError("Claude request failed")
    return llm_answer

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
        "next_workout_id": log.next_workout_id,
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

    Returns the created WorkoutLog plus a next-workout preview. The preview is
    not scheduled until the client accepts or rejects it; the regimen remains
    the long-term blueprint.
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

        modifications = log_entry["modifications"]
        try:
            baseline_next_workout = _build_next_workout_payload(plan, today_day.strip(), [])
            suggested_next_workout = _build_next_workout_payload(plan, today_day.strip(), modifications)
        except (KeyError, TypeError, ValueError, jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as exc:
            return {"error": f"next workout generation failed: {exc}", "modifications": modifications}, 422

        log = WorkoutLog(
            user_id=user.id,
            regimen_id=regimen_id,
            workout_id=workout_id,
            log_date=date_type.today(),
            day=today_day.strip(),
            observations=log_entry["observations"],
            modifications_json=json.dumps(modifications),
        )
        session.add(log)
        session.commit()

        response_payload = _serialize_log(log)
        response_payload["baseline_next_workout"] = baseline_next_workout
        response_payload["suggested_next_workout"] = suggested_next_workout
        print(
            f"[LLM] complete_workout response for username={username!r}; workout_id={workout_id}; regimen_id={regimen_id}:\n"
            f"{json.dumps(response_payload, indent=2)}",
            flush=True,
        )
        return response_payload, 201


@app.post("/users/<username>/logs/<int:log_id>/next-workout/<decision>")
def decide_next_workout(username: str, log_id: int, decision: str):
    """
    Create the next scheduled workout instance after the user reviews LLM
    suggestions. Accept uses the suggested patches; reject uses the regimen
    blueprint unchanged.
    """
    if decision not in {"accept", "reject"}:
        return {"error": "decision must be accept or reject"}, 400

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        log = session.query(WorkoutLog).filter_by(id=log_id, user_id=user.id).first()
        if log is None:
            return {"error": "log not found"}, 404
        if log.regimen_id is None:
            return {"error": "log has no regimen"}, 400
        if log.next_workout_id is not None:
            existing = session.query(Workout).filter_by(id=log.next_workout_id, user_id=user.id).first()
            if existing is not None:
                _ = existing.exercises
                return {"next_workout": _serialize_workout(existing), "decision": decision}, 200

        regimen = session.query(Regimen).filter_by(id=log.regimen_id, user_id=user.id).first()
        if regimen is None:
            return {"error": "regimen not found"}, 404
        if not regimen.plan_json:
            return {"error": "regimen has no plan"}, 400

        plan = json.loads(regimen.plan_json)
        modifications = json.loads(log.modifications_json) if log.modifications_json else []
        patches = modifications if decision == "accept" else []

        try:
            next_workout = _build_scheduled_workout_instance(user.id, regimen.id, plan, log.day, patches)
        except (KeyError, TypeError, ValueError, jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as exc:
            return {"error": f"next workout generation failed: {exc}", "modifications": patches}, 422
        next_workout.source_log_id = log.id
        session.add(next_workout)
        session.flush()
        log.next_workout_id = next_workout.id
        session.commit()
        _ = next_workout.exercises

        return {"next_workout": _serialize_workout(next_workout), "decision": decision}, 201


# ── Regimens ─────────────────────────────────────────────────────────────────

@app.get("/users/<username>/regimens/latest")
def get_latest_regimen(username: str):
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        regimen = (
            session.query(Regimen)
            .filter_by(user_id=user.id)
            .order_by(Regimen.created_at.desc())
            .first()
        )
        scheduled_workouts: list[dict[str, Any]] = []
        if regimen is not None:
            workouts = (
                session.query(Workout)
                .filter_by(user_id=user.id, regimen_id=regimen.id, status="scheduled")
                .order_by(Workout.created_at.desc())
                .all()
            )
            for workout in workouts:
                _ = workout.exercises
            scheduled_workouts = [_serialize_workout(workout) for workout in workouts]

        return {
            "regimen": _serialize_regimen(regimen) if regimen else None,
            "scheduled_workouts": scheduled_workouts,
        }


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

        print(
            f"[LLM TEST] create_regimen request received for username={username!r}; calling Claude regimen generator...",
            flush=True,
        )
        try:
            plan = asyncio.run(llm_create_regimen(onboarding))
        except Exception as exc:
            print(f"[LLM TEST] create_regimen failed for username={username!r}: {exc}", flush=True)
            return {"error": f"LLM call failed: {exc}"}, 502
        print(
            "[LLM TEST] create_regimen succeeded "
            f"for username={username!r}; schedule_days={len(plan.get('schedule', []))}; "
            f"workout_days={len(plan.get('workouts', {}))}",
            flush=True,
        )

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


@app.post("/users/<username>/regimens/skeleton")
def create_regimen_skeleton(username: str):
    """
    Generate and persist only step 1 of the regimen pipeline.

    The returned plan has a weekly schedule and an empty workouts map so the
    client can render the regimen immediately while individual days expand.
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

        print(
            f"[LLM] create_regimen_skeleton started for username={username!r}",
            flush=True,
        )
        try:
            weekly_plan = asyncio.run(llm_generate_weekly_plan(onboarding))
        except Exception as exc:
            print(f"[LLM] create_regimen_skeleton failed for username={username!r}: {exc}", flush=True)
            return {"error": f"LLM call failed: {exc}"}, 502
        print(
            f"[LLM] create_regimen_skeleton succeeded for username={username!r}; schedule_days={len(weekly_plan.schedule)}",
            flush=True,
        )

        raw_goals = onboarding.get("goals", "")
        goals_str = ", ".join(raw_goals) if isinstance(raw_goals, list) else str(raw_goals)
        plan = {
            "onboarding": onboarding,
            "schedule": [day.model_dump() for day in weekly_plan.schedule],
            "workouts": {},
        }

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


@app.post("/users/<username>/regimens/<int:regimen_id>/expand-day")
def expand_regimen_day(username: str, regimen_id: int):
    """
    Expand one skeleton day into a full exercise list and persist it.

    Body:
      day  str  — schedule day name, e.g. "Monday"
    """
    payload = flask.request.get_json(silent=True) or {}
    day_name = payload.get("day")
    if not isinstance(day_name, str) or not day_name.strip():
        return {"error": "day is required"}, 400

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
        schedule = plan.get("schedule")
        if not isinstance(schedule, list):
            return {"error": "regimen has no schedule"}, 400

        day_payload = next((day for day in schedule if isinstance(day, dict) and day.get("day") == day_name.strip()), None)
        if day_payload is None:
            return {"error": "day not found in regimen schedule"}, 404

        muscle_groups = day_payload.get("muscle_groups")
        if not isinstance(muscle_groups, list) or not muscle_groups:
            plan.setdefault("workouts", {})[day_name.strip()] = []
            regimen.plan_json = json.dumps(plan)
            session.commit()
            return _serialize_regimen(regimen), 200

        print(
            f"[LLM] expand_regimen_day started for username={username!r}; regimen_id={regimen_id}; day={day_name.strip()!r}",
            flush=True,
        )
        try:
            weekly_plan = WeeklyPlan(schedule=[DayPlan(**day) for day in schedule])
            day_plan = DayPlan(**day_payload)
            day_workout = asyncio.run(llm_expand_day(plan.get("onboarding", {}), weekly_plan, day_plan))
        except Exception as exc:
            print(
                f"[LLM] expand_regimen_day failed for username={username!r}; day={day_name.strip()!r}: {exc}",
                flush=True,
            )
            return {"error": f"LLM call failed: {exc}"}, 502
        print(
            f"[LLM] expand_regimen_day succeeded for username={username!r}; day={day_workout.day!r}; exercises={len(day_workout.exercises)}",
            flush=True,
        )

        plan.setdefault("workouts", {})[day_workout.day] = [exercise.model_dump() for exercise in day_workout.exercises]
        regimen.plan_json = json.dumps(plan)
        session.commit()

        return _serialize_regimen(regimen), 200


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

        print(
            f"[LLM] modify_regimen started for username={username!r}; regimen_id={regimen_id}; feedback={feedback.strip()!r}",
            flush=True,
        )
        try:
            result = asyncio.run(llm_modify_regimen(onboarding, plan, feedback.strip()))
        except Exception as exc:
            print(
                f"[LLM] modify_regimen failed for username={username!r}; regimen_id={regimen_id}: {exc}",
                flush=True,
            )
            return {"error": f"LLM call failed: {exc}"}, 502

        try:
            updated_plan = jsonpatch.apply_patch(plan, result["patches"])
        except (jsonpatch.JsonPatchException, jsonpatch.JsonPointerException) as exc:
            print(
                f"[LLM] modify_regimen patch failed for username={username!r}; regimen_id={regimen_id}; patches={result['patches']}: {exc}",
                flush=True,
            )
            return {"error": f"patch application failed: {exc}", "patches": result["patches"]}, 422

        regimen.plan_json = json.dumps(updated_plan)
        session.commit()

        print(
            f"[LLM] modify_regimen succeeded for username={username!r}; regimen_id={regimen_id}; patches={len(result['patches'])}",
            flush=True,
        )

        response_payload = {**_serialize_regimen(regimen), "reasoning": result["reasoning"]}
        print(
            f"[LLM] modify_regimen response for username={username!r}; regimen_id={regimen_id}:\n"
            f"{json.dumps(response_payload, indent=2)}",
            flush=True,
        )

        return response_payload


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


@app.get("/users/<username>/research/context")
def get_research_context(username: str):
    context = _build_research_context(username)
    if context is None:
        return {"error": "user not found"}, 404
    return context


@app.get("/users/<username>/research/suggestions")
def get_research_suggestions(username: str):
    context = _build_research_context(username)
    if context is None:
        return {"error": "user not found"}, 404

    return {
        "suggested_questions": _suggest_questions_from_context(context),
    }


@app.post("/users/<username>/research/ask")
def ask_research_question(username: str):
    payload = flask.request.get_json(silent=True) or {}
    question = payload.get("question")
    style = payload.get("style", "concise")
    if not isinstance(question, str) or not question.strip():
        return {"error": "question is required"}, 400
    if style not in ["concise", "detailed", "coach"]:
        return {"error": "style must be one of concise|detailed|coach"}, 400

    context = _build_research_context(username)
    if context is None:
        return {"error": "user not found"}, 404

    try:
        response = _generate_research_answer(question.strip(), context, style)
    except RuntimeError:
        return {"error": "Could not connect to AI provider. Please try again."}, 502

    return {
        "question": question.strip(),
        "style": style,
        **response,
    }


@app.post("/users/<username>/research/actions")
def research_actions(username: str):
    payload = flask.request.get_json(silent=True) or {}
    action = payload.get("action")
    answer_snapshot = payload.get("answer_snapshot")

    if action not in ["apply_to_next_workout", "save_as_note", "regenerate"]:
        return {"error": "action must be apply_to_next_workout|save_as_note|regenerate"}, 400

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user is None:
            return {"error": "user not found"}, 404

        if action == "apply_to_next_workout":
            note = "Applied research guidance to next workout plan."
            user.log = f"{(user.log or '').strip()}\n{note}".strip()
            session.commit()
            return {"ok": True, "message": note}

        if action == "save_as_note":
            content = str(answer_snapshot or "Saved empty note")
            user.log = f"{(user.log or '').strip()}\nResearch note: {content}".strip()
            session.commit()
            return {"ok": True, "message": "Saved research note to user log"}

        if action == "regenerate":
            question = payload.get("question")
            style = payload.get("style", "concise")
            if not isinstance(question, str) or not question.strip():
                return {"error": "question is required for regenerate"}, 400
            if style not in ["concise", "detailed", "coach"]:
                return {"error": "style must be one of concise|detailed|coach"}, 400

            context = _build_research_context(username)
            if context is None:
                return {"error": "user not found"}, 404
            try:
                response = _generate_research_answer(question.strip(), context, style)
            except RuntimeError:
                return {"error": "Could not connect to AI provider. Please try again."}, 502
            response["direct_answer"] = f"{response['direct_answer']} (regenerated)"
            return {"ok": True, "question": question.strip(), "style": style, **response}

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=bool(int(os.getenv("FLASK_DEBUG", "1"))))
