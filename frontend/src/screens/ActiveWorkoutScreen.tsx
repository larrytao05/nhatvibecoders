import React, { useEffect, useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { ExerciseCard } from "../components/ExerciseCard";
import { ProgressBar } from "../components/ProgressBar";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

export function ActiveWorkoutScreen() {
  const {
    selectedDay,
    currentWorkout,
    exerciseLogs,
    completionRatio,
    fetchWorkoutById,
    updateExerciseLog,
    completeWorkout,
  } = useWorkoutPlanner();
  const [feedbackVisible, setFeedbackVisible] = useState(false);

  useEffect(() => {
    if (selectedDay?.workout_id) {
      fetchWorkoutById(selectedDay.workout_id);
    }
  }, [fetchWorkoutById, selectedDay?.workout_id]);

  const finishWorkout = async () => {
    await completeWorkout({
      overallFeel: 3,
      concerns: [],
      notes: "Completed from active workout screen.",
    });
    setFeedbackVisible(true);
  };

  if (!currentWorkout) {
    return (
      <View className="flex-1 items-center justify-center bg-surface px-6">
        <Text className="text-center text-3xl font-black text-ink">{selectedDay?.title ?? "Rest Day"}</Text>
        <Text className="mt-3 text-center text-base leading-6 text-muted">
          No exercise list is mapped to this regimen day. Use the schedule to pick a lifting day.
        </Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-surface">
      <ScrollView contentContainerClassName="px-5 pb-32 pt-14">
        <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Active Workout</Text>
        <Text className="mt-2 text-4xl font-black text-ink">{selectedDay?.title}</Text>
        <Text className="mt-2 text-base leading-6 text-muted">{currentWorkout.muscles_worked}</Text>

        <View className="mt-6 rounded-3xl bg-white p-5">
          <View className="mb-3 flex-row items-center justify-between">
            <Text className="font-black text-ink">Completion</Text>
            <Text className="font-black text-brand">{Math.round(completionRatio * 100)}%</Text>
          </View>
          <ProgressBar value={completionRatio} />
        </View>

        <View className="mt-5">
          {currentWorkout.exercises.map((exercise) => (
            <ExerciseCard
              key={exercise.id}
              exercise={exercise}
              log={exerciseLogs[exercise.id]}
              onChange={(updates) => updateExerciseLog(exercise.id, updates)}
            />
          ))}
        </View>
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 border-t border-slate-200 bg-white px-5 pb-8 pt-4">
        <Pressable onPress={finishWorkout} className="rounded-2xl bg-brand px-5 py-4">
          <Text className="text-center text-lg font-black text-white">Complete Workout</Text>
        </Pressable>
      </View>

      <Modal visible={feedbackVisible} transparent animationType="fade">
        <View className="flex-1 justify-end bg-slate-950/50">
          <View className="rounded-t-[32px] bg-white px-5 pb-10 pt-6">
            <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Phase 4 Feedback</Text>
            <Text className="mt-3 text-3xl font-black text-ink">AI coach summary</Text>
            <Text className="mt-3 text-base leading-6 text-muted">
              Great adherence. The mock model would now compare planned versus actual reps and loads, then adjust next week
              if performance trends above or below target.
            </Text>
            <Pressable onPress={() => setFeedbackVisible(false)} className="mt-6 rounded-2xl bg-ink px-5 py-4">
              <Text className="text-center text-lg font-black text-white">Back to Plan</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}
