# API spec (Flask)

Base URL (local): `http://localhost:5000`

All endpoints are JSON. Error responses follow:

```json
{ "error": "message" }
```

## LLM configuration (Anthropic / Claude)

Some endpoints call the LLM to generate or modify plans and to produce workout logs.

- **Required env var**: `ANTHROPIC_API_KEY`
  - The LLM client is `anthropic.AsyncAnthropic()` (it reads `ANTHROPIC_API_KEY` by default).
- **Failure mode**: LLM call failures return **502** with `{ "error": "LLM call failed: ..." }`.

## Health

### `GET /`

**200**

```json
{ "ok": true, "service": "nhatvibecoders-backend" }
```

## Users

### `POST /users`

Create a user.

**Request**

```json
{ "username": "larry", "current_weight": 180.5 }
```

**Responses**
- **201**
- **400** if `username` missing/blank
- **409** if `username` already exists

### `GET /users/<username>`

Fetch a user by username.

**Responses**
- **200**
- **404** if not found

### `PATCH /users/<username>`

Update fields on a user (currently only `current_weight`).

**Request**

```json
{ "current_weight": 179.2 }
```

**Responses**
- **200**
- **404** if not found

## Workouts

### `POST /users/<username>/workouts`

Log a workout for a user.

**Request**

```json
{
  "mood": "good",
  "muscles_worked": ["chest", "triceps"],
  "exercises": [
    {
      "name": "Bench Press",
      "sets": 3,
      "reps": 8,
      "weight": 185,
      "rest_time": 180,
      "muscles_worked": ["chest", "triceps"]
    }
  ]
}
```

**Notes**
- `muscles_worked` can be a **string** or **list of strings**.
- `exercises[].muscles_worked` defaults to the top-level `muscles_worked` if omitted.

**Responses**
- **201** returns the created workout (including exercises)
- **400** validation errors (`muscles_worked`, `exercises`, or exercise fields)
- **404** if user not found

### `GET /users/<username>/workouts`

List workouts for a user (newest first).

**Responses**
- **200**

```json
{
  "username": "larry",
  "workouts": [
    {
      "id": 1,
      "user_id": 1,
      "mood": "good",
      "muscles_worked": "chest, triceps",
      "exercises": [
        {
          "id": 1,
          "name": "Bench Press",
          "sets": 3,
          "reps": 8,
          "weight": 185.0,
          "rest_time": 180,
          "muscles_worked": "chest, triceps"
        }
      ],
      "created_at": "2026-04-25T18:00:00+00:00",
      "updated_at": "2026-04-25T18:00:00+00:00"
    }
  ]
}
```

- **404** if user not found

### `POST /users/<username>/workouts/<workout_id>/complete`

Mark a workout complete and generate an **LLM-produced** log entry (observations + suggested modifications).

**Request**

```json
{
  "regimen_id": 123,
  "today_day": "Monday",
  "health_metrics": { "sleep_hours": 7.5, "resting_hr": 58 }
}
```

**Notes**
- `workout_id` is an integer path param.
- `health_metrics` is optional; defaults to `{}`.
- The returned `modifications` are **RFC 6902 JSON Patch operations** that you may optionally apply to the regimen (see `POST /users/<username>/regimens/<regimen_id>/apply-patches`).

**Responses**
- **201** returns the created workout log entry
- **400** if `regimen_id` missing/not int, `today_day` missing/blank, regimen has no plan
- **404** if user/workout/regimen not found
- **502** if LLM call fails

## Regimens

### `POST /users/<username>/regimens`

Create a regimen for a user via an **LLM-generated** plan (two-phase HTN expansion).

**Request**

```json
{
  "name": "Upper/Lower (4x)",
  "description": "Hypertrophy focus",
  "theme": "science-based",
  "onboarding": {
    "goals": ["fat loss", "strength"],
    "equipment": ["barbell", "dumbbells"],
    "experience": "beginner",
    "days_per_week": 4,
    "constraints": "knee pain"
  }
}
```

**Responses**
- **201** returns created regimen
- **400** if `name` missing/blank, or `onboarding` missing/not a non-empty object
- **404** if user not found
- **502** if LLM call fails

### `PATCH /users/<username>/regimens/<regimen_id>`

Modify an existing regimen via LLM-generated **RFC 6902** patches (patches are applied immediately server-side).

**Request**

```json
{ "feedback": "Make it more powerlifting-focused and reduce volume on squats." }
```

**Responses**
- **200** returns updated regimen plus `reasoning`
- **400** if `feedback` missing/blank
- **404** if user/regimen not found
- **400** if regimen has no plan
- **422** if the returned patches can’t be applied (response includes `patches` when applicable)
- **502** if LLM call fails

### `POST /users/<username>/regimens/<regimen_id>/apply-patches`

Apply pre-computed RFC 6902 patches to a regimen (e.g. if the user accepts modifications suggested after completing a workout).

**Request**

```json
{
  "patches": [
    { "op": "replace", "path": "/workouts/Tuesday/0/sets", "value": 3 }
  ]
}
```

**Responses**
- **200** returns updated regimen
- **400** if `patches` is not a list
- **404** if user/regimen not found
- **400** if regimen has no plan
- **422** if patch application fails

## Logs

### `GET /users/<username>/logs`

Return all workout log entries for a user (newest first).

**Responses**
- **200**
- **404** if user not found
