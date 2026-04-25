import React from "react";
import { ScrollView, Text, View } from "react-native";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

export function ProfileScreen() {
  const { user, onboarding, regimen, exerciseLogs } = useWorkoutPlanner();
  const completedExercises = Object.values(exerciseLogs).filter((log) => log.complete).length;

  return (
    <ScrollView className="flex-1 bg-surface" contentContainerClassName="px-5 pb-10 pt-14">
      <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Profile</Text>
      <Text className="mt-2 text-4xl font-black text-ink">My data</Text>

      <View className="mt-6 rounded-3xl bg-ink p-5">
        <Text className="text-xs font-black uppercase tracking-[2px] text-blue-200">Backend User</Text>
        <Text className="mt-3 text-2xl font-black text-white">{user?.username ?? "demo-athlete"}</Text>
        <Text className="mt-2 text-sm text-slate-300">{user?.email ?? "No email on file"}</Text>
        <View className="mt-5 flex-row justify-between">
          <ProfileMetric label="Weight" value={`${user?.current_weight ?? onboarding.current_weight} lb`} light />
          <ProfileMetric label="Height" value={`${user?.height ?? onboarding.height} in`} light />
          <ProfileMetric label="BF est." value={`${user?.estimated_bf ?? onboarding.estimated_bf}%`} light />
        </View>
      </View>

      <View className="mt-5 rounded-3xl bg-white p-5">
        <Text className="text-xs font-black uppercase tracking-[2px] text-muted">User-Originated Inputs</Text>
        <DataRow label="Goals" value={onboarding.goals.join(", ") || "None selected"} />
        <DataRow label="Frequency" value={`${onboarding.frequency} days/week`} />
        <DataRow label="Equipment" value={onboarding.equipment.join(", ") || "None selected"} />
        <DataRow label="Existing Plan" value={onboarding.existingPlan || "No pasted plan yet"} />
      </View>

      <View className="mt-5 rounded-3xl bg-white p-5">
        <Text className="text-xs font-black uppercase tracking-[2px] text-muted">Generated Plan Ownership</Text>
        <DataRow label="Regimen" value={regimen?.name ?? "No regimen generated"} />
        <DataRow label="Theme" value={regimen?.theme ?? "None"} />
        <DataRow label="Plan Days" value={`${regimen?.plan.days.length ?? 0}`} />
        <DataRow label="Logged Exercises" value={`${completedExercises}`} />
      </View>

      <View className="mt-5 rounded-3xl bg-white p-5">
        <Text className="text-xs font-black uppercase tracking-[2px] text-muted">Raw Profile Payload</Text>
        <Text className="mt-3 rounded-2xl bg-slate-50 p-4 font-mono text-xs leading-5 text-slate-700">
          {JSON.stringify(
            {
              user,
              onboarding,
              completed_exercises: completedExercises,
            },
            null,
            2,
          )}
        </Text>
      </View>
    </ScrollView>
  );
}

function ProfileMetric({ label, value, light }: { label: string; value: string; light?: boolean }) {
  return (
    <View>
      <Text className={`text-xs font-bold uppercase tracking-wide ${light ? "text-blue-200" : "text-muted"}`}>{label}</Text>
      <Text className={`mt-1 text-lg font-black ${light ? "text-white" : "text-ink"}`}>{value}</Text>
    </View>
  );
}

function DataRow({ label, value }: { label: string; value: string }) {
  return (
    <View className="mt-4 border-t border-slate-100 pt-4">
      <Text className="text-xs font-bold uppercase tracking-wide text-muted">{label}</Text>
      <Text className="mt-1 text-base font-bold leading-6 text-ink">{value}</Text>
    </View>
  );
}
