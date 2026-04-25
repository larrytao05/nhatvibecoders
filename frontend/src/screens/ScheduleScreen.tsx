import React, { useState } from "react";
import { Modal, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

export function ScheduleScreen() {
  const { regimen, workouts, selectedDayId, setSelectedDayId, tweakPlanWithFeedback } = useWorkoutPlanner();
  const [expandedDayId, setExpandedDayId] = useState(selectedDayId);
  const [feedbackVisible, setFeedbackVisible] = useState(false);
  const [feedback, setFeedback] = useState("My shoulders are irritated. Reduce pressing fatigue and add more recovery.");

  const submitFeedback = async () => {
    setFeedbackVisible(false);
    await tweakPlanWithFeedback(feedback);
  };

  return (
    <View className="flex-1 bg-surface">
      <ScrollView contentContainerClassName="px-5 pb-28 pt-14">
        <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Regimen</Text>
        <Text className="mt-2 text-4xl font-black text-ink">{regimen?.name ?? "No plan yet"}</Text>
        <Text className="mt-3 text-base leading-6 text-muted">{regimen?.description}</Text>

        <View className="mt-6 gap-4">
          {regimen?.plan.days.map((day) => {
            const expanded = expandedDayId === day.id;
            const workout = day.workout_id ? workouts.find((item) => item.id === day.workout_id) : null;
            const active = selectedDayId === day.id;

            return (
              <Pressable
                key={day.id}
                onPress={() => {
                  setExpandedDayId(expanded ? "" : day.id);
                  setSelectedDayId(day.id);
                }}
                className={`rounded-3xl border p-5 ${active ? "border-brand bg-blue-50" : "border-slate-200 bg-white"}`}
              >
                <View className="flex-row items-start justify-between gap-4">
                  <View className="flex-1">
                    <Text className="text-xs font-black uppercase tracking-[2px] text-muted">Day {day.day_index}</Text>
                    <Text className="mt-1 text-xl font-black text-ink">{day.title}</Text>
                    <Text className="mt-2 text-sm leading-5 text-slate-600">{day.focus}</Text>
                  </View>
                  <View className="rounded-full bg-white px-3 py-2">
                    <Text className="text-xs font-black text-brand">{day.intensity}</Text>
                  </View>
                </View>

                {expanded ? (
                  <View className="mt-5 rounded-2xl bg-white/80 p-4">
                    <Text className="font-black text-ink">Phase 2 workout list</Text>
                    {workout ? (
                      <View className="mt-3 gap-2">
                        {workout.exercises.map((exercise) => (
                          <View key={exercise.id} className="flex-row justify-between rounded-xl bg-slate-50 px-3 py-2">
                            <Text className="flex-1 font-semibold text-slate-700">{exercise.name}</Text>
                            <Text className="font-bold text-muted">
                              {exercise.sets}x{exercise.reps}
                            </Text>
                          </View>
                        ))}
                      </View>
                    ) : (
                      <Text className="mt-2 text-sm text-muted">{day.notes}</Text>
                    )}
                  </View>
                ) : null}
              </Pressable>
            );
          })}
        </View>
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 border-t border-slate-200 bg-white px-5 pb-8 pt-4">
        <Pressable onPress={() => setFeedbackVisible(true)} className="rounded-2xl bg-ink px-5 py-4">
          <Text className="text-center text-lg font-black text-white">Tweak this Plan</Text>
        </Pressable>
      </View>

      <Modal visible={feedbackVisible} animationType="slide" presentationStyle="pageSheet">
        <View className="flex-1 bg-surface px-5 pb-8 pt-16">
          <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Feedback Loop</Text>
          <Text className="mt-3 text-3xl font-black text-ink">Send the full JSON plus your notes.</Text>
          <View className="mt-6 rounded-3xl bg-white p-5">
            <Text className="text-xs font-black uppercase tracking-[2px] text-muted">Current payload preview</Text>
            <Text className="mt-3 text-sm leading-5 text-slate-600" numberOfLines={5}>
              {JSON.stringify(regimen, null, 2)}
            </Text>
          </View>
          <TextInput
            multiline
            value={feedback}
            onChangeText={setFeedback}
            className="mt-5 min-h-36 rounded-3xl border border-slate-200 bg-white p-5 text-base leading-6 text-ink"
          />
          <Pressable onPress={submitFeedback} className="mt-auto rounded-2xl bg-brand px-5 py-4">
            <Text className="text-center text-lg font-black text-white">Simulate AI Replacement JSON</Text>
          </Pressable>
          <Pressable onPress={() => setFeedbackVisible(false)} className="mt-3 px-5 py-3">
            <Text className="text-center font-bold text-muted">Cancel</Text>
          </Pressable>
        </View>
      </Modal>
    </View>
  );
}
