import os
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    current_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    height: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_bf: Mapped[float | None] = mapped_column(Float, nullable=True)
    log: Mapped[str | None] = mapped_column(Text, nullable=True)
    workouts: Mapped[list["Workout"]] = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    regimens: Mapped[list["Regimen"]] = relationship("Regimen", back_populates="user", cascade="all, delete-orphan")
    logs: Mapped[list["WorkoutLog"]] = relationship("WorkoutLog", back_populates="user", cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Regimen(Base):
    __tablename__ = "Regimens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user: Mapped["User"] = relationship("User", back_populates="regimens")
    goals: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    theme: Mapped[str | None] = mapped_column(String(64), nullable=True)
    plan_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Workout(Base):
    __tablename__ = "Workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    regimen_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("Regimens.id"), nullable=True, index=True)
    source_log_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    user: Mapped["User"] = relationship("User", back_populates="workouts")
    exercises: Mapped[list["Exercise"]] = relationship(
        "Exercise", back_populates="workout", cascade="all, delete-orphan"
    )
    mood: Mapped[str | None] = mapped_column(String(64), nullable=True)
    muscles_worked: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_day: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Exercise(Base):
    __tablename__ = "Exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    rest_time: Mapped[int] = mapped_column(Integer, nullable=False)
    muscles_worked: Mapped[str] = mapped_column(String(255), nullable=False)
    workout_id: Mapped[int] = mapped_column(Integer, ForeignKey("Workouts.id"), nullable=False)
    workout: Mapped["Workout"] = relationship("Workout", back_populates="exercises")

class WorkoutLog(Base):
    """Append-only log entry created after each completed workout.

    observations   — LLM free-text summary of the session.
    modifications_json — RFC 6902 patches relative to tomorrow's workout object.
                         Stored as a JSON string; the user may accept or reject them.
    """
    __tablename__ = "WorkoutLogs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    regimen_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("Regimens.id"), nullable=True, index=True)
    workout_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("Workouts.id"), nullable=True)
    next_workout_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("Workouts.id"), nullable=True)
    user: Mapped["User"] = relationship("User", back_populates="logs")
    log_date: Mapped[date] = mapped_column(Date, nullable=False)   # actual calendar date
    day: Mapped[str] = mapped_column(String(16), nullable=False)   # e.g. "Monday"
    observations: Mapped[str] = mapped_column(Text, nullable=False)
    modifications_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see backend/.env.example).")
    return url


def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _ensure_columns(engine)


def _ensure_columns(engine) -> None:
    """Lightweight forward migration for local/dev databases without Alembic."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "Workouts" not in table_names or "WorkoutLogs" not in table_names:
        return

    workout_columns = {column["name"] for column in inspector.get_columns("Workouts")}
    log_columns = {column["name"] for column in inspector.get_columns("WorkoutLogs")}
    additions: list[tuple[str, str, str]] = []

    if "regimen_id" not in workout_columns:
        additions.append(("Workouts", "regimen_id", "INTEGER"))
    if "source_log_id" not in workout_columns:
        additions.append(("Workouts", "source_log_id", "INTEGER"))
    if "scheduled_day" not in workout_columns:
        additions.append(("Workouts", "scheduled_day", "VARCHAR(16)"))
    if "status" not in workout_columns:
        additions.append(("Workouts", "status", "VARCHAR(32)"))
    if "next_workout_id" not in log_columns:
        additions.append(("WorkoutLogs", "next_workout_id", "INTEGER"))
    if "log_date" not in log_columns:
        additions.append(("WorkoutLogs", "log_date", "DATE"))
    if "day" not in log_columns:
        additions.append(("WorkoutLogs", "day", "VARCHAR(16)"))
    if "observations" not in log_columns:
        additions.append(("WorkoutLogs", "observations", "TEXT"))
    if "modifications_json" not in log_columns:
        additions.append(("WorkoutLogs", "modifications_json", "TEXT"))
    if "created_at" not in log_columns:
        additions.append(("WorkoutLogs", "created_at", "TIMESTAMP WITH TIME ZONE"))

    if not additions:
        return

    with engine.begin() as connection:
        for table_name, column_name, ddl_type in additions:
            connection.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {column_name} {ddl_type}'))


def get_session() -> Session:
    engine = get_engine()
    return Session(engine)
