import React, { useRef, useState } from "react";
import Slider from "@react-native-community/slider";
import { ActivityIndicator, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { ExerciseCard } from "../components/ExerciseCard";
import { ProgressBar } from "../components/ProgressBar";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";
import { WorkoutCompletionSuggestion, WorkoutReviewFeedback } from "../types/planning";

const concernOptions = ["Soreness", "Excessive burn", "Pain", "Injury", "Low energy", "Limited mobility"];
const ratingTicks = Array.from({ length: 11 }, (_, index) => index * 0.5);

export function WorkoutsScreen() {
  const {
    regimen,
    workouts,
    selectedDay,
    currentWorkout,
    selectedDayId,
    setSelectedDayId,
    exerciseLogs,
    completionRatio,
    hasWorkoutProgress,
    workoutComplete,
    isAiProcessing,
    isRegimenGenerating,
    generationError,
    updateExerciseLog,
    resetWorkoutProgress,
    completeWorkout,
    decideNextWorkout,
    expandingDayIds,
    tweakPlanWithFeedback,
  } = useWorkoutPlanner();
  const [recapVisible, setRecapVisible] = useState(false);
  const [completionVisible, setCompletionVisible] = useState(false);
  const [completionStep, setCompletionStep] = useState<"form" | "ingesting" | "review">("form");
  const [completionFeedback, setCompletionFeedback] = useState<WorkoutReviewFeedback>({
    overallFeel: 3,
    concerns: [],
    notes: "",
  });
  const [completionSuggestion, setCompletionSuggestion] = useState<WorkoutCompletionSuggestion | null>(null);
  const [completionError, setCompletionError] = useState<string | null>(null);
  const [completionDecisionLoading, setCompletionDecisionLoading] = useState<"accept" | "reject" | null>(null);
  const [regimenVisible, setRegimenVisible] = useState(false);
  const [modifyVisible, setModifyVisible] = useState(false);
  const [modificationLoading, setModificationLoading] = useState(false);
  const [modificationText, setModificationText] = useState("");
  const scrollViewRef = useRef<ScrollView>(null);
  const workoutInProgress = hasWorkoutProgress && !workoutComplete;
  const selectedDayIndex = regimen?.plan.days.findIndex((day) => day.id === selectedDayId) ?? -1;
  const nextDay =
    regimen && selectedDayIndex >= 0 ? regimen.plan.days[(selectedDayIndex + 1) % regimen.plan.days.length] : null;

  const finishWorkout = () => {
    setCompletionFeedback({ overallFeel: 3, concerns: [], notes: "" });
    setCompletionSuggestion(null);
    setCompletionError(null);
    setCompletionStep("form");
    setCompletionVisible(true);
  };

  const toggleCompletionConcern = (concern: string) => {
    setCompletionFeedback((previous) => ({
      ...previous,
      concerns: previous.concerns.includes(concern)
        ? previous.concerns.filter((item) => item !== concern)
        : [...previous.concerns, concern],
    }));
  };

  const submitCompletionFeedback = async () => {
    setCompletionStep("ingesting");
    setCompletionError(null);
    try {
      const suggestion = await completeWorkout(completionFeedback);
      if (suggestion) {
        setCompletionSuggestion(suggestion);
      } else {
        setCompletionError("Could not generate next-workout suggestions because no current workout was available.");
      }
    } catch (error) {
      setCompletionError(error instanceof Error ? error.message : "Could not generate next-workout suggestions.");
    } finally {
      setCompletionStep("review");
    }
  };

  const decideCompletionSuggestion = async (decision: "accept" | "reject") => {
    if (!completionSuggestion) {
      return;
    }

    setCompletionDecisionLoading(decision);
    try {
      await decideNextWorkout(completionSuggestion.logId, decision);
      setCompletionVisible(false);
      setCompletionSuggestion(null);
      setRecapVisible(true);
    } finally {
      setCompletionDecisionLoading(null);
    }
  };

  const submitModification = async () => {
    const feedback = modificationText.trim();
    if (!feedback) {
      return;
    }

    setModificationLoading(true);
    try {
      await tweakPlanWithFeedback(feedback);
      setModifyVisible(false);
      setRegimenVisible(false);
      setModificationText("");
    } finally {
      setModificationLoading(false);
    }
  };

  return (
    <View className="flex-1 bg-surface">
      <ScrollView ref={scrollViewRef} contentContainerClassName="px-5 pb-32 pt-14">
        <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Workouts</Text>
        <Text className="mt-2 text-4xl font-black text-ink">Today and what&apos;s next</Text>
        <Text className="mt-3 text-base leading-6 text-muted">
          Today stays pinned to the top, followed by the next training days and planning metrics.
        </Text>

        {!regimen ? (
          <View className="mt-6 rounded-3xl border border-blue-100 bg-white p-5">
            <Text className="text-xl font-black text-ink">
              {generationError ? "Regimen setup needs attention" : "Creating your regimen skeleton"}
            </Text>
            <Text className={`mt-2 text-sm font-semibold leading-5 ${generationError ? "text-red-600" : "text-brand"}`}>
              {generationError
                ? generationError
                : isRegimenGenerating || isAiProcessing
                  ? "The first LLM call is building your weekly schedule. It will appear here automatically."
                  : "Your plan will appear here as soon as generation starts."}
            </Text>
          </View>
        ) : null}

        {regimen ? <View className="mt-6 rounded-3xl border border-brand bg-blue-50 p-5">
          <View className="flex-row items-start justify-between gap-4">
            <View className="flex-1">
              <Text className="text-xs font-black uppercase tracking-[2px] text-brand">Today</Text>
              <Text className="mt-2 text-2xl font-black text-ink">{selectedDay?.title ?? "No workout selected"}</Text>
              <Text className="mt-2 text-sm leading-5 text-slate-600">{selectedDay?.focus}</Text>
            </View>
            <Text className="rounded-full bg-white px-3 py-2 text-xs font-black text-brand">
              {selectedDay?.intensity ?? "Plan"}
            </Text>
          </View>

          <View className="mt-5">
            <View className="mb-3 flex-row items-center justify-between">
              <Text className="font-black text-ink">Logged progress</Text>
              <Text className="font-black text-brand">{Math.round(completionRatio * 100)}%</Text>
            </View>
            <ProgressBar value={completionRatio} />
          </View>

          {currentWorkout && hasWorkoutProgress ? (
            <View className="mt-5 flex-row gap-3">
              {workoutInProgress ? (
                <Pressable
                  onPress={() => scrollViewRef.current?.scrollTo({ y: 360, animated: true })}
                  className="flex-1 rounded-2xl bg-brand px-4 py-3"
                >
                  <Text className="text-center font-black text-white">Resume Workout</Text>
                </Pressable>
              ) : null}
              <Pressable onPress={resetWorkoutProgress} className="flex-1 rounded-2xl border border-slate-300 bg-white px-4 py-3">
                <Text className="text-center font-black text-slate-700">Reset Progress</Text>
              </Pressable>
            </View>
          ) : null}
        </View> : null}

        {regimen ? currentWorkout ? (
          <View className="mt-5">
            {currentWorkout.exercises.map((exercise) => (
              <ExerciseCard
                key={exercise.id}
                exercise={exercise}
                log={exerciseLogs[exercise.id]}
                onChange={(updates) => updateExerciseLog(exercise.id, updates)}
              />
            ))}
            <Pressable onPress={finishWorkout} className="mt-1 rounded-2xl bg-brand px-5 py-4">
              <Text className="text-center text-lg font-black text-white">
                {workoutInProgress ? "Finish Saved Workout" : "Complete Workout"}
              </Text>
            </Pressable>
          </View>
        ) : selectedDay?.workout_id ? (
          <View className="mt-5 rounded-3xl border border-blue-100 bg-white p-5">
            <Text className="text-xl font-black text-ink">Workout is being built</Text>
            <Text className="mt-2 text-sm leading-5 text-muted">
              The weekly skeleton is ready. This day&apos;s exercise list will appear here as soon as its LLM expansion call returns.
            </Text>
          </View>
        ) : (
          <View className="mt-5 rounded-3xl bg-white p-5">
            <Text className="text-xl font-black text-ink">Recovery day</Text>
            <Text className="mt-2 text-sm leading-5 text-muted">{selectedDay?.notes ?? "No lift scheduled."}</Text>
          </View>
        ) : null}

        {nextDay ? (
          <DaySummaryCard
            day={nextDay}
            workout={nextDay.workout_id ? workouts.find((item) => item.id === nextDay.workout_id) ?? null : null}
            expanding={expandingDayIds.includes(nextDay.id) || Boolean(nextDay.workout_id && !workouts.find((item) => item.id === nextDay.workout_id))}
            eyebrow="Next day"
            onPress={() => setSelectedDayId(nextDay.id)}
          />
        ) : null}

        {regimen ? (
          <Pressable onPress={() => setRegimenVisible(true)} className="mt-6 rounded-2xl bg-ink px-5 py-4">
            <Text className="text-center text-lg font-black text-white">Regimen</Text>
          </Pressable>
        ) : null}
      </ScrollView>

      <Modal visible={completionVisible} animationType="slide" presentationStyle="pageSheet">
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} className="flex-1 bg-surface">
          <ScrollView contentContainerClassName="flex-grow px-5 pb-8 pt-16" keyboardShouldPersistTaps="handled">
            <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Workout Check-In</Text>
            <Text className="mt-3 text-3xl font-black text-ink">How did today&apos;s workout go?</Text>

            {completionStep === "form" ? (
              <View className="mt-6 rounded-3xl bg-white p-5">
                <View className="flex-row items-center justify-between gap-4">
                  <Text className="flex-1 text-sm font-black text-ink">How did your workout feel overall?</Text>
                  <Text className="rounded-full bg-blue-50 px-3 py-2 text-lg font-black text-brand">
                    {completionFeedback.overallFeel.toFixed(1)}
                  </Text>
                </View>
                <View className="mt-4">
                  <Slider
                    minimumValue={0}
                    maximumValue={5}
                    step={0.5}
                    value={completionFeedback.overallFeel}
                    minimumTrackTintColor="#2563eb"
                    maximumTrackTintColor="#e2e8f0"
                    thumbTintColor="#2563eb"
                    onValueChange={(overallFeel) => setCompletionFeedback((previous) => ({ ...previous, overallFeel }))}
                  />
                  <View className="-mt-1 flex-row items-start justify-between px-3">
                    {ratingTicks.map((tick) => (
                      <View key={tick} className={tick % 1 === 0 ? "h-3 w-0.5 rounded-full bg-slate-400" : "h-2 w-0.5 rounded-full bg-slate-300"} />
                    ))}
                  </View>
                  <View className="mt-1 flex-row justify-between">
                    <Text className="text-xs font-bold text-muted">0</Text>
                    <Text className="text-xs font-bold text-muted">2.5</Text>
                    <Text className="text-xs font-bold text-muted">5</Text>
                  </View>
                </View>

                <Text className="mt-6 text-sm font-black text-ink">Identify any of the following concerns</Text>
                <View className="mt-3 flex-row flex-wrap gap-2">
                  {concernOptions.map((concern) => {
                    const active = completionFeedback.concerns.includes(concern);
                    return (
                      <Pressable
                        key={concern}
                        onPress={() => toggleCompletionConcern(concern)}
                        className={`rounded-full px-3 py-2 ${active ? "bg-red-50" : "bg-slate-100"}`}
                      >
                        <Text className={`font-bold ${active ? "text-red-600" : "text-slate-700"}`}>{concern}</Text>
                      </Pressable>
                    );
                  })}
                </View>

                <Text className="mt-6 text-sm font-black text-ink">Describe any feedback about your workout</Text>
                <TextInput
                  multiline
                  value={completionFeedback.notes}
                  onChangeText={(notes) => setCompletionFeedback((previous) => ({ ...previous, notes }))}
                  placeholder="Anything feel too easy, too intense, painful, or constrained by time/equipment?"
                  placeholderTextColor="#94a3b8"
                  className="mt-3 min-h-32 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-base leading-6 text-ink"
                />

                <Pressable onPress={submitCompletionFeedback} className="mt-5 rounded-2xl bg-brand px-5 py-4">
                  <Text className="text-center text-lg font-black text-white">Submit</Text>
                </Pressable>
                <Pressable onPress={() => setCompletionVisible(false)} className="mt-3 px-5 py-3">
                  <Text className="text-center font-bold text-muted">Cancel</Text>
                </Pressable>
              </View>
            ) : null}

            {completionStep === "ingesting" ? (
              <View className="mt-6 flex-1 items-center justify-center rounded-3xl bg-white p-6">
                <ActivityIndicator color="#2563eb" size="large" />
                <Text className="mt-4 text-center text-2xl font-black text-ink">AI is ingesting your results...</Text>
                <Text className="mt-2 text-center text-sm leading-5 text-muted">
                  Reviewing your logged sets, reps, load, concerns, and feedback before drafting tomorrow&apos;s session.
                </Text>
              </View>
            ) : null}

            {completionStep === "review" ? (
              <View className="mt-6 rounded-3xl bg-white p-5">
                <Text className="text-xs font-black uppercase tracking-[2px] text-brand">Tomorrow&apos;s Workout</Text>
                {completionError ? <Text className="mt-3 text-sm font-semibold text-red-600">{completionError}</Text> : null}
                {completionSuggestion?.suggestedWorkout ? (
                  <SuggestedWorkoutBlurb suggestion={completionSuggestion} />
                ) : null}
                <View className="mt-5 flex-row gap-3">
                  <Pressable
                    disabled={!completionSuggestion || Boolean(completionDecisionLoading)}
                    onPress={() => decideCompletionSuggestion("accept")}
                    className="flex-1 rounded-2xl bg-brand px-4 py-4"
                  >
                    <Text className="text-center font-black text-white">
                      {completionDecisionLoading === "accept" ? "Accepting..." : "Accept"}
                    </Text>
                  </Pressable>
                  <Pressable
                    disabled={!completionSuggestion || Boolean(completionDecisionLoading)}
                    onPress={() => decideCompletionSuggestion("reject")}
                    className="flex-1 rounded-2xl border border-slate-300 bg-white px-4 py-4"
                  >
                    <Text className="text-center font-black text-slate-700">
                      {completionDecisionLoading === "reject" ? "Rejecting..." : "Reject"}
                    </Text>
                  </Pressable>
                </View>
                <Pressable onPress={() => setCompletionVisible(false)} className="mt-3 px-5 py-3">
                  <Text className="text-center font-bold text-muted">Close</Text>
                </Pressable>
              </View>
            ) : null}
          </ScrollView>
        </KeyboardAvoidingView>
      </Modal>

      <Modal visible={recapVisible} transparent animationType="fade">
        <View className="flex-1 justify-end bg-slate-950/50">
          <View className="rounded-t-[32px] bg-white px-5 pb-10 pt-6">
            <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Workout Recap</Text>
            <Text className="mt-3 text-3xl font-black text-ink">Workout complete</Text>
            <Text className="mt-3 text-base leading-6 text-muted">
              Planned versus actual reps and loads are saved in local state and ready for the AI feedback loop.
            </Text>
            <Pressable onPress={() => setRecapVisible(false)} className="mt-6 rounded-2xl bg-ink px-5 py-4">
              <Text className="text-center text-lg font-black text-white">Close Recap</Text>
            </Pressable>
          </View>
        </View>
      </Modal>

      <Modal visible={regimenVisible} animationType="slide" presentationStyle="pageSheet">
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : "height"} className="flex-1 bg-surface">
          <View className="flex-1 px-5 pb-8 pt-16">
            {modificationLoading ? (
              <View className="flex-1 items-center justify-center">
                <View className="w-full rounded-3xl bg-white p-6">
                  <ActivityIndicator color="#2563eb" size="large" />
                  <Text className="mt-4 text-center text-2xl font-black text-ink">Modifying regimen...</Text>
                  <Text className="mt-2 text-center text-sm leading-5 text-muted">
                    Applying your feedback to the durable training blueprint. This can take a moment.
                  </Text>
                </View>
              </View>
            ) : (
              <>
                <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Regimen</Text>
                <Text className="mt-3 text-3xl font-black text-ink">{regimen?.name ?? "Current plan"}</Text>
                <ScrollView className="mt-5" contentContainerClassName="gap-3 pb-6" keyboardShouldPersistTaps="handled">
                  {regimen?.plan.days.map((day) => {
                    const workout = day.workout_id ? workouts.find((item) => item.id === day.workout_id) ?? null : null;
                    const expanding = expandingDayIds.includes(day.id) || Boolean(day.workout_id && !workout);
                    return <DaySummaryCard key={day.id} day={day} workout={workout} expanding={expanding} eyebrow={`Day ${day.day_index}`} />;
                  })}
                </ScrollView>

                {modifyVisible ? (
                  <View className="rounded-3xl border border-slate-200 bg-white p-4">
                    <Text className="text-xs font-black uppercase tracking-[2px] text-muted">Modification request</Text>
                    <TextInput
                      multiline
                      value={modificationText}
                      onChangeText={setModificationText}
                      placeholder="Tell the AI how to modify this regimen..."
                      placeholderTextColor="#94a3b8"
                      className="mt-3 min-h-28 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-base leading-6 text-ink"
                    />
                    <Pressable onPress={submitModification} className="mt-4 rounded-2xl bg-brand px-5 py-4">
                      <Text className="text-center text-lg font-black text-white">Submit Modification</Text>
                    </Pressable>
                  </View>
                ) : (
                  <Pressable onPress={() => setModifyVisible(true)} className="rounded-2xl bg-brand px-5 py-4">
                    <Text className="text-center text-lg font-black text-white">Modify Regimen</Text>
                  </Pressable>
                )}

                <Pressable onPress={() => setRegimenVisible(false)} className="mt-3 px-5 py-3">
                  <Text className="text-center font-bold text-muted">Close</Text>
                </Pressable>
              </>
            )}
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

function SuggestedWorkoutBlurb({ suggestion }: { suggestion: WorkoutCompletionSuggestion }) {
  const baseline = suggestion.baselineWorkout;
  const suggested = suggestion.suggestedWorkout;
  const hasChanges = suggestion.modifications.length > 0;
  const suggestedIsRest = suggested?.exercises.length === 0;
  const baselineIsRest = baseline?.exercises.length === 0;

  if (!suggested) {
    return <Text className="mt-3 text-sm font-semibold text-muted">No next workout is scheduled from the regimen blueprint.</Text>;
  }

  return (
    <View className="mt-3">
      <Text className="text-2xl font-black text-ink">{suggested.scheduled_day}</Text>
      <Text className="mt-1 text-sm font-semibold text-muted">
        {hasChanges
          ? "AI suggested short-term changes based on your workout feedback."
          : "No short-term changes suggested; this matches the regimen blueprint."}
      </Text>
      {suggestedIsRest ? (
        <View className="mt-4 rounded-2xl bg-slate-50 p-4">
          <Text className="font-black text-ink">Rest day</Text>
          <Text className="mt-1 text-sm font-semibold text-muted">
            {baselineIsRest
              ? "Tomorrow was already a rest day in the regimen blueprint."
              : "AI suggests converting tomorrow's workout instance into recovery based on your feedback."}
          </Text>
        </View>
      ) : null}
      <View className="mt-4 gap-3">
        {suggested.exercises.map((exercise, index) => (
          <View key={`${exercise.name}-${index}`} className="rounded-2xl bg-slate-50 p-4">
            <Text className="font-black text-ink">{exercise.name}</Text>
            <View className="mt-2 flex-row flex-wrap gap-3">
              <ExerciseValueDiff label="Sets" before={baseline?.exercises[index]?.sets} after={exercise.sets} />
              <ExerciseValueDiff label="Reps" before={baseline?.exercises[index]?.reps} after={exercise.reps} />
              <ExerciseValueDiff label="Weight" before={baseline?.exercises[index]?.weight} after={exercise.weight} suffix=" lb" />
              <ExerciseValueDiff label="Rest" before={baseline?.exercises[index]?.rest_time} after={exercise.rest_time} suffix="s" />
            </View>
          </View>
        ))}
      </View>
    </View>
  );
}

function ExerciseValueDiff({
  label,
  before,
  after,
  suffix = "",
}: {
  label: string;
  before?: number;
  after: number;
  suffix?: string;
}) {
  const changed = before !== undefined && before !== after;
  return (
    <View className="min-w-20">
      <Text className="text-xs font-bold uppercase tracking-wide text-muted">{label}</Text>
      {changed ? (
        <Text className="mt-1 text-sm font-black">
          <Text className="text-slate-400 line-through">
            {before}
            {suffix}
          </Text>
          <Text className="text-red-600">
            {"  "}
            {after}
            {suffix}
          </Text>
        </Text>
      ) : (
        <Text className="mt-1 text-sm font-black text-slate-700">
          {after}
          {suffix}
        </Text>
      )}
    </View>
  );
}

function DaySummaryCard({
  day,
  workout,
  expanding,
  eyebrow,
  onPress,
}: {
  day: NonNullable<ReturnType<typeof useWorkoutPlanner>["selectedDay"]>;
  workout: ReturnType<typeof useWorkoutPlanner>["currentWorkout"];
  expanding: boolean;
  eyebrow: string;
  onPress?: () => void;
}) {
  const content = (
    <View className="rounded-3xl border border-slate-200 bg-white p-4">
      <View className="flex-row items-center justify-between gap-4">
        <View className="flex-1">
          <Text className="text-xs font-black uppercase tracking-[2px] text-muted">{eyebrow}</Text>
          <Text className="mt-1 text-lg font-black text-ink">{day.title}</Text>
          <Text className="mt-1 text-sm text-muted" numberOfLines={2}>
            {workout
              ? workout.exercises.length > 0
                ? `${workout.exercises.length} exercises • ${workout.muscles_worked}`
                : "Rest day"
              : expanding
                ? "Expanding workout..."
                : day.notes}
          </Text>
        </View>
        <Text className="rounded-full bg-slate-100 px-3 py-2 text-xs font-black text-slate-600">
          {expanding ? "AI" : day.intensity}
        </Text>
      </View>
      {workout ? (
        <View className="mt-3 gap-2">
          {workout.exercises.map((exercise) => (
            <View key={exercise.id} className="flex-row justify-between rounded-xl bg-slate-50 px-3 py-2">
              <Text className="flex-1 font-semibold text-slate-700">{exercise.name}</Text>
              <Text className="font-bold text-muted">
                {exercise.sets}x{exercise.reps}
              </Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );

  return onPress ? <Pressable onPress={onPress}>{content}</Pressable> : content;
}
