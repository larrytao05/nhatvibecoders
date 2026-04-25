import React from "react";
import { ActivityIndicator, Modal, Text, View } from "react-native";

export function AiProcessingOverlay({ visible }: { visible: boolean }) {
  return (
    <Modal visible={visible} transparent animationType="fade">
      <View className="flex-1 items-center justify-center bg-slate-950/60 px-8">
        <View className="w-full rounded-3xl bg-white p-6">
          <ActivityIndicator color="#2563eb" size="large" />
          <Text className="mt-4 text-center text-xl font-black text-ink">AI Processing...</Text>
          <Text className="mt-2 text-center text-sm leading-5 text-muted">
            Generating personalized workout plan...
          </Text>
        </View>
      </View>
    </Modal>
  );
}
