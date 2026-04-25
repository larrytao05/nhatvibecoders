"""Shared sample data for all test modules."""

SAMPLE_ONBOARDING = {
    "goals": ["muscle gain", "strength"],
    "biometrics": {"height": 70, "weight": 180, "estimated_bf": 15},
    "commitment": {"frequency": 4, "intensity": "moderate", "duration": 60},
    "equipment": ["barbell", "dumbbell"],
    "existing_plans": "",
}

# Full 7-day plan returned by the mocked LLM create_regimen call.
SAMPLE_PLAN = {
    "onboarding": SAMPLE_ONBOARDING,
    "schedule": [
        {"day": "Monday",    "muscle_groups": ["Upper Chest", "Triceps"], "reasoning": "Push day"},
        {"day": "Tuesday",   "muscle_groups": ["Lats", "Biceps"],         "reasoning": "Pull day"},
        {"day": "Wednesday", "muscle_groups": [],                          "reasoning": "Rest"},
        {"day": "Thursday",  "muscle_groups": ["Quads", "Hamstrings"],    "reasoning": "Leg day"},
        {"day": "Friday",    "muscle_groups": ["Front Delt", "Side Delt"],"reasoning": "Shoulder day"},
        {"day": "Saturday",  "muscle_groups": [],                          "reasoning": "Rest"},
        {"day": "Sunday",    "muscle_groups": [],                          "reasoning": "Rest"},
    ],
    "workouts": {
        "Monday": [
            {"name": "Barbell Bench Press", "sets": 4, "reps": 8,  "weight": 135.0, "rest_time": 120, "notes": ""},
            {"name": "Chest Dip",           "sets": 3, "reps": 12, "weight": 0.0,   "rest_time": 90,  "notes": ""},
        ],
        "Tuesday": [
            {"name": "Pull-Up",    "sets": 4, "reps": 8,  "weight": 0.0,   "rest_time": 90, "notes": ""},
            {"name": "Barbell Row","sets": 4, "reps": 10, "weight": 115.0, "rest_time": 90, "notes": ""},
        ],
        "Thursday": [
            {"name": "Barbell Squat", "sets": 4, "reps": 6, "weight": 185.0, "rest_time": 180, "notes": ""},
        ],
        "Friday": [
            {"name": "Barbell Overhead Press", "sets": 4, "reps": 8, "weight": 95.0, "rest_time": 120, "notes": ""},
        ],
    },
}

SAMPLE_EXERCISES_PAYLOAD = [
    {
        "name": "Barbell Bench Press",
        "sets": 4,
        "reps": 8,
        "weight": 135.0,
        "rest_time": 120,
        "muscles_worked": ["chest", "triceps"],
    }
]
