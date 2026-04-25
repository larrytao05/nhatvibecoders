import { BackendUser, Exercise, ExerciseLog, OnboardingProfile, Regimen, Workout } from "../types/planning";

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

export async function createRegimen(username: string, regimen: Regimen): Promise<Regimen> {
  return requestJson<Regimen>(`/users/${encodeURIComponent(username)}/regimens`, {
    method: "POST",
    body: JSON.stringify({
      name: regimen.name,
      description: regimen.description,
      theme: regimen.theme,
      plan: regimen.plan,
    }),
  });
}

export async function requestRegimenTweak(username: string, regimenId: number, feedback: string): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>(`/users/${encodeURIComponent(username)}/regimens/${regimenId}`, {
    method: "PATCH",
    body: JSON.stringify({ feedback }),
  });
}

export async function requestWorkoutCompletion(username: string, workoutId: number): Promise<{ ok: boolean }> {
  return requestJson<{ ok: boolean }>(`/users/${encodeURIComponent(username)}/workouts/${workoutId}/complete`, {
    method: "POST",
  });
}
