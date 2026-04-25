import React from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { Exercise, ExerciseLog } from "../types/planning";

interface ExerciseCardProps {
  exercise: Exercise;
  log: ExerciseLog | undefined;
  onChange: (updates: Partial<ExerciseLog>) => void;
}

export function ExerciseCard({ exercise, log, onChange }: ExerciseCardProps) {
  const complete = log?.complete ?? false;

  return (
    <View className="mb-4 rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
      <View className="flex-row items-start justify-between gap-3">
        <View className="flex-1">
          <Text className="text-lg font-black text-ink">{exercise.name}</Text>
          <Text className="mt-1 text-sm text-muted">{exercise.muscles_worked}</Text>
        </View>
        <Pressable
          accessibilityRole="checkbox"
          accessibilityState={{ checked: complete }}
          onPress={() => onChange({ complete: !complete })}
          className={`h-8 w-8 items-center justify-center rounded-full border ${
            complete ? "border-emerald-500 bg-emerald-500" : "border-slate-300 bg-white"
          }`}
        >
          <Text className="font-black text-white">{complete ? "✓" : ""}</Text>
        </Pressable>
      </View>

      <View className="mt-4 flex-row rounded-2xl bg-slate-50 p-3">
        <View className="flex-1">
          <Text className="text-xs font-bold uppercase tracking-wide text-muted">Planned</Text>
          <Text className="mt-1 font-black text-ink">
            {exercise.sets} x {exercise.reps} @ {exercise.weight} lb
          </Text>
          <Text className="mt-1 text-xs text-muted">{exercise.rest_time}s rest</Text>
        </View>
        <View className="flex-1">
          <Text className="text-xs font-bold uppercase tracking-wide text-muted">Actual</Text>
          <View className="mt-2 flex-row gap-2">
            <TextInput
              className="h-11 flex-1 rounded-xl border border-slate-200 bg-white px-3 text-center font-bold text-ink"
              keyboardType="numeric"
              value={log?.actualReps ?? String(exercise.reps)}
              onChangeText={(actualReps) => onChange({ actualReps })}
            />
            <TextInput
              className="h-11 flex-1 rounded-xl border border-slate-200 bg-white px-3 text-center font-bold text-ink"
              keyboardType="numeric"
              value={log?.actualWeight ?? String(exercise.weight)}
              onChangeText={(actualWeight) => onChange({ actualWeight })}
            />
          </View>
          <Text className="mt-1 text-xs text-muted">reps / weight</Text>
        </View>
      </View>
    </View>
  );
}
