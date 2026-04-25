from typing import Any


DAYS_OF_WEEK = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]

# Granular muscle groups the LLM selects from in step 1.
# Empty muscle_groups list on a day signals a rest day.
MUSCLE_GROUPS = [
    # Chest
    "Upper Chest", "Lower Chest",
    # Back
    "Lats", "Upper Back", "Lower Back", "Rhomboids", "Traps",
    # Shoulders
    "Front Delt", "Side Delt", "Rear Delt",
    # Arms
    "Biceps", "Triceps", "Forearms",
    # Legs
    "Quads", "Hamstrings", "Glutes", "Calves", "Hip Flexors", "Adductors",
    # Core
    "Abs", "Obliques",
]


def _unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(cleaned)
    return unique


def normalize_muscle_groups(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return _unique_strings(value.split(","))
    if isinstance(value, list):
        return _unique_strings([str(item) for item in value])
    return _unique_strings([str(value)])


# Hardcoded exercise database with explicit exercise → muscle-group coverage.
EXERCISE_LIBRARY = [
    # Chest
    {"name": "Barbell Bench Press", "muscles_worked": ["Upper Chest", "Front Delt", "Triceps"]},
    {"name": "Dumbbell Bench Press", "muscles_worked": ["Upper Chest", "Front Delt", "Triceps"]},
    {"name": "Incline Barbell Press", "muscles_worked": ["Upper Chest", "Front Delt", "Triceps"]},
    {"name": "Incline Dumbbell Press", "muscles_worked": ["Upper Chest", "Front Delt", "Triceps"]},
    {"name": "Decline Bench Press", "muscles_worked": ["Lower Chest", "Front Delt", "Triceps"]},
    {"name": "Cable Fly", "muscles_worked": ["Upper Chest", "Lower Chest"]},
    {"name": "Dumbbell Fly", "muscles_worked": ["Upper Chest", "Lower Chest"]},
    {"name": "Pec Deck", "muscles_worked": ["Upper Chest", "Lower Chest"]},
    {"name": "Push-Up", "muscles_worked": ["Upper Chest", "Lower Chest", "Triceps"]},
    {"name": "Chest Dip", "muscles_worked": ["Lower Chest", "Front Delt", "Triceps"]},
    # Back
    {"name": "Pull-Up", "muscles_worked": ["Lats", "Upper Back", "Biceps"]},
    {"name": "Chin-Up", "muscles_worked": ["Lats", "Upper Back", "Biceps"]},
    {"name": "Lat Pulldown", "muscles_worked": ["Lats", "Biceps"]},
    {"name": "Barbell Row", "muscles_worked": ["Lats", "Upper Back", "Rhomboids", "Biceps"]},
    {"name": "Dumbbell Row", "muscles_worked": ["Lats", "Upper Back", "Rhomboids", "Biceps"]},
    {"name": "Cable Row", "muscles_worked": ["Lats", "Upper Back", "Rhomboids", "Biceps"]},
    {"name": "T-Bar Row", "muscles_worked": ["Lats", "Upper Back", "Rhomboids", "Biceps"]},
    {"name": "Face Pull", "muscles_worked": ["Rear Delt", "Rhomboids", "Traps"]},
    {"name": "Straight-Arm Pulldown", "muscles_worked": ["Lats"]},
    {"name": "Deadlift", "muscles_worked": ["Lower Back", "Hamstrings", "Glutes", "Traps"]},
    {"name": "Romanian Deadlift", "muscles_worked": ["Hamstrings", "Glutes", "Lower Back"]},
    {"name": "Hyperextension", "muscles_worked": ["Lower Back", "Glutes", "Hamstrings"]},
    {"name": "Good Morning", "muscles_worked": ["Hamstrings", "Glutes", "Lower Back"]},
    # Shoulders
    {"name": "Barbell Overhead Press", "muscles_worked": ["Front Delt", "Side Delt", "Triceps"]},
    {"name": "Dumbbell Shoulder Press", "muscles_worked": ["Front Delt", "Side Delt", "Triceps"]},
    {"name": "Arnold Press", "muscles_worked": ["Front Delt", "Side Delt", "Triceps"]},
    {"name": "Lateral Raise", "muscles_worked": ["Side Delt"]},
    {"name": "Cable Lateral Raise", "muscles_worked": ["Side Delt"]},
    {"name": "Front Raise", "muscles_worked": ["Front Delt"]},
    {"name": "Reverse Fly", "muscles_worked": ["Rear Delt", "Rhomboids"]},
    {"name": "Cable Reverse Fly", "muscles_worked": ["Rear Delt", "Rhomboids"]},
    {"name": "Shrug", "muscles_worked": ["Traps"]},
    # Arms
    {"name": "Barbell Curl", "muscles_worked": ["Biceps", "Forearms"]},
    {"name": "Dumbbell Curl", "muscles_worked": ["Biceps", "Forearms"]},
    {"name": "Hammer Curl", "muscles_worked": ["Biceps", "Forearms"]},
    {"name": "Preacher Curl", "muscles_worked": ["Biceps", "Forearms"]},
    {"name": "Cable Curl", "muscles_worked": ["Biceps", "Forearms"]},
    {"name": "Incline Dumbbell Curl", "muscles_worked": ["Biceps", "Forearms"]},
    {"name": "Tricep Pushdown", "muscles_worked": ["Triceps"]},
    {"name": "Overhead Tricep Extension", "muscles_worked": ["Triceps"]},
    {"name": "Skull Crusher", "muscles_worked": ["Triceps"]},
    {"name": "Close-Grip Bench Press", "muscles_worked": ["Triceps", "Upper Chest", "Front Delt"]},
    {"name": "Diamond Push-Up", "muscles_worked": ["Triceps", "Upper Chest", "Front Delt"]},
    {"name": "Wrist Curl", "muscles_worked": ["Forearms"]},
    {"name": "Reverse Wrist Curl", "muscles_worked": ["Forearms"]},
    # Legs
    {"name": "Barbell Squat", "muscles_worked": ["Quads", "Glutes", "Adductors"]},
    {"name": "Front Squat", "muscles_worked": ["Quads", "Glutes", "Abs"]},
    {"name": "Leg Press", "muscles_worked": ["Quads", "Glutes"]},
    {"name": "Hack Squat", "muscles_worked": ["Quads", "Glutes"]},
    {"name": "Lunge", "muscles_worked": ["Quads", "Glutes", "Hamstrings"]},
    {"name": "Walking Lunge", "muscles_worked": ["Quads", "Glutes", "Hamstrings"]},
    {"name": "Bulgarian Split Squat", "muscles_worked": ["Quads", "Glutes", "Hamstrings"]},
    {"name": "Leg Curl", "muscles_worked": ["Hamstrings"]},
    {"name": "Leg Extension", "muscles_worked": ["Quads"]},
    {"name": "Hip Thrust", "muscles_worked": ["Glutes", "Hamstrings"]},
    {"name": "Glute Bridge", "muscles_worked": ["Glutes", "Hamstrings"]},
    {"name": "Calf Raise", "muscles_worked": ["Calves"]},
    {"name": "Seated Calf Raise", "muscles_worked": ["Calves"]},
    {"name": "Adductor Machine", "muscles_worked": ["Adductors"]},
    {"name": "Cable Kickback", "muscles_worked": ["Glutes"]},
    # Core
    {"name": "Plank", "muscles_worked": ["Abs", "Obliques"]},
    {"name": "Side Plank", "muscles_worked": ["Obliques", "Abs"]},
    {"name": "Crunch", "muscles_worked": ["Abs"]},
    {"name": "Cable Crunch", "muscles_worked": ["Abs"]},
    {"name": "Leg Raise", "muscles_worked": ["Abs", "Hip Flexors"]},
    {"name": "Hanging Leg Raise", "muscles_worked": ["Abs", "Hip Flexors"]},
    {"name": "Russian Twist", "muscles_worked": ["Obliques", "Abs"]},
    {"name": "Ab Wheel Rollout", "muscles_worked": ["Abs", "Obliques"]},
    {"name": "Dead Bug", "muscles_worked": ["Abs", "Obliques", "Lower Back"]},
    {"name": "Bird Dog", "muscles_worked": ["Abs", "Obliques", "Lower Back"]},
]

EXERCISE_MUSCLE_MAP = {
    entry["name"]: normalize_muscle_groups(entry["muscles_worked"])
    for entry in EXERCISE_LIBRARY
}

EXERCISE_DB = [entry["name"] for entry in EXERCISE_LIBRARY]


def get_exercise_muscles(name: str, fallback: Any = None) -> list[str]:
    muscles = EXERCISE_MUSCLE_MAP.get(name)
    if muscles:
        return list(muscles)
    return normalize_muscle_groups(fallback)


def filter_exercises_by_muscles(muscle_groups: list[str]) -> list[str]:
    if not muscle_groups:
        return list(EXERCISE_DB)

    target_keys = {muscle.casefold() for muscle in muscle_groups if muscle.strip()}
    matched = [
        entry["name"]
        for entry in EXERCISE_LIBRARY
        if target_keys.intersection(muscle.casefold() for muscle in entry["muscles_worked"])
    ]
    return matched or list(EXERCISE_DB)
