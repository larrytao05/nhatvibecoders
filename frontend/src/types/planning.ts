export interface BackendUser {
  id: number;
  username: string;
  email?: string | null;
  current_weight: number | null;
  height: number | null;
  estimated_bf: number | null;
  created_at: string;
  updated_at: string;
}

export interface Exercise {
  id: number;
  workout_id: number;
  name: string;
  sets: number;
  reps: number;
  weight: number;
  rest_time: number;
  muscles_worked: string;
}

export interface Workout {
  id: number;
  user_id: number;
  regimen_id?: number | null;
  source_log_id?: number | null;
  mood: string | null;
  muscles_worked: string;
  scheduled_day?: string | null;
  status?: "scheduled" | string | null;
  exercises: Exercise[];
  created_at: string;
  updated_at: string;
}

export interface WorkoutReviewFeedback {
  overallFeel: number;
  concerns: string[];
  notes: string;
}

export interface WorkoutPreviewExercise {
  name: string;
  sets: number;
  reps: number;
  weight: number;
  rest_time: number;
  muscles_worked: string;
}

export interface WorkoutPreview {
  scheduled_day: string;
  status: string;
  muscles_worked: string;
  exercises: WorkoutPreviewExercise[];
}

export interface WorkoutCompletionSuggestion {
  logId: number;
  observations: string;
  modifications: Array<{ op: string; path: string; value?: unknown }>;
  baselineWorkout: WorkoutPreview | null;
  suggestedWorkout: WorkoutPreview | null;
}

export interface RegimenDay {
  id: string;
  day_index: number;
  title: string;
  focus: string;
  intensity: "Low" | "Medium" | "High";
  workout_id: number | null;
  notes: string;
}

export interface RegimenPlan {
  days: RegimenDay[];
}

export interface Regimen {
  id: number;
  user_id: number;
  name: string;
  goals?: string;
  description: string | null;
  theme: string | null;
  plan: RegimenPlan;
  created_at: string;
  updated_at: string;
}

export interface OnboardingProfile {
  height: string;
  current_weight: string;
  estimated_bf: string;
  goals: string[];
  frequency: number;
  equipment: string[];
  existingPlan: string;
}

export interface ExerciseLog {
  exerciseId: number;
  actualReps: string;
  actualWeight: string;
  complete: boolean;
}
