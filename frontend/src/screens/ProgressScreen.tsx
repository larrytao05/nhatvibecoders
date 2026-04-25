import React from "react";
import { ScrollView, Text, View } from "react-native";
import { ProgressBar } from "../components/ProgressBar";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

export function ProgressScreen() {
  const { user, regimen, completionRatio } = useWorkoutPlanner();

  return (
    <ScrollView className="flex-1 bg-surface" contentContainerClassName="px-5 pb-10 pt-14">
      <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Progress</Text>
      <Text className="mt-2 text-4xl font-black text-ink">Health metrics and AI insights</Text>
      <Text className="mt-3 text-base leading-6 text-muted">
        Placeholder dashboard for future body metrics, lift logs, adherence, and model-generated recommendations.
      </Text>

      <View className="mt-6 rounded-3xl bg-white p-5">
        <Text className="text-xs font-black uppercase tracking-[2px] text-muted">Profile Snapshot</Text>
        <View className="mt-4 flex-row justify-between">
          <Metric label="Weight" value={`${user?.current_weight ?? "--"} lb`} />
          <Metric label="Height" value={`${user?.height ?? "--"} in`} />
          <Metric label="BF est." value={`${user?.estimated_bf ?? "--"}%`} />
        </View>
      </View>

      <View className="mt-5 rounded-3xl bg-white p-5">
        <View className="flex-row items-center justify-between">
          <Text className="font-black text-ink">Today adherence</Text>
          <Text className="font-black text-brand">{Math.round(completionRatio * 100)}%</Text>
        </View>
        <View className="mt-4">
          <ProgressBar value={completionRatio} />
        </View>
      </View>

      <View className="mt-5 rounded-3xl bg-ink p-5">
        <Text className="text-xs font-black uppercase tracking-[2px] text-blue-200">AI Insight</Text>
        <Text className="mt-3 text-xl font-black text-white">{regimen?.theme ?? "adaptive plan"}</Text>
        <Text className="mt-2 text-sm leading-6 text-slate-300">
          Once real logs are available, this area can summarize fatigue, progression, and likely plan tweaks.
        </Text>
      </View>
    </ScrollView>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <View>
      <Text className="text-xs font-bold uppercase tracking-wide text-muted">{label}</Text>
      <Text className="mt-1 text-lg font-black text-ink">{value}</Text>
    </View>
  );
}
