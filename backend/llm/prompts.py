import json
from .constants import MUSCLE_GROUPS, DAYS_OF_WEEK
from .schemas import DayPlan, WeeklyPlan

_ROLE = (
    "You are a health-conscious fitness instructor. Your client has joined our workout service "
    "to receive tailored workout plans and feedback during their fitness journey."
)


def _fmt(obj) -> str:
    return json.dumps(obj, indent=2)


# ── Step 1: high-level weekly plan ──────────────────────────────────────────

def build_step1_messages(onboarding: dict) -> tuple[str, str]:
    user = f"""<task>
You have been provided the user's basic biometric information, personal goals, time commitment, \
and existing/previous workout materials they use. Your job is to facilitate the creation of a \
workout regimen tailored to the user. The first step is to create a high-level weekly plan of \
workouts and rest days, along with their corresponding muscle groups. You will specify exercises, \
sets/reps, and other granular details in a later step — this step exists to inform that expansion.
</task>

<input>
{_fmt(onboarding)}
</input>

<constraints>
- Cover all seven days in order: {", ".join(DAYS_OF_WEEK)}
- muscle_groups for each day must only contain values from this list:
  {", ".join(MUSCLE_GROUPS)}
- Rest days have an empty muscle_groups list
- Use the reasoning field to capture decisions (e.g. why this split, recovery considerations) \
that should inform the exercise-selection step
</constraints>"""
    return _ROLE, user


# ── Step N: per-day exercise expansion ──────────────────────────────────────

def build_step_n_messages(
    onboarding: dict,
    weekly_plan: WeeklyPlan,
    day_plan: DayPlan,
    available_exercises: list[str],
) -> tuple[str, str]:
    weekly_overview = _fmt([d.model_dump() for d in weekly_plan.schedule])
    user = f"""<task>
You have been provided the user's basic biometric information, personal goals, time commitment, \
and existing/previous workout materials they use. You already created a weekly high-level overview \
of which muscle groups should be targeted each day. In this step, expand {day_plan.day}'s workout \
by selecting appropriate exercises and specifying all parameters.
</task>

<input>
{_fmt(onboarding)}
</input>

<weekly_plan>
{weekly_overview}
</weekly_plan>

<today>
Day: {day_plan.day}
Muscle groups: {", ".join(day_plan.muscle_groups)}
Planning notes: {day_plan.reasoning}
</today>

<available_exercises>
{chr(10).join(f"- {e}" for e in available_exercises)}
</available_exercises>

<constraints>
- Only select exercises from the available_exercises list above; do not invent new names
- Specify realistic values: sets, reps, weight in lbs, rest_time in seconds
- Use the notes field for brief form cues or exercise-specific guidance
- Choose exercise count and volume appropriate for the user's commitment and goals
</constraints>"""
    return _ROLE, user


# ── Modify regimen ───────────────────────────────────────────────────────────

def build_modify_messages(
    onboarding: dict,
    current_regimen: dict,
    feedback: str,
) -> tuple[str, str]:
    user = f"""<task>
You have been provided the user's basic biometric information, personal goals, time commitment, \
and existing/previous workout materials they use. You previously created a full weekly regimen \
for this user. The user has now provided feedback that requires modifications to the plan.
</task>

<input>
{_fmt(onboarding)}
</input>

<current_regimen>
{_fmt(current_regimen)}
</current_regimen>

<user_feedback>
{feedback}
</user_feedback>

<constraints>
- Return RFC 6902 JSON Patch operations targeting paths in current_regimen
- Supported ops: "add", "remove", "replace"
- Paths use JSON Pointer notation (e.g. "/workouts/Monday/0/sets")
- Only patch what the feedback explicitly requires; do not restructure unrelated parts
- Include a reasoning field explaining the changes
</constraints>"""
    return _ROLE, user


# ── Complete workout / log entry ─────────────────────────────────────────────

def build_complete_workout_messages(
    onboarding: dict,
    current_regimen: dict,
    completed_workout: dict,
    health_metrics: dict,
    today_day: str,
    tomorrow_workout: dict,
) -> tuple[str, str]:
    user = f"""<task>
You have been provided the user's basic biometric information, personal goals, time commitment, \
and the workout regimen you co-curated. The user just completed today's ({today_day}) workout. \
Review their performance and any available health metrics. Provide a brief observation about the \
session, and if warranted, suggest temporary modifications to tomorrow's scheduled workout as \
RFC 6902 JSON Patch operations. The user may reject your suggestions.
</task>

<input>
{_fmt(onboarding)}
</input>

<current_regimen>
{_fmt(current_regimen)}
</current_regimen>

<completed_workout>
{_fmt(completed_workout)}
</completed_workout>

<health_metrics>
{_fmt(health_metrics)}
</health_metrics>

<tomorrow_workout>
{_fmt(tomorrow_workout)}
</tomorrow_workout>

<constraints>
- observations: concise, actionable free-text summary of today's session
- modifications: RFC 6902 patches relative to the tomorrow_workout object above \
  (e.g. "/exercises/0/sets"); empty list if no changes are needed
- Only suggest modifications for recovery or safety reasons, not cosmetic changes
</constraints>"""
    return _ROLE, user
