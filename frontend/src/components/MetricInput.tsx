import React from "react";
import { Text, TextInput, TextInputProps, View } from "react-native";

interface MetricInputProps extends TextInputProps {
  label: string;
  unit?: string;
}

export function MetricInput({ label, unit, className, ...props }: MetricInputProps) {
  return (
    <View className="mb-4">
      <Text className="mb-2 text-sm font-semibold text-slate-700">{label}</Text>
      <View className="flex-row items-center rounded-2xl border border-slate-200 bg-white px-4">
        <TextInput
          className={`min-h-14 flex-1 text-lg font-semibold text-ink ${className ?? ""}`}
          keyboardType="numeric"
          placeholderTextColor="#94a3b8"
          {...props}
        />
        {unit ? <Text className="ml-3 text-sm font-semibold text-muted">{unit}</Text> : null}
      </View>
    </View>
  );
}
