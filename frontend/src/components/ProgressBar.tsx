import React from "react";
import { DimensionValue, View } from "react-native";

interface ProgressBarProps {
  value: number;
}

export function ProgressBar({ value }: ProgressBarProps) {
  const width = `${Math.max(0, Math.min(value, 1)) * 100}%` as DimensionValue;

  return (
    <View className="h-3 overflow-hidden rounded-full bg-slate-200">
      <View className="h-full rounded-full bg-brand" style={{ width }} />
    </View>
  );
}
