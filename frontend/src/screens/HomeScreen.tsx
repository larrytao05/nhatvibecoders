import { BottomTabNavigationProp } from "@react-navigation/bottom-tabs";
import { useNavigation } from "@react-navigation/native";
import React from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { ProgressBar } from "../components/ProgressBar";
import { MainTabParamList } from "../navigation/types";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

export function HomeScreen() {
  const navigation = useNavigation<BottomTabNavigationProp<MainTabParamList, "Home">>();
  const { regimen, selectedDay, currentWorkout, completionRatio, onboarding } = useWorkoutPlanner();
  const workoutDone = currentWorkout ? completionRatio === 1 : false;
  const weeklyTrainingDays = regimen?.plan.days.filter((day) => day.workout_id).length ?? onboarding.frequency;

  return (
    <ScrollView className="flex-1 bg-surface" contentContainerClassName="px-5 pb-28 pt-14">
      <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Home</Text>
      <Text className="mt-2 text-4xl font-black text-ink">Today at a glance</Text>
      <Text className="mt-3 text-base leading-6 text-muted">
        Your current plan, daily workout status, and reminders in one place.
      </Text>

      <HomeCard eyebrow="Summary" title={regimen?.name ?? "HTP Plan"}>
        <View className="mt-5 flex-row justify-between">
          <SummaryMetric label="Days" value="7" />
          <SummaryMetric label="Lifts" value={String(weeklyTrainingDays)} />
          <SummaryMetric label="Done" value={`${Math.round(completionRatio * 100)}%`} />
        </View>
      </HomeCard>

      <HomeCard eyebrow="Today's Workout" title={selectedDay?.title ?? "No workout selected"}>
        <View className="flex-row items-start justify-between gap-4">
          <View className="flex-1">
            <Text className="text-sm leading-5 text-muted">{selectedDay?.focus ?? "Generate a plan to see today&apos;s training."}</Text>
          </View>
          <View className={`rounded-full px-3 py-2 ${workoutDone ? "bg-emerald-50" : "bg-blue-50"}`}>
            <Text className={`text-xs font-black ${workoutDone ? "text-emerald-600" : "text-brand"}`}>
              {workoutDone ? "DONE" : "READY"}
            </Text>
          </View>
        </View>

        {currentWorkout ? (
          <View className="mt-5">
            <ProgressBar value={completionRatio} />
            <Text className="mt-3 text-sm font-semibold text-slate-600">
              {workoutDone
                ? `${currentWorkout.exercises.length} exercises completed. Review your logged reps and load in Workouts.`
                : `${currentWorkout.exercises.length} exercises planned. Start when you are ready.`}
            </Text>
          </View>
        ) : (
          <Text className="mt-4 text-sm font-semibold text-slate-600">{selectedDay?.notes ?? "Rest, recover, and keep your steps easy."}</Text>
        )}

        <Pressable onPress={() => navigation.navigate("Workouts")} className="mt-5 rounded-2xl bg-brand px-5 py-4">
          <Text className="text-center text-lg font-black text-white">{workoutDone ? "View Recap" : "Start Workout"}</Text>
        </Pressable>
      </HomeCard>

      <HomeCard eyebrow="Daily / Weekly Reminders" title="Stay on track">
        <Reminder text={`Train ${weeklyTrainingDays} days this week based on your current regimen.`} />
        <Reminder text="Log actual reps and weight before completing the workout." />
        <Reminder text="Use plan feedback when soreness, schedule, or equipment changes." />
      </HomeCard>

      <HomeCard eyebrow="Alerts / Notifications" title="AI coaching note" badge="New">
        <Text className="mt-3 text-sm font-semibold leading-5 text-slate-700">
          Mock AI alert: keep today&apos;s main lifts near RPE 8 and avoid adding extra pressing volume.
        </Text>
      </HomeCard>
    </ScrollView>
  );
}

function HomeCard({
  eyebrow,
  title,
  badge,
  children,
}: {
  eyebrow: string;
  title: string;
  badge?: string;
  children: React.ReactNode;
}) {
  return (
    <View className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <View className="flex-row items-start justify-between gap-4">
        <View className="flex-1">
          <Text className="text-xs font-black uppercase tracking-[2px] text-muted">{eyebrow}</Text>
          <Text className="mt-2 text-2xl font-black leading-8 text-ink">{title}</Text>
        </View>
        {badge ? (
          <View className="rounded-full bg-blue-50 px-3 py-2">
            <Text className="text-xs font-black text-brand">{badge}</Text>
          </View>
        ) : null}
      </View>
      {children}
    </View>
  );
}

function SummaryMetric({ label, value }: { label: string; value: string }) {
  return (
    <View>
      <Text className="text-xs font-bold uppercase tracking-wide text-muted">{label}</Text>
      <Text className="mt-1 text-2xl font-black text-ink">{value}</Text>
    </View>
  );
}

function Reminder({ text }: { text: string }) {
  return (
    <View className="mt-4 flex-row gap-3">
      <View className="mt-1 h-2 w-2 rounded-full bg-brand" />
      <Text className="flex-1 text-sm font-semibold leading-5 text-slate-700">{text}</Text>
    </View>
  );
}
