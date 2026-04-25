import { BackendUser, Exercise, ExerciseLog, OnboardingProfile, Regimen, RegimenDay, Workout } from "../types/planning";

declare const process: { env?: Record<string, string | undefined> };

const env = process.env ?? {};

export const API_BASE_URL = env.EXPO_PUBLIC_API_URL ?? "http://127.0.0.1:5000";
export const DEFAULT_USERNAME = env.EXPO_PUBLIC_USERNAME ?? "demo-athlete";

interface ApiErrorBody {
  error?: string;
}

interface WorkoutListResponse {
  username: string;
  workouts: BackendWorkoutResponse[];
}

type BackendUserResponse = Partial<BackendUser> & {
  id: number;
  username: string;
  current_weight: number | null;
  created_at: string;
  updated_at: string;
};

type BackendExerciseResponse = Omit<Exercise, "workout_id"> & {
  workout_id?: number;
};

type BackendWorkoutResponse = Omit<Workout, "exercises"> & {
  exercises: BackendExerciseResponse[];
};

interface LlmRegimenPlan {
  onboarding?: Record<string, unknown>;
  schedule?: Array<{
    day: string;
    muscle_groups: string[];
    reasoning: string;
  }>;
  workouts?: Record<
    string,
    Array<{
      name: string;
      sets: number;
      reps: number;
      weight: number;
      rest_time: number;
      muscles_worked?: string;
      notes?: string;
    }>
  >;
}

interface BackendRegimenResponse extends Omit<Regimen, "plan"> {
  plan: Regimen["plan"] | LlmRegimenPlan;
  reasoning?: string;
}

export interface RegimenWithWorkouts {
  regimen: Regimen;
  plannedWorkouts: Workout[];
  reasoning?: string;
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...init?.headers,
      },
      ...init,
    });
  } catch (error) {
    throw new Error(
      `Cannot reach backend at ${API_BASE_URL}. If you are using Expo Go, restart Expo with EXPO_PUBLIC_API_URL set to your computer's LAN IP, not 127.0.0.1.`,
    );
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new Error(body.error ?? `Request failed with ${response.status}`);
  }

  return (await response.json()) as T;
}

function normalizeUser(user: BackendUserResponse, profile?: OnboardingProfile): BackendUser {
  return {
    id: user.id,
    username: user.username,
    email: user.email ?? null,
    current_weight: user.current_weight ?? (profile?.current_weight ? Number(profile.current_weight) : null),
    height: user.height ?? (profile?.height ? Number(profile.height) : null),
    estimated_bf: user.estimated_bf ?? (profile?.estimated_bf ? Number(profile.estimated_bf) : null),
    created_at: user.created_at,
    updated_at: user.updated_at,
  };
}

function normalizeWorkout(workout: BackendWorkoutResponse): Workout {
  return {
    ...workout,
    exercises: workout.exercises.map((exercise) => ({
      ...exercise,
      workout_id: exercise.workout_id ?? workout.id,
    })),
  };
}

function isLlmRegimenPlan(plan: BackendRegimenResponse["plan"]): plan is LlmRegimenPlan {
  return Boolean(plan && "schedule" in plan && "workouts" in plan);
}

function normalizeRegimen(response: BackendRegimenResponse): RegimenWithWorkouts {
  if (!isLlmRegimenPlan(response.plan)) {
    return {
      regimen: response as Regimen,
      plannedWorkouts: [],
      reasoning: response.reasoning,
    };
  }

  const now = new Date().toISOString();
  const llmPlan = response.plan;
  const plannedWorkouts: Workout[] = [];
  const days: RegimenDay[] = (llmPlan.schedule ?? []).map((dayPlan, index) => {
    const exercises = llmPlan.workouts?.[dayPlan.day] ?? [];
    const workoutId = exercises.length > 0 ? -(index + 1) : null;

    if (workoutId !== null) {
      plannedWorkouts.push({
        id: workoutId,
        user_id: response.user_id,
        mood: null,
        muscles_worked: dayPlan.muscle_groups.join(", "),
        created_at: now,
        updated_at: now,
        exercises: exercises.map((exercise, exerciseIndex) => ({
          id: workoutId * 100 - exerciseIndex,
          workout_id: workoutId,
          name: exercise.name,
          sets: exercise.sets,
          reps: exercise.reps,
          weight: exercise.weight,
          rest_time: exercise.rest_time,
          muscles_worked: exercise.muscles_worked ?? dayPlan.muscle_groups.join(", "),
        })),
      });
    }

    return {
      id: `day-${index + 1}`,
      day_index: index + 1,
      title: dayPlan.day,
      focus: dayPlan.muscle_groups.length > 0 ? dayPlan.muscle_groups.join(", ") : "Recovery",
      intensity: dayPlan.muscle_groups.length > 2 ? "High" : dayPlan.muscle_groups.length > 0 ? "Medium" : "Low",
      workout_id: workoutId,
      notes: dayPlan.reasoning,
    };
  });

  return {
    regimen: {
      ...response,
      plan: { days },
    },
    plannedWorkouts,
    reasoning: response.reasoning,
  };
}

function toBackendOnboarding(profile: OnboardingProfile) {
  return {
    height: Number(profile.height),
    current_weight: Number(profile.current_weight),
    estimated_bf: Number(profile.estimated_bf),
    goals: profile.goals,
    commitment: {
      frequency_per_week: profile.frequency,
    },
    equipment: profile.equipment,
    existing_plans: profile.existingPlan,
  };
}

export async function getHealth() {
  return requestJson<{ ok: boolean; service: string }>("/");
}

export async function createUser(username: string, currentWeight?: number | null, profile?: OnboardingProfile): Promise<BackendUser> {
  const user = await requestJson<BackendUserResponse>("/users", {
    method: "POST",
    body: JSON.stringify({
      username,
      current_weight: currentWeight ?? null,
    }),
  });

  return normalizeUser(user, profile);
}

export async function getUser(username: string, profile?: OnboardingProfile): Promise<BackendUser> {
  const user = await requestJson<BackendUserResponse>(`/users/${encodeURIComponent(username)}`);
  return normalizeUser(user, profile);
}

export async function getOrCreateUser(username: string, profile: OnboardingProfile): Promise<BackendUser> {
  try {
    return await getUser(username, profile);
  } catch (error) {
    return createUser(username, profile.current_weight ? Number(profile.current_weight) : null, profile);
  }
}

export async function updateUserWeight(username: string, currentWeight: number, profile?: OnboardingProfile): Promise<BackendUser> {
  const user = await requestJson<BackendUserResponse>(`/users/${encodeURIComponent(username)}`, {
    method: "PATCH",
    body: JSON.stringify({ current_weight: currentWeight }),
  });

  return normalizeUser(user, profile);
}

export async function getUserWorkouts(username: string): Promise<Workout[]> {
  const response = await requestJson<WorkoutListResponse>(`/users/${encodeURIComponent(username)}/workouts`);
  return response.workouts.map(normalizeWorkout);
}

export async function logWorkout(username: string, workout: Workout, logs: Record<number, ExerciseLog>): Promise<Workout> {
  const created = await requestJson<BackendWorkoutResponse>(`/users/${encodeURIComponent(username)}/workouts`, {
    method: "POST",
    body: JSON.stringify({
      mood: workout.mood ?? "completed",
      muscles_worked: workout.muscles_worked,
      exercises: workout.exercises.map((exercise) => ({
        name: exercise.name,
        sets: exercise.sets,
        reps: Number(logs[exercise.id]?.actualReps ?? exercise.reps),
        weight: Number(logs[exercise.id]?.actualWeight ?? exercise.weight),
        rest_time: exercise.rest_time,
        muscles_worked: exercise.muscles_worked,
      })),
    }),
  });

  return normalizeWorkout(created);
}

export async function createRegimen(username: string, regimen: Regimen, profile: OnboardingProfile): Promise<RegimenWithWorkouts> {
  const created = await requestJson<BackendRegimenResponse>(`/users/${encodeURIComponent(username)}/regimens`, {
    method: "POST",
    body: JSON.stringify({
      name: regimen.name,
      description: regimen.description,
      theme: regimen.theme,
      onboarding: toBackendOnboarding(profile),
    }),
  });

  return normalizeRegimen(created);
}

export async function requestRegimenTweak(username: string, regimenId: number, feedback: string): Promise<RegimenWithWorkouts> {
  const updated = await requestJson<BackendRegimenResponse>(`/users/${encodeURIComponent(username)}/regimens/${regimenId}`, {
    method: "PATCH",
    body: JSON.stringify({ feedback }),
  });

  return normalizeRegimen(updated);
}

export async function getLatestRegimen(username: string): Promise<RegimenWithWorkouts> {
  const response = await requestJson<BackendRegimenResponse>(`/users/${encodeURIComponent(username)}/regimens/latest`);
  return normalizeRegimen(response);
}

export async function requestWorkoutCompletion(
  username: string,
  workoutId: number,
  regimenId: number,
  todayDay: string,
): Promise<unknown> {
  return requestJson<unknown>(`/users/${encodeURIComponent(username)}/workouts/${workoutId}/complete`, {
    method: "POST",
    body: JSON.stringify({
      regimen_id: regimenId,
      today_day: todayDay,
      health_metrics: {},
    }),
  });
}
