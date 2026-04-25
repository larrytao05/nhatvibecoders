import { NativeStackScreenProps } from "@react-navigation/native-stack";
import React from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { MetricInput } from "../components/MetricInput";
import { OnboardingStackParamList } from "../navigation/types";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

type Props = NativeStackScreenProps<OnboardingStackParamList, "Biometrics">;

export function BiometricsScreen({ navigation }: Props) {
  const { onboarding, setBiometricField } = useWorkoutPlanner();

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} className="flex-1 bg-surface">
      <ScrollView contentContainerClassName="flex-grow px-5 pb-8 pt-16">
        <Text className="text-sm font-black uppercase tracking-[3px] text-brand">HTP Setup</Text>
        <Text className="mt-3 text-4xl font-black leading-tight text-ink">Start with your current body metrics.</Text>
        <Text className="mt-3 text-base leading-6 text-muted">
          These mirror the backend `users` table so the real profile endpoint can drop in later.
        </Text>

        <View className="mt-8">
          <MetricInput
            label="Height"
            unit="in"
            value={onboarding.height}
            onChangeText={(value) => setBiometricField("height", value)}
          />
          <MetricInput
            label="Weight"
            unit="lb"
            value={onboarding.current_weight}
            onChangeText={(value) => setBiometricField("current_weight", value)}
          />
          <MetricInput
            label="Body Fat Estimate"
            unit="%"
            value={onboarding.estimated_bf}
            onChangeText={(value) => setBiometricField("estimated_bf", value)}
          />
        </View>

        <Pressable onPress={() => navigation.navigate("Goals")} className="mt-auto rounded-2xl bg-brand px-5 py-4">
          <Text className="text-center text-lg font-black text-white">Continue</Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
