import React, { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { getMockRegimen, getMockReplacementRegimen, getMockUser, getMockWorkoutById, getMockWorkouts } from "../mocks/api";
import { BackendUser, ExerciseLog, OnboardingProfile, Regimen, RegimenDay, Workout } from "../types/planning";

interface WorkoutPlannerContextValue {
  user: BackendUser | null;
  onboarding: OnboardingProfile;
  regimen: Regimen | null;
  workouts: Workout[];
  selectedDayId: string;
  selectedDay: RegimenDay | null;
  currentWorkout: Workout | null;
  exerciseLogs: Record<number, ExerciseLog>;
  isAiProcessing: boolean;
  onboardingComplete: boolean;
  completionRatio: number;
  setBiometricField: (field: "height" | "current_weight" | "estimated_bf", value: string) => void;
  toggleGoal: (goal: string) => void;
  setFrequency: (frequency: number) => void;
  toggleEquipment: (equipment: string) => void;
  setExistingPlan: (value: string) => void;
  setSelectedDayId: (dayId: string) => void;
  generateRegimenFromText: () => Promise<void>;
  fetchWorkoutById: (id: number) => Promise<Workout | null>;
  updateExerciseLog: (exerciseId: number, updates: Partial<ExerciseLog>) => void;
  completeWorkout: () => Promise<void>;
  tweakPlanWithFeedback: (feedback: string) => Promise<void>;
}

const defaultOnboarding: OnboardingProfile = {
  height: "70",
  current_weight: "178",
  estimated_bf: "16",
  goals: ["Build strength", "Recomposition"],
  frequency: 5,
  equipment: ["Barbell", "Dumbbells"],
  existingPlan: "",
};

const WorkoutPlannerContext = createContext<WorkoutPlannerContextValue | null>(null);

export function WorkoutPlannerProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<BackendUser | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingProfile>(defaultOnboarding);
  const [regimen, setRegimen] = useState<Regimen | null>(null);
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [selectedDayId, setSelectedDayId] = useState("day-1");
  const [exerciseLogs, setExerciseLogs] = useState<Record<number, ExerciseLog>>({});
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [onboardingComplete, setOnboardingComplete] = useState(false);

  useEffect(() => {
    async function hydrateMocks() {
      const [mockUser, mockWorkouts] = await Promise.all([getMockUser(), getMockWorkouts()]);
      setUser(mockUser);
      setWorkouts(mockWorkouts);
    }

    hydrateMocks();
  }, []);

  const selectedDay = regimen?.plan.days.find((day) => day.id === selectedDayId) ?? regimen?.plan.days[0] ?? null;

  const currentWorkout = selectedDay?.workout_id
    ? workouts.find((workout) => workout.id === selectedDay.workout_id) ?? null
    : null;

  useEffect(() => {
    if (!currentWorkout) {
      return;
    }

    setExerciseLogs((previous) => {
      const next = { ...previous };
      currentWorkout.exercises.forEach((exercise) => {
        if (!next[exercise.id]) {
          next[exercise.id] = {
            exerciseId: exercise.id,
            actualReps: String(exercise.reps),
            actualWeight: String(exercise.weight),
            complete: false,
          };
        }
      });
      return next;
    });
  }, [currentWorkout]);

  const completionRatio = (() => {
    if (!currentWorkout || currentWorkout.exercises.length === 0) {
      return 0;
    }
    const completed = currentWorkout.exercises.filter((exercise) => exerciseLogs[exercise.id]?.complete).length;
    return completed / currentWorkout.exercises.length;
  })();

  const setBiometricField: WorkoutPlannerContextValue["setBiometricField"] = (field, value) => {
    setOnboarding((previous) => ({ ...previous, [field]: value }));
  };

  const toggleGoal = (goal: string) => {
    setOnboarding((previous) => ({
      ...previous,
      goals: previous.goals.includes(goal) ? previous.goals.filter((item) => item !== goal) : [...previous.goals, goal],
    }));
  };

  const setFrequency = (frequency: number) => {
    setOnboarding((previous) => ({ ...previous, frequency }));
  };

  const toggleEquipment = (equipment: string) => {
    setOnboarding((previous) => ({
      ...previous,
      equipment: previous.equipment.includes(equipment)
        ? previous.equipment.filter((item) => item !== equipment)
        : [...previous.equipment, equipment],
    }));
  };

  const setExistingPlan = (value: string) => {
    setOnboarding((previous) => ({ ...previous, existingPlan: value }));
  };

  const generateRegimenFromText = async () => {
    setIsAiProcessing(true);
    const mockRegimen = await getMockRegimen();
    setRegimen(mockRegimen);
    setSelectedDayId(mockRegimen.plan.days[0]?.id ?? "day-1");
    setOnboardingComplete(true);
    setIsAiProcessing(false);
  };

  const fetchWorkoutById = async (id: number) => {
    const workout = await getMockWorkoutById(id);
    if (workout && !workouts.some((item) => item.id === workout.id)) {
      setWorkouts((previous) => [...previous, workout]);
    }
    return workout;
  };

  const updateExerciseLog: WorkoutPlannerContextValue["updateExerciseLog"] = (exerciseId, updates) => {
    setExerciseLogs((previous) => ({
      ...previous,
      [exerciseId]: {
        exerciseId,
        actualReps: previous[exerciseId]?.actualReps ?? "",
        actualWeight: previous[exerciseId]?.actualWeight ?? "",
        complete: previous[exerciseId]?.complete ?? false,
        ...updates,
      },
    }));
  };

  const completeWorkout = async () => {
    setIsAiProcessing(true);
    await new Promise((resolve) => setTimeout(resolve, 900));
    if (currentWorkout) {
      setExerciseLogs((previous) => {
        const next = { ...previous };
        currentWorkout.exercises.forEach((exercise) => {
          next[exercise.id] = {
            exerciseId: exercise.id,
            actualReps: previous[exercise.id]?.actualReps ?? String(exercise.reps),
            actualWeight: previous[exercise.id]?.actualWeight ?? String(exercise.weight),
            complete: true,
          };
        });
        return next;
      });
    }
    setIsAiProcessing(false);
  };

  const tweakPlanWithFeedback = async (_feedback: string) => {
    setIsAiProcessing(true);
    const replacement = await getMockReplacementRegimen();
    setRegimen(replacement);
    setSelectedDayId(replacement.plan.days[0]?.id ?? "day-1");
    setIsAiProcessing(false);
  };

  return (
    <WorkoutPlannerContext.Provider
      value={{
        user,
        onboarding,
        regimen,
        workouts,
        selectedDayId,
        selectedDay,
        currentWorkout,
        exerciseLogs,
        isAiProcessing,
        onboardingComplete,
        completionRatio,
        setBiometricField,
        toggleGoal,
        setFrequency,
        toggleEquipment,
        setExistingPlan,
        setSelectedDayId,
        generateRegimenFromText,
        fetchWorkoutById,
        updateExerciseLog,
        completeWorkout,
        tweakPlanWithFeedback,
      }}
    >
      {children}
    </WorkoutPlannerContext.Provider>
  );
}

export function useWorkoutPlanner() {
  const context = useContext(WorkoutPlannerContext);
  if (!context) {
    throw new Error("useWorkoutPlanner must be used inside WorkoutPlannerProvider");
  }
  return context;
}
