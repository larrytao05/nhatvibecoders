import AsyncStorage from "@react-native-async-storage/async-storage";
import React, { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";
import {
  createUser,
  createRegimenSkeleton,
  DEFAULT_USERNAME,
  decideNextWorkoutSuggestion,
  expandRegimenDay,
  getLatestRegimen,
  getUser,
  getUserWorkouts,
  logWorkout,
  requestRegimenTweak,
  requestWorkoutCompletion,
} from "../api/backend";
import { getMockRegimen, getMockWorkoutById, getMockWorkouts } from "../mocks/api";
import {
  BackendUser,
  ExerciseLog,
  OnboardingProfile,
  Regimen,
  RegimenDay,
  Workout,
  WorkoutCompletionSuggestion,
  WorkoutReviewFeedback,
} from "../types/planning";

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
  isRegimenGenerating: boolean;
  generationError: string | null;
  authComplete: boolean;
  onboardingComplete: boolean;
  completionRatio: number;
  hasWorkoutProgress: boolean;
  workoutComplete: boolean;
  expandingDayIds: string[];
  initialMainTab: "Home" | "Workouts";
  loginUser: (username: string) => Promise<void>;
  signupUser: (username: string) => Promise<void>;
  setBiometricField: (field: "height" | "current_weight" | "estimated_bf", value: string) => void;
  toggleGoal: (goal: string) => void;
  setFrequency: (frequency: number) => void;
  toggleEquipment: (equipment: string) => void;
  setExistingPlan: (value: string) => void;
  setSelectedDayId: (dayId: string) => void;
  generateRegimenFromText: () => Promise<void>;
  fetchWorkoutById: (id: number) => Promise<Workout | null>;
  updateExerciseLog: (exerciseId: number, updates: Partial<ExerciseLog>) => void;
  resetWorkoutProgress: () => void;
  completeWorkout: (feedback: WorkoutReviewFeedback) => Promise<WorkoutCompletionSuggestion | null>;
  decideNextWorkout: (logId: number, decision: "accept" | "reject") => Promise<Workout | null>;
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

function getTodayKey() {
  return new Date().toISOString().slice(0, 10);
}

export function WorkoutPlannerProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<BackendUser | null>(null);
  const [onboarding, setOnboarding] = useState<OnboardingProfile>(defaultOnboarding);
  const [regimen, setRegimen] = useState<Regimen | null>(null);
  const [workouts, setWorkouts] = useState<Workout[]>([]);
  const [selectedDayId, setSelectedDayId] = useState("day-1");
  const [exerciseLogsByDay, setExerciseLogsByDay] = useState<Record<string, Record<number, ExerciseLog>>>({});
  const [progressHydrated, setProgressHydrated] = useState(false);
  const [expandingDayIds, setExpandingDayIds] = useState<string[]>([]);
  const [isAiProcessing, setIsAiProcessing] = useState(false);
  const [isRegimenGenerating, setIsRegimenGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [authComplete, setAuthComplete] = useState(false);
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const [initialMainTab, setInitialMainTab] = useState<"Home" | "Workouts">("Home");
  const progressStorageKey = useMemo(
    () => `workout-progress:${user?.username ?? DEFAULT_USERNAME}:${getTodayKey()}`,
    [user?.username],
  );

  useEffect(() => {
    let active = true;
    setProgressHydrated(false);

    AsyncStorage.getItem(progressStorageKey)
      .then((storedProgress) => {
        if (!active) {
          return;
        }

        setExerciseLogsByDay(storedProgress ? (JSON.parse(storedProgress) as Record<string, Record<number, ExerciseLog>>) : {});
      })
      .catch(() => {
        if (active) {
          setExerciseLogsByDay({});
        }
      })
      .finally(() => {
        if (active) {
          setProgressHydrated(true);
        }
      });

    return () => {
      active = false;
    };
  }, [progressStorageKey]);

  useEffect(() => {
    if (!progressHydrated) {
      return;
    }

    AsyncStorage.setItem(progressStorageKey, JSON.stringify(exerciseLogsByDay)).catch(() => {
      // Progress remains available in memory if local persistence is unavailable.
    });
  }, [exerciseLogsByDay, progressHydrated, progressStorageKey]);

  const finishAuth = async (authenticatedUser: BackendUser) => {
    const fallbackWorkouts = await getMockWorkouts();
    const apiWorkouts = await getUserWorkouts(authenticatedUser.username).catch(() => []);
    const latestRegimen = await getLatestRegimen(authenticatedUser.username).catch(() => null);
    const baseWorkouts = apiWorkouts.length > 0 ? apiWorkouts : fallbackWorkouts;

    setUser(authenticatedUser);
    if (latestRegimen) {
      setRegimen(latestRegimen.regimen);
      setSelectedDayId(latestRegimen.regimen.plan.days[0]?.id ?? "day-1");
      setWorkouts([
        ...latestRegimen.plannedWorkouts,
        ...baseWorkouts.filter(
          (workout) => !latestRegimen.plannedWorkouts.some((plannedWorkout) => plannedWorkout.id === workout.id),
        ),
      ]);
    } else {
      setRegimen(null);
      setWorkouts(baseWorkouts);
    }
    setAuthComplete(true);
  };

  const mergePlannedWorkouts = (plannedWorkouts: Workout[]) => {
    setWorkouts((previous) => [
      ...plannedWorkouts,
      ...previous.filter((workout) => !plannedWorkouts.some((plannedWorkout) => plannedWorkout.id === workout.id)),
    ]);
  };

  const pointRegimenDayAtWorkout = (dayTitle: string, workoutId: number) => {
    setRegimen((previous) =>
      previous
        ? {
            ...previous,
            plan: {
              days: previous.plan.days.map((day) =>
                day.title === dayTitle
                  ? {
                      ...day,
                      workout_id: workoutId,
                    }
                  : day,
              ),
            },
          }
        : previous,
    );
  };

  const generateRegimenForUsername = async (username: string, showBlockingOverlay: boolean) => {
    setIsRegimenGenerating(true);
    if (showBlockingOverlay) {
      setIsAiProcessing(true);
    }
    setGenerationError(null);
    const mockRegimen = await getMockRegimen();

    try {
      const created = await createRegimenSkeleton(username, mockRegimen, onboarding);
      setRegimen(created.regimen);
      mergePlannedWorkouts(created.plannedWorkouts);
      setSelectedDayId(created.regimen.plan.days[0]?.id ?? "day-1");
      setOnboardingComplete(true);
      if (showBlockingOverlay) {
        setIsAiProcessing(false);
      }

      const trainingDays = created.regimen.plan.days.filter((day) => day.workout_id);
      for (const day of trainingDays) {
        setExpandingDayIds((previous) => [...new Set([...previous, day.id])]);
        try {
          const expanded = await expandRegimenDay(username, created.regimen.id, day.title);
          setRegimen(expanded.regimen);
          mergePlannedWorkouts(expanded.plannedWorkouts);
        } catch (error) {
          setGenerationError(error instanceof Error ? error.message : `Could not expand ${day.title}.`);
          // Keep the skeleton visible if one day expansion fails.
        } finally {
          setExpandingDayIds((previous) => previous.filter((dayId) => dayId !== day.id));
        }
      }
    } catch (error) {
      setGenerationError(error instanceof Error ? error.message : "Could not create regimen skeleton.");
      if (showBlockingOverlay) {
        setIsAiProcessing(false);
      }
    } finally {
      setIsRegimenGenerating(false);
    }
  };

  const loginUser = async (username: string) => {
    setIsAiProcessing(true);
    try {
      setInitialMainTab("Home");
      const authenticatedUser = await getUser(username.trim(), onboarding);
      setOnboardingComplete(true);
      await finishAuth(authenticatedUser);
    } finally {
      setIsAiProcessing(false);
    }
  };

  const signupUser = async (username: string) => {
    setIsAiProcessing(true);
    try {
      const authenticatedUser = await createUser(username.trim(), null, onboarding);
      setInitialMainTab("Workouts");
      setOnboardingComplete(true);
      await finishAuth(authenticatedUser);
      setIsAiProcessing(false);
      void generateRegimenForUsername(authenticatedUser.username, false);
    } catch (error) {
      setIsAiProcessing(false);
      throw error;
    }
  };

  const selectedDay = regimen?.plan.days.find((day) => day.id === selectedDayId) ?? regimen?.plan.days[0] ?? null;

  const currentWorkout = selectedDay?.workout_id
    ? workouts.find((workout) => workout.id === selectedDay.workout_id) ?? null
    : null;
  const exerciseLogs = exerciseLogsByDay[selectedDayId] ?? {};

  useEffect(() => {
    if (!currentWorkout) {
      return;
    }

    setExerciseLogsByDay((previous) => {
      const dayLogs = previous[selectedDayId] ?? {};
      const nextDayLogs = { ...dayLogs };
      currentWorkout.exercises.forEach((exercise) => {
        if (!nextDayLogs[exercise.id]) {
          nextDayLogs[exercise.id] = {
            exerciseId: exercise.id,
            actualReps: String(exercise.reps),
            actualWeight: String(exercise.weight),
            complete: false,
          };
        }
      });
      return { ...previous, [selectedDayId]: nextDayLogs };
    });
  }, [currentWorkout, selectedDayId]);

  const completionRatio = (() => {
    if (!currentWorkout || currentWorkout.exercises.length === 0) {
      return 0;
    }
    const completed = currentWorkout.exercises.filter((exercise) => exerciseLogs[exercise.id]?.complete).length;
    return completed / currentWorkout.exercises.length;
  })();
  const hasWorkoutProgress = currentWorkout
    ? currentWorkout.exercises.some((exercise) => {
        const log = exerciseLogs[exercise.id];
        return (
          Boolean(log?.complete) ||
          (log?.actualReps ?? String(exercise.reps)) !== String(exercise.reps) ||
          (log?.actualWeight ?? String(exercise.weight)) !== String(exercise.weight)
        );
      })
    : false;
  const workoutComplete = currentWorkout ? completionRatio === 1 : false;

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
    await generateRegimenForUsername(user?.username ?? DEFAULT_USERNAME, true);
  };

  const fetchWorkoutById = async (id: number) => {
    const workout = await getMockWorkoutById(id);
    if (workout && !workouts.some((item) => item.id === workout.id)) {
      setWorkouts((previous) => [...previous, workout]);
    }
    return workout;
  };

  const updateExerciseLog: WorkoutPlannerContextValue["updateExerciseLog"] = (exerciseId, updates) => {
    setExerciseLogsByDay((previous) => ({
      ...previous,
      [selectedDayId]: {
        ...(previous[selectedDayId] ?? {}),
        [exerciseId]: {
          exerciseId,
          actualReps: previous[selectedDayId]?.[exerciseId]?.actualReps ?? "",
          actualWeight: previous[selectedDayId]?.[exerciseId]?.actualWeight ?? "",
          complete: previous[selectedDayId]?.[exerciseId]?.complete ?? false,
          ...updates,
        },
      },
    }));
  };

  const resetWorkoutProgress = () => {
    setExerciseLogsByDay((previous) => {
      const next = { ...previous };
      delete next[selectedDayId];
      return next;
    });
  };

  const completeWorkout: WorkoutPlannerContextValue["completeWorkout"] = async (feedback) => {
    if (currentWorkout) {
      const username = user?.username ?? DEFAULT_USERNAME;
      let completedWorkout: Workout | null = null;

      try {
        completedWorkout = await logWorkout(username, currentWorkout, exerciseLogs);
        setWorkouts((previous) => {
          const withoutCompletedDuplicate = previous.filter((workout) => workout.id !== completedWorkout?.id);
          return completedWorkout ? [completedWorkout, ...withoutCompletedDuplicate] : previous;
        });
      } catch (error) {
        // Keep the local completion state even if the backend log call is unavailable.
      }

      setExerciseLogsByDay((previous) => {
        const dayLogs = previous[selectedDayId] ?? {};
        const nextDayLogs = { ...dayLogs };
        currentWorkout.exercises.forEach((exercise) => {
          nextDayLogs[exercise.id] = {
            exerciseId: exercise.id,
            actualReps: dayLogs[exercise.id]?.actualReps ?? String(exercise.reps),
            actualWeight: dayLogs[exercise.id]?.actualWeight ?? String(exercise.weight),
            complete: true,
          };
        });
        return { ...previous, [selectedDayId]: nextDayLogs };
      });

      if (completedWorkout && regimen && selectedDay) {
        try {
          return await requestWorkoutCompletion(username, completedWorkout.id, regimen.id, selectedDay.title, feedback);
        } catch (error) {
          setGenerationError(error instanceof Error ? error.message : "Could not generate next-workout suggestions.");
          throw error;
        }
      }
    }
    return null;
  };

  const decideNextWorkout: WorkoutPlannerContextValue["decideNextWorkout"] = async (logId, decision) => {
    const username = user?.username ?? DEFAULT_USERNAME;
    const nextWorkout = await decideNextWorkoutSuggestion(username, logId, decision);
    mergePlannedWorkouts([nextWorkout]);
    if (nextWorkout.scheduled_day) {
      pointRegimenDayAtWorkout(nextWorkout.scheduled_day, nextWorkout.id);
    }
    return nextWorkout;
  };

  const tweakPlanWithFeedback = async (feedback: string) => {
    setIsAiProcessing(true);
    setGenerationError(null);
    if (regimen) {
      try {
        const updated = await requestRegimenTweak(user?.username ?? DEFAULT_USERNAME, regimen.id, feedback);
        setRegimen(updated.regimen);
        mergePlannedWorkouts(updated.plannedWorkouts);
        setSelectedDayId((previousDayId) =>
          updated.regimen.plan.days.some((day) => day.id === previousDayId)
            ? previousDayId
            : updated.regimen.plan.days[0]?.id ?? "day-1",
        );
        setIsAiProcessing(false);
        return;
      } catch (error) {
        setGenerationError(error instanceof Error ? error.message : "Could not modify regimen.");
      }
    }

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
        isRegimenGenerating,
        generationError,
        authComplete,
        onboardingComplete,
        completionRatio,
        hasWorkoutProgress,
        workoutComplete,
        expandingDayIds,
        initialMainTab,
        loginUser,
        signupUser,
        setBiometricField,
        toggleGoal,
        setFrequency,
        toggleEquipment,
        setExistingPlan,
        setSelectedDayId,
        generateRegimenFromText,
        fetchWorkoutById,
        updateExerciseLog,
        resetWorkoutProgress,
        completeWorkout,
        decideNextWorkout,
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
