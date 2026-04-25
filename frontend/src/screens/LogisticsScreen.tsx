import React from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

const equipmentOptions = ["Barbell", "Dumbbells", "Cables", "Machines", "Pull-up bar", "Bands"];

export function LogisticsScreen() {
  const { onboarding, setFrequency, toggleEquipment, setExistingPlan, generateRegimenFromText, generationError } = useWorkoutPlanner();

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} className="flex-1 bg-surface">
      <ScrollView contentContainerClassName="px-5 pb-8 pt-16">
        <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Constraints</Text>
        <Text className="mt-3 text-4xl font-black leading-tight text-ink">Tell the AI what real life allows.</Text>
        <Text className="mt-3 text-base leading-6 text-muted">
          Pasting an existing routine triggers the simulated LLM call and hydrates the regimen JSON.
        </Text>

        <View className="mt-8 rounded-3xl bg-white p-5">
          <View className="flex-row items-center justify-between">
            <Text className="text-lg font-black text-ink">Training frequency</Text>
            <Text className="text-lg font-black text-brand">{onboarding.frequency}x/week</Text>
          </View>
          <View className="mt-5 flex-row justify-between">
            {[2, 3, 4, 5, 6, 7].map((value) => (
              <Pressable key={value} onPress={() => setFrequency(value)} className="items-center">
                <View className={`h-4 w-4 rounded-full ${onboarding.frequency >= value ? "bg-brand" : "bg-slate-300"}`} />
                <Text className="mt-2 text-xs font-bold text-muted">{value}</Text>
              </Pressable>
            ))}
          </View>
          <View className="mt-3 h-2 rounded-full bg-slate-200">
            <View className="h-2 rounded-full bg-brand" style={{ width: `${((onboarding.frequency - 2) / 5) * 100}%` }} />
          </View>
        </View>

        <View className="mt-5 rounded-3xl bg-white p-5">
          <Text className="text-lg font-black text-ink">Equipment</Text>
          <View className="mt-4 gap-3">
            {equipmentOptions.map((equipment) => {
              const checked = onboarding.equipment.includes(equipment);
              return (
                <Pressable key={equipment} onPress={() => toggleEquipment(equipment)} className="flex-row items-center">
                  <View className={`mr-3 h-6 w-6 items-center justify-center rounded-lg ${checked ? "bg-brand" : "bg-slate-200"}`}>
                    <Text className="text-xs font-black text-white">{checked ? "✓" : ""}</Text>
                  </View>
                  <Text className="font-semibold text-slate-700">{equipment}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <View className="mt-5 rounded-3xl bg-white p-5">
          <Text className="text-lg font-black text-ink">Existing Plan</Text>
          <TextInput
            multiline
            textAlignVertical="top"
            value={onboarding.existingPlan}
            onChangeText={setExistingPlan}
            placeholder="Paste your previous program, notes, injuries, or routine here..."
            placeholderTextColor="#94a3b8"
            className="mt-4 min-h-40 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-base leading-6 text-ink"
          />
        </View>

        <Pressable onPress={generateRegimenFromText} className="mt-6 rounded-2xl bg-ink px-5 py-4">
          <Text className="text-center text-lg font-black text-white">Generate Workout Plan</Text>
        </Pressable>
        {generationError ? (
          <Text className="mt-3 text-center text-sm font-semibold leading-5 text-red-600">{generationError}</Text>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
