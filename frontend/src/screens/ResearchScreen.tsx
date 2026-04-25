import React, { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { API_BASE_URL } from "../api/backend";
import { useWorkoutPlanner } from "../state/WorkoutPlannerContext";

const API_BASE = API_BASE_URL;

interface ResearchResponse {
  direct_answer: string;
  why: string[];
  do_this_next: string[];
  follow_ups: string[];
  citations: string[];
  safety_flags: string[];
}

interface HistoryItem {
  id: string;
  question: string;
  answer: string;
}

export function ResearchScreen() {
  const { user, refreshPlannerData } = useWorkoutPlanner();
  const [question, setQuestion] = useState("");
  const [lastAsked, setLastAsked] = useState("");
  const [suggestionsExpanded, setSuggestionsExpanded] = useState(false);
  const [regenerateExpanded, setRegenerateExpanded] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [answer, setAnswer] = useState<ResearchResponse | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [conversationY, setConversationY] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const mainScrollRef = useRef<ScrollView>(null);

  const username = user?.username ?? "demo-athlete";

  async function callApi<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error ?? `Request failed (${response.status})`);
    }
    return payload as T;
  }

  async function loadContextAndSuggestions() {
    setLoading(true);
    setStatusMessage("");
    try {
      const suggested = await callApi<{ suggested_questions: string[] }>(`/users/${username}/research/suggestions`);
      setSuggestions(suggested.suggested_questions ?? []);
    } catch (error) {
      setStatusMessage(`Unable to load backend suggestions. (${String(error)})`);
      setSuggestions([
        "Based on my last workout, what should I train next?",
        "How much should I increase weight for compound lifts next week?",
        "What rest times should I use for strength vs hypertrophy?",
      ]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadContextAndSuggestions();
    // We want this to run once for initial hydration.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function askQuestion(prompt: string, options?: { scrollToResponse?: boolean }) {
    if (!prompt.trim()) {
      setStatusMessage("Type a question first.");
      return;
    }
    setLoading(true);
    setStatusMessage("");
    try {
      const response = await callApi<ResearchResponse>(`/users/${username}/research/ask`, {
        method: "POST",
        body: JSON.stringify({
          question: prompt.trim(),
          style: "concise",
        }),
      });
      setAnswer(response);
      setLastAsked(prompt.trim());
      setQuestion(prompt);
      setSuggestions(response.follow_ups ?? suggestions);
      setHistory((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${Math.random()}`,
          question: prompt.trim(),
          answer: response.direct_answer,
        },
      ]);
      setStatusMessage("Answer generated from research context.");
      if (options?.scrollToResponse) {
        requestAnimationFrame(() => {
          mainScrollRef.current?.scrollTo({ y: Math.max(conversationY - 12, 0), animated: true });
        });
      }
    } catch (error) {
      setStatusMessage(`Failed to ask question: ${String(error)}`);
    } finally {
      setLoading(false);
    }
  }

  async function runAction(action: "apply_to_next_workout" | "save_as_note" | "regenerate") {
    if (action === "regenerate") {
      await askQuestion(question);
      return;
    }
    if (action === "apply_to_next_workout" && !lastAsked.trim() && !answer?.direct_answer?.trim()) {
      setStatusMessage("Ask a question first so coach guidance can be applied to your workout.");
      return;
    }
    setLoading(true);
    setStatusMessage("");
    try {
      const payload = await callApi<{ message: string }>(`/users/${username}/research/actions`, {
        method: "POST",
        body: JSON.stringify({
          action,
          question: (lastAsked || question).trim(),
          style: "concise",
          answer_snapshot: answer?.direct_answer ?? "",
        }),
      });
      if (action === "apply_to_next_workout") {
        await refreshPlannerData();
      }
      setStatusMessage(payload.message);
    } catch (error) {
      setStatusMessage(`Action failed: ${String(error)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <View className="flex-1 bg-surface">
      <ScrollView ref={mainScrollRef} className="flex-1" contentContainerClassName="px-5 pb-44 pt-14">
        <Text className="text-sm font-black uppercase tracking-[3px] text-brand">Research</Text>
        <Text className="mt-2 text-4xl font-black text-ink">AI Trainer</Text>
        <Text className="mt-3 text-base leading-6 text-muted">
          Ask questions using your regimen, workouts, mood, rest, and weight context.
        </Text>

        <View className="mt-5 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <Text className="text-sm font-black uppercase tracking-[2px] text-muted">Search / ask bar</Text>
          <TextInput
            value={question}
            onChangeText={setQuestion}
            placeholder="How should I progress bench next week?"
            placeholderTextColor="#94a3b8"
            className="mt-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-base font-semibold leading-5 text-ink"
            style={{ minHeight: 56 }}
          />
          <View className="mt-3 flex-row items-center justify-between">
            <Text className="mr-3 flex-1 text-sm font-semibold leading-5 text-muted">
              Ask directly or tap a suggested question below.
            </Text>
            <Pressable onPress={() => askQuestion(question)} className="rounded-2xl bg-brand px-5 py-2.5">
              <Text className="text-center text-base font-black text-white">Ask</Text>
            </Pressable>
          </View>

          <View className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
            <Pressable onPress={() => setSuggestionsExpanded((value) => !value)} className="flex-row items-center justify-between">
              <Text className="text-sm font-black uppercase tracking-[2px] text-muted">Suggested questions</Text>
              <Text className="text-sm font-black text-brand">{suggestionsExpanded ? "Minimize" : "Expand"}</Text>
            </Pressable>

            {suggestionsExpanded ? (
              <View className="mt-3 gap-2">
                {suggestions.length === 0 ? (
                  <Text className="text-base font-semibold text-muted">Loading context-aware question ideas...</Text>
                ) : (
                  suggestions.map((chip) => (
                    <Pressable
                      key={chip}
                      onPress={() => askQuestion(chip, { scrollToResponse: true })}
                      className="rounded-xl bg-white px-4 py-3"
                    >
                      <Text className="text-base font-black leading-6 text-slate-700">{chip}</Text>
                    </Pressable>
                  ))
                )}
              </View>
            ) : null}
          </View>

          {loading ? <ActivityIndicator className="mt-4" /> : null}
          {statusMessage ? <Text className="mt-4 text-base font-semibold text-slate-600">{statusMessage}</Text> : null}
        </View>

        <View
          onLayout={(event) => setConversationY(event.nativeEvent.layout.y)}
          className="mt-4 flex-1 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm"
        >
          <View className="flex-row items-center justify-between">
            <Text className="text-sm font-black uppercase tracking-[2px] text-muted">Conversation</Text>
            <Pressable
              onPress={() => setHistoryOpen(true)}
              className="rounded-xl border border-slate-300 bg-slate-50 px-3 py-1.5"
            >
              <Text className="text-xs font-black uppercase tracking-[1px] text-slate-700">History</Text>
            </Pressable>
          </View>

        {lastAsked ? (
          <View className="mt-4 items-end">
            <View className="max-w-[88%] rounded-2xl bg-brand px-4 py-3">
              <Text className="text-base font-semibold leading-6 text-white">{lastAsked}</Text>
            </View>
          </View>
        ) : null}

        <View className="mt-3 items-start">
          <View className="w-full rounded-2xl bg-slate-100 px-4 py-3">
            <Text className="text-base font-semibold leading-6 text-slate-800">
              {answer?.direct_answer ?? "Ask a question to start the coach chat."}
            </Text>
            {(answer?.why?.length ?? 0) > 0 ? (
              <Text className="mt-3 text-sm font-black uppercase tracking-[2px] text-muted">Why</Text>
            ) : null}
            {(answer?.why ?? []).map((line) => (
              <Text key={line} className="mt-1 text-base font-semibold leading-6 text-slate-700">
                • {line}
              </Text>
            ))}
            {(answer?.do_this_next?.length ?? 0) > 0 ? (
              <Text className="mt-3 text-sm font-black uppercase tracking-[2px] text-muted">Do this next</Text>
            ) : null}
            {(answer?.do_this_next ?? []).map((step) => (
              <Text key={step} className="mt-1 text-base font-semibold leading-6 text-slate-700">
                - {step}
              </Text>
            ))}
            {(answer?.citations?.length ?? 0) > 0 ? (
              <Text className="mt-3 text-sm font-black uppercase tracking-[2px] text-muted">Citations</Text>
            ) : null}
            {(answer?.citations ?? []).map((item) => (
              <Text key={item} className="mt-1 text-base font-semibold leading-6 text-slate-700">
                • {item}
              </Text>
            ))}
          </View>
        </View>

        {answer?.safety_flags?.length ? (
          <View className="mt-5 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3">
            <Text className="text-base font-black text-amber-800">
              Safety: possible injury language detected. Keep guidance conservative and seek medical care for persistent pain.
            </Text>
          </View>
        ) : null}

        <Text className="mt-5 text-sm font-black uppercase tracking-[2px] text-muted">Follow-up chips</Text>
        <View className="mt-2 gap-2">
          {(answer?.follow_ups ?? []).map((chip) => (
            <Pressable
              key={chip}
              onPress={() => askQuestion(chip, { scrollToResponse: true })}
              className="rounded-2xl bg-blue-50 px-4 py-3"
            >
              <Text className="text-base font-black leading-6 text-brand">{chip}</Text>
            </Pressable>
          ))}
        </View>

        </View>
      </ScrollView>

      <View className="absolute bottom-0 left-0 right-0 border-t border-slate-200 bg-white px-5 pb-6 pt-4">
        <View className="items-center">
          <Pressable
            onPress={() => setRegenerateExpanded((value) => !value)}
            className="h-7 w-10 items-center justify-center rounded-full border border-slate-300 bg-slate-50"
            accessibilityRole="button"
            accessibilityLabel={regenerateExpanded ? "Collapse footer actions" : "Expand footer actions"}
          >
            <Text className="text-base font-black text-slate-600">{regenerateExpanded ? "⌄" : "⌃"}</Text>
          </Pressable>
        </View>
        {regenerateExpanded ? (
          <View className="mt-3 flex-row gap-2">
            <Pressable onPress={() => runAction("apply_to_next_workout")} className="flex-1 rounded-2xl bg-slate-900 px-3 py-3">
              <Text className="text-center text-base font-black text-white">Apply</Text>
            </Pressable>
            <Pressable onPress={() => runAction("regenerate")} className="flex-1 rounded-2xl bg-brand px-3 py-3">
              <Text className="text-center text-base font-black text-white">Regenerate</Text>
            </Pressable>
          </View>
        ) : null}
      </View>

      <Modal visible={historyOpen} animationType="slide" transparent onRequestClose={() => setHistoryOpen(false)}>
        <View className="flex-1 bg-black/35">
          <View className="mt-20 flex-1 rounded-t-3xl bg-white px-5 pb-10 pt-5">
            <View className="flex-row items-center justify-between">
              <Text className="text-sm font-black uppercase tracking-[2px] text-muted">Coach chat history</Text>
              <Pressable onPress={() => setHistoryOpen(false)} className="rounded-xl bg-slate-100 px-3 py-2">
                <Text className="text-sm font-black text-slate-700">Close</Text>
              </Pressable>
            </View>

            <ScrollView className="mt-4 flex-1">
              {history.length === 0 ? (
                <View className="rounded-2xl bg-slate-100 px-4 py-3">
                  <Text className="text-base font-semibold text-slate-700">
                    No messages yet. Ask a question to start your history.
                  </Text>
                </View>
              ) : (
                history.map((item) => (
                  <View key={item.id} className="mb-3">
                    <View className="items-end">
                      <View className="max-w-[88%] rounded-2xl bg-brand px-4 py-3">
                        <Text className="text-base font-semibold leading-6 text-white">{item.question}</Text>
                      </View>
                    </View>
                    <View className="mt-2 items-start">
                      <View className="max-w-[92%] rounded-2xl bg-slate-100 px-4 py-3">
                        <Text className="text-base font-semibold leading-6 text-slate-800">{item.answer}</Text>
                      </View>
                    </View>
                  </View>
                ))
              )}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
}
