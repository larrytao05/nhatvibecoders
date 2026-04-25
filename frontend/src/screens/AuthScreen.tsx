import React, { useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, Text, TextInput, View } from "react-native";
import { API_BASE_URL } from "../api/backend";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

type AuthMode = "login" | "signup";

export function AuthScreen() {
  const { loginUser, signupUser } = useWorkoutPlanner();
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [error, setError] = useState("");

  const submit = async () => {
    const trimmedUsername = username.trim();
    setError("");

    if (!trimmedUsername) {
      setError("Enter a username to continue.");
      return;
    }

    try {
      if (mode === "login") {
        await loginUser(trimmedUsername);
      } else {
        await signupUser(trimmedUsername);
      }
    } catch (caughtError) {
      const message = caughtError instanceof Error ? caughtError.message : "Something went wrong.";
      if (mode === "signup" && message.toLowerCase().includes("already")) {
        setError("That username already exists. Switch to Log in to continue.");
      } else if (mode === "login" && message.toLowerCase().includes("not found")) {
        setError("No account found for that username. Switch to Sign up to create one.");
      } else {
        setError(message);
      }
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} className="flex-1 bg-surface px-5 pt-16">
      <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Welcome</Text>
      <Text className="mt-3 text-4xl font-black leading-tight text-ink">gAI.nz</Text>

      <View className="mt-8 flex-row rounded-2xl bg-slate-200 p-1">
        <AuthToggle label="Log in" selected={mode === "login"} onPress={() => setMode("login")} />
        <AuthToggle label="Sign up" selected={mode === "signup"} onPress={() => setMode("signup")} />
      </View>

      <View className="mt-6 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <Text className="text-xs font-black uppercase tracking-[2px] text-muted">Username</Text>
        <TextInput
          autoCapitalize="none"
          autoCorrect={false}
          value={username}
          onChangeText={setUsername}
          onSubmitEditing={submit}
          placeholder="demo-athlete"
          placeholderTextColor="#94a3b8"
          className="mt-3 min-h-14 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-lg font-bold text-ink"
        />
        {error ? <Text className="mt-3 text-sm font-semibold leading-5 text-red-600">{error}</Text> : null}

        <Pressable onPress={submit} className="mt-5 rounded-2xl bg-brand px-5 py-4">
          <Text className="text-center text-lg font-black text-white">{mode === "login" ? "Log in" : "Create user"}</Text>
        </Pressable>
      </View>

      <View className="mt-auto pb-8">
        <Text className="text-center text-xs leading-5 text-muted">Backend: {API_BASE_URL}</Text>
      </View>
    </KeyboardAvoidingView>
  );
}

function AuthToggle({ label, selected, onPress }: { label: string; selected: boolean; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} className={`flex-1 rounded-xl px-4 py-3 ${selected ? "bg-white" : "bg-transparent"}`}>
      <Text className={`text-center font-black ${selected ? "text-ink" : "text-muted"}`}>{label}</Text>
    </Pressable>
  );
}
