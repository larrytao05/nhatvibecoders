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

if not args.mock and not os.getenv("ANTHROPIC_API_KEY"):
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
    print("  Calling Claude to build weekly plan + expand each workout day...")

    onboarding = {
        "goals": ["muscle gain", "strength"],
        "biometrics": {"height": 70, "weight": 180, "estimated_bf": 15},
        "commitment": {"frequency": 4, "intensity": "moderate", "duration": 60},
        "equipment": ["barbell", "dumbbell", "cable machine"],
        "existing_plans": "Previously ran a basic 3-day full body routine.",
    }

    # In mock mode the MOCK_PLAN onboarding field is filled dynamically
    if args.mock:
        MOCK_PLAN["onboarding"] = onboarding

    regimen = check(
        client.post(f"/users/{username}/regimens", json={
            "name": "AI-Generated Plan",
            "theme": "science-based",
            "onboarding": onboarding,
        }),
        "POST /users/<u>/regimens",
    )

    print("\n  Weekly schedule:")
    for day in regimen["plan"]["schedule"]:
        muscles = ", ".join(day["muscle_groups"]) if day["muscle_groups"] else "Rest"
        print(f"    {day['day']:12s} — {muscles}")

    print("\n  Monday workout:")
    for ex in regimen["plan"]["workouts"].get("Monday", []):
        print(f"    {ex['name']:35s} {ex['sets']}x{ex['reps']} @ {ex['weight']} lbs")

    regimen_id = regimen["id"]

    # ── Step 3: Log a completed workout ─────────────────────────────────────
    section("Step 3 — Log a workout")
    monday_exercises = regimen["plan"]["workouts"].get("Monday", [])
    exercises_payload = [
        {**ex, "muscles_worked": ["chest", "triceps"]}
        for ex in monday_exercises
    ] or [
        {"name": "Barbell Bench Press", "sets": 4, "reps": 8, "weight": 135.0,
         "rest_time": 120, "muscles_worked": ["chest"]}
    ]

    workout = check(
        client.post(f"/users/{username}/workouts", json={
            "mood": "energetic",
            "muscles_worked": ["chest", "triceps"],
            "exercises": exercises_payload,
        }),
        "POST /users/<u>/workouts",
    )
    print(f"  Logged workout #{workout['id']} with {len(workout['exercises'])} exercises")

    # ── Step 4: Modify regimen with feedback (LLM: modify_regimen) ───────────
    section("Step 4 — Modify regimen from feedback (LLM: modify_regimen)")
    feedback = "I want to add more volume to Monday's bench press — increase sets and weight."
    print(f"  Feedback: \"{feedback}\"")

    modified = check(
        client.patch(f"/users/{username}/regimens/{regimen_id}", json={"feedback": feedback}),
        f"PATCH /users/<u>/regimens/{regimen_id}",
    )

    print(f"\n  Reasoning: {modified['reasoning']}")
    print("\n  Patches applied:")
    for patch_op in modified["plan"].get("_applied_patches", modified.get("patches", [])) or []:
        print(f"    {patch_op}")

    print("\n  Monday bench press after modification:")
    bench = modified["plan"]["workouts"]["Monday"][0]
    print(f"    {bench['name']} — {bench['sets']}x{bench['reps']} @ {bench['weight']} lbs")

    # ── Step 5: Complete workout (LLM: complete_workout) ─────────────────────
    section("Step 5 — Complete workout (LLM: complete_workout)")
    print("  Asking Claude to review the session and suggest tomorrow's adjustments...")

    health_metrics = {"resting_hr": 58, "sleep_hours": 7.5, "hrv": 62}
    log_entry = check(
        client.post(f"/users/{username}/workouts/{workout['id']}/complete", json={
            "regimen_id": regimen_id,
            "today_day": "Monday",
            "health_metrics": health_metrics,
        }),
        f"POST /users/<u>/workouts/{workout['id']}/complete",
    )

    print(f"\n  Observations: {log_entry['observations']}")
    if log_entry["modifications"]:
        print(f"\n  Suggested modifications to Tuesday's workout:")
        for mod in log_entry["modifications"]:
            print(f"    {mod['op']} {mod['path']} → {mod.get('value', '(remove)')}")
    else:
        print("\n  No modifications suggested — keep Tuesday as-is.")

    # ── Step 6: Accept modifications ─────────────────────────────────────────
    if log_entry["modifications"]:
        section("Step 6 — Accept suggested modifications")
        print("  Translating relative paths → absolute regimen paths and applying...")

        abs_patches = [
            {**mod, "path": f"/workouts/Tuesday{mod['path']}"}
            for mod in log_entry["modifications"]
        ]
        show("Absolute patches", abs_patches)

        updated = check(
            client.post(f"/users/{username}/regimens/{regimen_id}/apply-patches",
                        json={"patches": abs_patches}),
            f"POST /users/<u>/regimens/{regimen_id}/apply-patches",
        )
        print("\n  Tuesday workout after applying suggestions:")
        for ex in updated["plan"]["workouts"].get("Tuesday", []):
            print(f"    {ex['name']:35s} {ex['sets']}x{ex['reps']} @ {ex['weight']} lbs")

    # ── Step 7: Fetch logs ────────────────────────────────────────────────────
    section("Step 7 — Fetch workout logs")
    logs = check(client.get(f"/users/{username}/logs"), "GET /users/<u>/logs")
    print(f"\n  {len(logs['logs'])} log entry(s) found:")
    for log in logs["logs"]:
        print(f"    [{log['day']}] {log['observations'][:80]}...")

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
