# API spec (Flask)

Base URL (local): `http://localhost:5000`

All endpoints are JSON. Error responses follow:

```json
{ "error": "message" }
```

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

## Regimens

### `POST /users/<username>/regimens`

Create a regimen for a user.

**Request**

```json
{
  "name": "Upper/Lower (4x)",
  "description": "Hypertrophy focus",
  "theme": "science-based",
  "plan": { "weeks": 12, "days": ["Upper A", "Lower A", "Upper B", "Lower B"] }
}
```

**Responses**
- **201** returns created regimen
- **400** if `name` missing/blank, or `plan` is missing, or `plan` is not JSON-serializable
- **404** if user not found

## Not implemented yet

These routes exist but are currently placeholders:

- `PATCH /users/<username>/regimens/<regimen_id>`
- `POST /users/<username>/workouts/<workout_id>/complete`
