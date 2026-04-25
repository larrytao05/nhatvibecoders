import { NativeStackScreenProps } from "@react-navigation/native-stack";
import React from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { OnboardingStackParamList } from "../navigation/types";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

const goals = ["Build strength", "Recomposition", "Hypertrophy", "Improve conditioning", "Fix weak points", "Stay pain-free"];

type Props = NativeStackScreenProps<OnboardingStackParamList, "Goals">;

export function GoalsScreen({ navigation }: Props) {
  const { onboarding, toggleGoal } = useWorkoutPlanner();

  return (
    <ScrollView className="flex-1 bg-surface" contentContainerClassName="px-5 pb-8 pt-16">
      <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Objectives</Text>
      <Text className="mt-3 text-4xl font-black leading-tight text-ink">What should the plan optimize for?</Text>

      <View className="mt-8 flex-row flex-wrap gap-3">
        {goals.map((goal) => {
          const selected = onboarding.goals.includes(goal);
          return (
            <Pressable
              key={goal}
              onPress={() => toggleGoal(goal)}
              className={`rounded-full border px-5 py-3 ${
                selected ? "border-brand bg-blue-50" : "border-slate-200 bg-white"
              }`}
            >
              <Text className={`font-bold ${selected ? "text-brand" : "text-slate-700"}`}>{goal}</Text>
            </Pressable>
          );
        })}
      </View>

      <Pressable onPress={() => navigation.navigate("Logistics")} className="mt-10 rounded-2xl bg-brand px-5 py-4">
        <Text className="text-center text-lg font-black text-white">Continue</Text>
      </Pressable>
    </ScrollView>
  );
}
