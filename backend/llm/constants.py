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

# Hardcoded exercise name database. The LLM picks from this list only.
# Future: annotate each entry with muscle_group tags and filter per day.
EXERCISE_DB = [
    # Chest
    "Barbell Bench Press", "Dumbbell Bench Press",
    "Incline Barbell Press", "Incline Dumbbell Press",
    "Decline Bench Press", "Cable Fly", "Dumbbell Fly", "Pec Deck",
    "Push-Up", "Chest Dip",
    # Back
    "Pull-Up", "Chin-Up", "Lat Pulldown", "Barbell Row", "Dumbbell Row",
    "Cable Row", "T-Bar Row", "Face Pull", "Straight-Arm Pulldown",
    "Deadlift", "Romanian Deadlift", "Hyperextension", "Good Morning",
    # Shoulders
    "Barbell Overhead Press", "Dumbbell Shoulder Press", "Arnold Press",
    "Lateral Raise", "Cable Lateral Raise", "Front Raise",
    "Reverse Fly", "Cable Reverse Fly", "Shrug",
    # Arms
    "Barbell Curl", "Dumbbell Curl", "Hammer Curl", "Preacher Curl",
    "Cable Curl", "Incline Dumbbell Curl",
    "Tricep Pushdown", "Overhead Tricep Extension", "Skull Crusher",
    "Close-Grip Bench Press", "Diamond Push-Up",
    "Wrist Curl", "Reverse Wrist Curl",
    # Legs
    "Barbell Squat", "Front Squat", "Leg Press", "Hack Squat",
    "Lunge", "Walking Lunge", "Bulgarian Split Squat",
    "Leg Curl", "Leg Extension", "Hip Thrust", "Glute Bridge",
    "Calf Raise", "Seated Calf Raise", "Adductor Machine",
    "Cable Kickback",
    # Core
    "Plank", "Side Plank", "Crunch", "Cable Crunch", "Leg Raise",
    "Hanging Leg Raise", "Russian Twist", "Ab Wheel Rollout",
    "Dead Bug", "Bird Dog",
]
