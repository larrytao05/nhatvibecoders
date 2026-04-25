#!/usr/bin/env python3
"""
End-to-end pipeline runner for the nhatvibecoders backend.

Runs the full user flow through the real Flask app and real PostgreSQL DB.
In real mode, every LLM step calls Claude. In mock mode, hardcoded responses
are substituted so you can verify the plumbing without spending API credits.

Requirements: DB must be running (docker compose up -d).

Usage:
    python run_pipeline.py           # real Claude calls
    python run_pipeline.py --mock    # instant fake responses
"""
import argparse
import json
import os
import sys
import uuid
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser(description="Run the nhatvibecoders backend pipeline")
parser.add_argument("--mock", action="store_true", help="Use fake LLM responses (no API calls)")
args = parser.parse_args()

if args.mock:
    # No Docker needed — override DATABASE_URL to SQLite in-memory before any db import
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
elif not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not set. Add it to .env or run with --mock.")
    sys.exit(1)

# ── Mock responses ────────────────────────────────────────────────────────────

MOCK_PLAN = {
    "onboarding": {},  # filled in at runtime
    "schedule": [
        {"day": "Monday",    "muscle_groups": ["Upper Chest", "Triceps"], "reasoning": "Classic push day — chest/tri volume"},
        {"day": "Tuesday",   "muscle_groups": ["Lats", "Biceps"],         "reasoning": "Pull day — back width and arm curl"},
        {"day": "Wednesday", "muscle_groups": [],                          "reasoning": "Rest and recover"},
        {"day": "Thursday",  "muscle_groups": ["Quads", "Hamstrings", "Glutes"], "reasoning": "Leg day"},
        {"day": "Friday",    "muscle_groups": ["Front Delt", "Side Delt", "Rear Delt"], "reasoning": "Shoulder isolation"},
        {"day": "Saturday",  "muscle_groups": [],                          "reasoning": "Rest"},
        {"day": "Sunday",    "muscle_groups": [],                          "reasoning": "Rest"},
    ],
    "workouts": {
        "Monday": [
            {"name": "Barbell Bench Press", "sets": 4, "reps": 8,  "weight": 135.0, "rest_time": 120, "notes": "Retract scapula"},
            {"name": "Incline Dumbbell Press", "sets": 3, "reps": 10, "weight": 50.0, "rest_time": 90, "notes": ""},
            {"name": "Tricep Pushdown",     "sets": 3, "reps": 12, "weight": 50.0,  "rest_time": 60,  "notes": ""},
        ],
        "Tuesday": [
            {"name": "Pull-Up",    "sets": 4, "reps": 8,  "weight": 0.0,   "rest_time": 90,  "notes": "Full ROM"},
            {"name": "Barbell Row","sets": 4, "reps": 10, "weight": 115.0, "rest_time": 90,  "notes": ""},
            {"name": "Barbell Curl","sets": 3,"reps": 12, "weight": 65.0,  "rest_time": 60,  "notes": ""},
        ],
        "Thursday": [
            {"name": "Barbell Squat",        "sets": 4, "reps": 6,  "weight": 185.0, "rest_time": 180, "notes": "Depth below parallel"},
            {"name": "Romanian Deadlift",    "sets": 3, "reps": 10, "weight": 135.0, "rest_time": 120, "notes": ""},
            {"name": "Leg Press",            "sets": 3, "reps": 12, "weight": 270.0, "rest_time": 90,  "notes": ""},
        ],
        "Friday": [
            {"name": "Barbell Overhead Press","sets": 4,"reps": 8,  "weight": 95.0,  "rest_time": 120, "notes": ""},
            {"name": "Lateral Raise",         "sets": 4,"reps": 15, "weight": 20.0,  "rest_time": 60,  "notes": ""},
            {"name": "Reverse Fly",           "sets": 3,"reps": 15, "weight": 15.0,  "rest_time": 60,  "notes": ""},
        ],
    },
}

MOCK_MODIFY = {
    "patches": [
        {"op": "replace", "path": "/workouts/Monday/0/sets", "value": 5},
        {"op": "replace", "path": "/workouts/Monday/0/weight", "value": 145.0},
    ],
    "reasoning": "Increasing bench press volume and load for progressive overload as requested.",
}

MOCK_LOG = {
    "observations": (
        "Strong session — all sets completed at target weight. "
        "Recovery looks good based on metrics. "
        "Consider adding 5 lbs to bench next Monday."
    ),
    "modifications": [
        {"op": "replace", "path": "/exercises/0/sets", "value": 3},
    ],
}

# ── Printer ───────────────────────────────────────────────────────────────────

def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def show(label: str, data):
    print(f"\n{label}:")
    print(json.dumps(data, indent=2))


def check(response, step: str):
    data = response.get_json()
    if response.status_code >= 400:
        print(f"\n✗ {step} failed ({response.status_code}): {data}")
        sys.exit(1)
    print(f"✓ {step} ({response.status_code})")
    return data


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run(client):
    username = f"demo_{uuid.uuid4().hex[:6]}"
    print(f"\nUser: {username}")

    # ── Step 1: Create user ──────────────────────────────────────────────────
    section("Step 1 — Create user")
    user = check(
        client.post("/users", json={"username": username, "current_weight": 180.0}),
        "POST /users",
    )
    show("User", user)

    # ── Step 2: Create regimen (LLM: HTN expansion) ──────────────────────────
    section("Step 2 — Generate regimen (LLM: create_regimen)")

    onboarding = {
        "goals": ["muscle gain", "strength"],
        "biometrics": {"height": 70, "weight": 180, "estimated_bf": 15},
        "commitment": {"frequency": 4, "intensity": "moderate", "duration": 60},
        "equipment": ["barbell", "dumbbell", "cable machine"],
        "existing_plans": "Previously ran a basic 3-day full body routine.",
    }
    print("  Onboarding input:")
    for k, v in onboarding.items():
        print(f"    {k}: {v}")

    if args.mock:
        # Mock: use hardcoded plan, print it immediately
        MOCK_PLAN["onboarding"] = onboarding
        plan = MOCK_PLAN
        print("\n  [MOCK] Weekly skeleton:")
        for day in plan["schedule"]:
            muscles = ", ".join(day["muscle_groups"]) if day["muscle_groups"] else "— Rest —"
            print(f"    {day['day']:12s} {muscles}")
            if day["muscle_groups"]:
                print(f"    {'':12s} {day['reasoning']}")
        print("\n  [MOCK] Workout days expanded:")
        for day_name, exercises in plan["workouts"].items():
            print(f"\n    {day_name}:")
            for ex in exercises:
                print(f"      {ex['name']:35s} {ex['sets']}x{ex['reps']} @ {ex['weight']} lbs")
    else:
        # Real: call LLM primitives directly so we can print each day as it arrives
        import asyncio as _asyncio
        from llm.functions import expand_day as _expand_day
        from llm.functions import generate_weekly_plan as _gen_plan

        async def _stream():
            print("\n  [LLM call 1] Generating weekly skeleton...")
            weekly_plan = await _gen_plan(onboarding)
            print("  [LLM call 1] Done.\n")

            print("  Weekly schedule:")
            for day in weekly_plan.schedule:
                muscles = ", ".join(day.muscle_groups) if day.muscle_groups else "— Rest —"
                print(f"    {day.day:12s} {muscles}")
                if day.muscle_groups:
                    print(f"    {'':12s} {day.reasoning}")

            workout_days = [d for d in weekly_plan.schedule if d.muscle_groups]
            workouts_by_day = {}
            total = len(workout_days)
            for i, day_plan in enumerate(workout_days, 1):
                print(f"\n  [LLM call {i+1}/{total+1}] Expanding {day_plan.day} ({', '.join(day_plan.muscle_groups)})...")
                dw = await _expand_day(onboarding, weekly_plan, day_plan)
                workouts_by_day[dw.day] = [e.model_dump() for e in dw.exercises]
                print(f"  Done — {len(dw.exercises)} exercise(s):")
                for ex in dw.exercises:
                    print(f"    {ex.name:35s} {ex.sets}x{ex.reps} @ {ex.weight} lbs  rest {ex.rest_time}s")

            return {
                "onboarding": onboarding,
                "schedule": [d.model_dump() for d in weekly_plan.schedule],
                "workouts": workouts_by_day,
            }

        plan = _asyncio.run(_stream())

    # Save plan to DB directly (avoids a second round of LLM calls through the endpoint)
    from db import Regimen as _Regimen, get_session as _get_session
    raw_goals = onboarding.get("goals", "")
    goals_str = ", ".join(raw_goals) if isinstance(raw_goals, list) else str(raw_goals)
    with _get_session() as db_session:
        regimen_row = _Regimen(
            user_id=user["id"],
            name="AI-Generated Plan",
            goals=goals_str,
            theme="science-based",
            plan_json=json.dumps(plan),
        )
        db_session.add(regimen_row)
        db_session.commit()
        db_session.refresh(regimen_row)
        regimen_id = regimen_row.id
    print(f"\n✓ Regimen #{regimen_id} saved to DB")

    # ── Step 3: Log a completed workout ─────────────────────────────────────
    section("Step 3 — Log a workout (no LLM)")
    first_workout_day = next(iter(plan["workouts"]), None)
    day_exercises = plan["workouts"].get(first_workout_day, []) if first_workout_day else []
    exercises_payload = [
        {**ex, "muscles_worked": ex.get("muscles_worked", ["unknown"])}
        for ex in day_exercises
    ] or [
        {"name": "Barbell Bench Press", "sets": 4, "reps": 8, "weight": 135.0,
         "rest_time": 120, "muscles_worked": ["chest"]}
    ]

    print(f"  Logging {first_workout_day or 'Monday'}'s workout as completed:")
    for ex in exercises_payload:
        print(f"    {ex['name']}")

    workout = check(
        client.post(f"/users/{username}/workouts", json={
            "mood": "energetic",
            "muscles_worked": list({m for ex in exercises_payload for m in ex.get("muscles_worked", [])}),
            "exercises": exercises_payload,
        }),
        "POST /users/<u>/workouts",
    )
    print(f"  → Workout #{workout['id']} saved with {len(workout['exercises'])} exercises")

    # ── Step 4: Modify regimen with feedback (LLM: modify_regimen) ───────────
    section("Step 4 — Modify regimen from user feedback (LLM: modify_regimen)")
    feedback = f"I want to add more volume to {first_workout_day or 'Monday'}'s first exercise — increase sets and weight."
    print(f"  User feedback sent to Claude:\n    \"{feedback}\"\n")

    modified = check(
        client.patch(f"/users/{username}/regimens/{regimen_id}", json={"feedback": feedback}),
        f"PATCH /users/<u>/regimens/{regimen_id}",
    )

    print(f"\n  Claude's reasoning: {modified['reasoning']}")

    # Show before/after for the first exercise of the first workout day
    first_day_workouts = modified["plan"]["workouts"].get(first_workout_day, [])
    if first_day_workouts:
        ex = first_day_workouts[0]
        orig = plan["workouts"].get(first_workout_day, [{}])[0]
        print(f"\n  {first_workout_day} / {ex['name']} — before vs after:")
        print(f"    sets:   {orig.get('sets')} → {ex['sets']}")
        print(f"    weight: {orig.get('weight')} → {ex['weight']} lbs")

    # ── Step 5: Complete workout (LLM: complete_workout) ─────────────────────
    section("Step 5 — Complete workout (LLM: complete_workout)")
    health_metrics = {"resting_hr": 58, "sleep_hours": 7.5, "hrv": 62}
    today_day = first_workout_day or "Monday"
    print(f"  Today: {today_day}")
    print(f"  Health metrics sent: {health_metrics}")
    print("  Asking Claude to review the session and suggest adjustments to tomorrow's workout...\n")

    log_entry = check(
        client.post(f"/users/{username}/workouts/{workout['id']}/complete", json={
            "regimen_id": regimen_id,
            "today_day": today_day,
            "health_metrics": health_metrics,
        }),
        f"POST /users/<u>/workouts/{workout['id']}/complete",
    )

    print(f"\n  Claude's observations:\n    {log_entry['observations']}")
    if log_entry["modifications"]:
        print(f"\n  Suggested modifications to tomorrow's workout ({len(log_entry['modifications'])} patch(es)):")
        for mod in log_entry["modifications"]:
            print(f"    {mod['op']:8s} {mod['path']}  →  {mod.get('value', '(remove)')}")
    else:
        print("\n  No modifications suggested — tomorrow's workout unchanged.")

    # ── Step 6: Accept modifications ─────────────────────────────────────────
    from llm.constants import DAYS_OF_WEEK
    tomorrow_day = DAYS_OF_WEEK[(DAYS_OF_WEEK.index(today_day) + 1) % 7]

    if log_entry["modifications"]:
        section("Step 6 — Accept suggested modifications")
        print(f"  Tomorrow: {tomorrow_day}")
        print(f"  Translating {len(log_entry['modifications'])} relative path(s) → absolute regimen paths:")

        abs_patches = [
            {**mod, "path": f"/workouts/{tomorrow_day}{mod['path']}"}
            for mod in log_entry["modifications"]
        ]
        for p in abs_patches:
            print(f"    {p['op']:8s} {p['path']}  →  {p.get('value', '(remove)')}")

        updated = check(
            client.post(f"/users/{username}/regimens/{regimen_id}/apply-patches",
                        json={"patches": abs_patches}),
            f"POST /users/<u>/regimens/{regimen_id}/apply-patches",
        )
        print(f"\n  {tomorrow_day} workout after applying suggestions:")
        for ex in updated["plan"]["workouts"].get(tomorrow_day, []):
            print(f"    {ex['name']:35s} {ex['sets']}x{ex['reps']} @ {ex['weight']} lbs")

    # ── Step 7: Fetch logs ────────────────────────────────────────────────────
    section("Step 7 — Fetch workout logs")
    logs = check(client.get(f"/users/{username}/logs"), "GET /users/<u>/logs")
    print(f"\n  {len(logs['logs'])} log entry(s) found:")
    for log in logs["logs"]:
        print(f"\n  ┌─ Log #{log['id']}  [{log['log_date']}  {log['day']}]")
        print(f"  │  Observations: {log['observations']}")
        if log["modifications"]:
            print(f"  │  Modifications ({len(log['modifications'])}):")
            for mod in log["modifications"]:
                print(f"  │    {mod['op']:8s} {mod['path']}  →  {mod.get('value', '(remove)')}")
        else:
            print(f"  │  Modifications: none")
        print(f"  └─")

    section("Pipeline complete ✓")
    print(f"\n  All steps passed for user '{username}'.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    from app import app
    from db import init_db

    init_db()
    app.config["TESTING"] = True

    mode = "MOCK" if args.mock else "REAL (live Claude API)"
    print(f"\n{'═' * 60}")
    print(f"  nhatvibecoders — Backend Pipeline Runner")
    print(f"  Mode: {mode}")
    print(f"{'═' * 60}")

    with app.test_client() as client:
        run(client)


if args.mock:
    with patch("app.llm_create_regimen", new=AsyncMock(return_value=MOCK_PLAN)), \
         patch("app.llm_modify_regimen", new=AsyncMock(return_value=MOCK_MODIFY)), \
         patch("app.llm_complete_workout", new=AsyncMock(return_value=MOCK_LOG)):
        main()
else:
    main()
