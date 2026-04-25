# Database spec (Postgres)

The backend uses **Postgres** and **SQLAlchemy models** in `backend/db.py`. Tables are created automatically on backend startup via `Base.metadata.create_all(...)`.

## Connection

- **Env var**: `DATABASE_URL`
- **Example (Docker compose default)**: `postgresql+psycopg2://postgres:postgres@127.0.0.1:5433/nhatvibecoders`

## Tables

### `users`

Primary table for user identity + current body stats.

- **Columns**
  - **`id`**: `integer` primary key
  - **`username`**: `varchar(64)` **NOT NULL**
  - **`email`**: `varchar(255)` nullable
  - **`current_weight`**: `float` nullable
  - **`height`**: `float` nullable
  - **`estimated_bf`**: `float` nullable
  - **`created_at`**: `timestamptz` **NOT NULL**
  - **`updated_at`**: `timestamptz` **NOT NULL**

- **Constraints / indexes**
  - **Primary key**: `users_pkey (id)`
  - **Unique**: `username`, `email`
  - **Index**: `username`, `email` (SQLAlchemy `index=True`)

- **Relationships**
  - **1 → many** `users.id` → `Workouts.user_id`

### `Workouts`

A workout session logged by a user.

- **Columns**
  - **`id`**: `integer` primary key
  - **`user_id`**: `integer` **NOT NULL** (FK → `users.id`)
  - **`mood`**: `varchar(64)` nullable
  - **`created_at`**: `timestamptz` **NOT NULL**
  - **`updated_at`**: `timestamptz` **NOT NULL**

- **Constraints / indexes**
  - **Primary key**: `Workouts_pkey (id)`
  - **Foreign key**: `Workouts_user_id_fkey (user_id → users.id)`

- **Relationships**
  - **many → 1** `Workouts.user_id` → `users.id`
  - **1 → many** `Workouts.id` → `Exercises.workout_id`

### `Exercises`

Exercises performed within a workout session.

- **Columns**
  - **`id`**: `integer` primary key
  - **`workout_id`**: `integer` **NOT NULL** (FK → `Workouts.id`)
  - **`name`**: `varchar(64)` **NOT NULL**
  - **`sets`**: `integer` **NOT NULL**
  - **`reps`**: `integer` **NOT NULL**
  - **`weight`**: `float` **NOT NULL**
  - **`rest_time`**: `integer` **NOT NULL** (seconds)

- **Constraints / indexes**
  - **Primary key**: `Exercises_pkey (id)`
  - **Foreign key**: `Exercises_workout_id_fkey (workout_id → Workouts.id)`

- **Relationships**
  - **many → 1** `Exercises.workout_id` → `Workouts.id`

## ER diagram (logical)

```mermaid
erDiagram
  users ||--o{ Workouts : has
  Workouts ||--o{ Exercises : has
```

## Notes / conventions

- **Timestamps**: `created_at`/`updated_at` are stored as timezone-aware timestamps (`timestamptz`).
- **Table naming**: workout/exercise tables are currently named **`Workouts`** and **`Exercises`** (capitalized). If you prefer snake_case (`workouts`, `exercises`), we can normalize before adding more tables.

## Likely next tables (for the product you described)

- `progress_photos` (user_id, week_start, storage_key/url, pose, camera metadata)
- `body_metrics` (user_id, date, weight, waist, etc.)
- `lift_logs` / `sets` (actual sets/reps/weight/assistance/RPE/notes)
- `plans` + `plan_blocks` + `plan_days` (templated “bro/science/powerlifting” plans + customizations)
- `adherence` (sleep, steps, nutrition compliance)
