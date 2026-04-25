import React, { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { ExerciseCard } from "../components/ExerciseCard";
import { ProgressBar } from "../components/ProgressBar";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

export function WorkoutsScreen() {
  const {
    regimen,
    workouts,
    selectedDay,
    currentWorkout,
    selectedDayId,
    setSelectedDayId,
    exerciseLogs,
    completionRatio,
    updateExerciseLog,
    completeWorkout,
  } = useWorkoutPlanner();
  const [feedbackVisible, setFeedbackVisible] = useState(false);

  const finishWorkout = async () => {
    await completeWorkout();
    setFeedbackVisible(true);
  };

  const upcomingDays = regimen?.plan.days.filter((day) => day.id !== selectedDayId).slice(0, 5) ?? [];

  return (
    <View className="flex-1 bg-surface">
      <ScrollView contentContainerClassName="px-5 pb-32 pt-14">
        <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Workouts</Text>
        <Text className="mt-2 text-4xl font-black text-ink">Today and what&apos;s next</Text>
        <Text className="mt-3 text-base leading-6 text-muted">
          Today stays pinned to the top, followed by the next training days and planning metrics.
        </Text>

        <View className="mt-6 rounded-3xl border border-brand bg-blue-50 p-5">
          <View className="flex-row items-start justify-between gap-4">
            <View className="flex-1">
              <Text className="text-xs font-black uppercase tracking-[2px] text-brand">Today</Text>
              <Text className="mt-2 text-2xl font-black text-ink">{selectedDay?.title ?? "No workout selected"}</Text>
              <Text className="mt-2 text-sm leading-5 text-slate-600">{selectedDay?.focus}</Text>
            </View>
            <Text className="rounded-full bg-white px-3 py-2 text-xs font-black text-brand">
              {selectedDay?.intensity ?? "Plan"}
            </Text>
          </View>

          <View className="mt-5">
            <View className="mb-3 flex-row items-center justify-between">
              <Text className="font-black text-ink">Logged progress</Text>
              <Text className="font-black text-brand">{Math.round(completionRatio * 100)}%</Text>
            </View>
            <ProgressBar value={completionRatio} />
          </View>
        </View>

        {currentWorkout ? (
          <View className="mt-5">
            {currentWorkout.exercises.map((exercise) => (
              <ExerciseCard
                key={exercise.id}
                exercise={exercise}
                log={exerciseLogs[exercise.id]}
                onChange={(updates) => updateExerciseLog(exercise.id, updates)}
              />
            ))}
            <Pressable onPress={finishWorkout} className="mt-1 rounded-2xl bg-brand px-5 py-4">
              <Text className="text-center text-lg font-black text-white">Complete Workout</Text>
            </Pressable>
          </View>
        ) : (
          <View className="mt-5 rounded-3xl bg-white p-5">
            <Text className="text-xl font-black text-ink">Recovery day</Text>
            <Text className="mt-2 text-sm leading-5 text-muted">{selectedDay?.notes ?? "No lift scheduled."}</Text>
          </View>
        )}

        <View className="mt-8">
          <Text className="text-xl font-black text-ink">Next days</Text>
          <View className="mt-4 gap-3">
            {upcomingDays.map((day) => {
              const workout = day.workout_id ? workouts.find((item) => item.id === day.workout_id) : null;
              return (
                <Pressable
                  key={day.id}
                  onPress={() => setSelectedDayId(day.id)}
                  className="rounded-3xl border border-slate-200 bg-white p-4"
                >
                  <View className="flex-row items-center justify-between">
                    <View className="flex-1 pr-3">
                      <Text className="text-xs font-black uppercase tracking-[2px] text-muted">Day {day.day_index}</Text>
                      <Text className="mt-1 text-lg font-black text-ink">{day.title}</Text>
                      <Text className="mt-1 text-sm text-muted" numberOfLines={2}>
                        {workout ? `${workout.exercises.length} exercises • ${workout.muscles_worked}` : day.notes}
                      </Text>
                    </View>
                    <Text className="rounded-full bg-slate-100 px-3 py-2 text-xs font-black text-slate-600">{day.intensity}</Text>
                  </View>
                </Pressable>
              );
            })}
          </View>
        </View>

        <View className="mt-8 rounded-3xl bg-white p-5">
          <Text className="text-xl font-black text-ink">Calendar view</Text>
          <View className="mt-4 flex-row justify-between">
            {regimen?.plan.days.map((day) => (
              <Pressable key={day.id} onPress={() => setSelectedDayId(day.id)} className="items-center">
                <View
                  className={`h-12 w-10 items-center justify-center rounded-2xl ${
                    day.id === selectedDayId ? "bg-brand" : day.workout_id ? "bg-blue-50" : "bg-slate-100"
                  }`}
                >
                  <Text className={`font-black ${day.id === selectedDayId ? "text-white" : "text-slate-700"}`}>
                    {day.day_index}
                  </Text>
                </View>
                <View className={`mt-2 h-1.5 w-1.5 rounded-full ${day.workout_id ? "bg-brand" : "bg-slate-300"}`} />
              </Pressable>
            ))}
          </View>
        </View>

        <View className="mt-5 rounded-3xl bg-white p-5">
          <Text className="text-xl font-black text-ink">Metric chart</Text>
          <Text className="mt-1 text-sm text-muted">Planned volume by upcoming day</Text>
          <View className="mt-5 flex-row items-end justify-between">
            {regimen?.plan.days.map((day) => {
              const workout = day.workout_id ? workouts.find((item) => item.id === day.workout_id) : null;
              const volume = workout?.exercises.reduce((total, exercise) => total + exercise.sets * exercise.reps, 0) ?? 8;
              const height = Math.min(120, 28 + volume);
              return (
                <View key={day.id} className="items-center">
                  <View className="w-7 rounded-t-xl bg-brand" style={{ height }} />
                  <Text className="mt-2 text-xs font-bold text-muted">D{day.day_index}</Text>
                </View>
              );
            })}
          </View>
        </View>
      </ScrollView>

      <Modal visible={feedbackVisible} transparent animationType="fade">
        <View className="flex-1 justify-end bg-slate-950/50">
          <View className="rounded-t-[32px] bg-white px-5 pb-10 pt-6">
            <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Workout Recap</Text>
            <Text className="mt-3 text-3xl font-black text-ink">Workout complete</Text>
            <Text className="mt-3 text-base leading-6 text-muted">
              Planned versus actual reps and loads are saved in local state and ready for the AI feedback loop.
            </Text>
            <Pressable onPress={() => setFeedbackVisible(false)} className="mt-6 rounded-2xl bg-ink px-5 py-4">
              <Text className="text-center text-lg font-black text-white">Close Recap</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}
