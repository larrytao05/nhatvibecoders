import "../global.css";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";
import React from "react";
import { Text } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AiProcessingOverlay } from "./components/AiProcessingOverlay";
import { MainTabParamList, OnboardingStackParamList } from "./navigation/types";
import { BiometricsScreen } from "./screens/BiometricsScreen";
import { GoalsScreen } from "./screens/GoalsScreen";
import { HomeScreen } from "./screens/HomeScreen";
import { LogisticsScreen } from "./screens/LogisticsScreen";
import { ProfileScreen } from "./screens/ProfileScreen";
import { WorkoutsScreen } from "./screens/WorkoutsScreen";
import { useWorkoutPlanner, WorkoutPlannerProvider } from "./state/WorkoutPlannerContext";

const OnboardingStack = createNativeStackNavigator<OnboardingStackParamList>();
const MainTabs = createBottomTabNavigator<MainTabParamList>();

function OnboardingNavigator() {
  return (
    <OnboardingStack.Navigator screenOptions={{ headerShown: false }}>
      <OnboardingStack.Screen name="Biometrics" component={BiometricsScreen} />
      <OnboardingStack.Screen name="Goals" component={GoalsScreen} />
      <OnboardingStack.Screen name="Logistics" component={LogisticsScreen} />
    </OnboardingStack.Navigator>
  );
}

function TabGlyph({ label, focused }: { label: string; focused: boolean }) {
  return <Text className={`text-xs font-black ${focused ? "text-brand" : "text-slate-400"}`}>{label}</Text>;
}

function MainNavigator() {
  return (
    <MainTabs.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#2563eb",
        tabBarInactiveTintColor: "#94a3b8",
        tabBarLabelStyle: { fontWeight: "800", fontSize: 11 },
        tabBarStyle: {
          height: 84,
          paddingBottom: 24,
          paddingTop: 10,
          borderTopColor: "#e2e8f0",
        },
      }}
    >
      <MainTabs.Screen name="Home" component={HomeScreen} options={{ tabBarIcon: ({ focused }) => <TabGlyph focused={focused} label="HM" /> }} />
      <MainTabs.Screen
        name="Workouts"
        component={WorkoutsScreen}
        options={{ tabBarIcon: ({ focused }) => <TabGlyph focused={focused} label="WO" /> }}
      />
      <MainTabs.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ tabBarIcon: ({ focused }) => <TabGlyph focused={focused} label="ME" /> }}
      />
    </MainTabs.Navigator>
  );
}

function RootNavigator() {
  const { onboardingComplete, isAiProcessing } = useWorkoutPlanner();

  return (
    <>
      <NavigationContainer>{onboardingComplete ? <MainNavigator /> : <OnboardingNavigator />}</NavigationContainer>
      <AiProcessingOverlay visible={isAiProcessing} />
    </>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <WorkoutPlannerProvider>
        <StatusBar style="dark" />
        <RootNavigator />
      </WorkoutPlannerProvider>
    </SafeAreaProvider>
  );
}
