import "../global.css";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";
import React from "react";
import { Image, ImageSourcePropType } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { AiProcessingOverlay } from "./components/AiProcessingOverlay";
import { MainTabParamList, OnboardingStackParamList } from "./navigation/types";
import { AuthScreen } from "./screens/AuthScreen";
import { BiometricsScreen } from "./screens/BiometricsScreen";
import { GoalsScreen } from "./screens/GoalsScreen";
import { HomeScreen } from "./screens/HomeScreen";
import { LogisticsScreen } from "./screens/LogisticsScreen";
import { ProfileScreen } from "./screens/ProfileScreen";
import { ResearchScreen } from "./screens/ResearchScreen";
import { WorkoutsScreen } from "./screens/WorkoutsScreen";
import { useWorkoutPlanner, WorkoutPlannerProvider } from "./state/WorkoutPlannerContext";

const OnboardingStack = createNativeStackNavigator<OnboardingStackParamList>();
const MainTabs = createBottomTabNavigator<MainTabParamList>();
const tabIcons = {
  Home: require("../assets/home.png") as ImageSourcePropType,
  Workouts: require("../assets/dumbell.png") as ImageSourcePropType,
  Research: require("../assets/loupe.png") as ImageSourcePropType,
  Profile: require("../assets/user.png") as ImageSourcePropType,
};

function OnboardingNavigator() {
  return (
    <OnboardingStack.Navigator screenOptions={{ headerShown: false }}>
      <OnboardingStack.Screen name="Biometrics" component={BiometricsScreen} />
      <OnboardingStack.Screen name="Goals" component={GoalsScreen} />
      <OnboardingStack.Screen name="Logistics" component={LogisticsScreen} />
    </OnboardingStack.Navigator>
  );
}

function TabIcon({ source, focused }: { source: ImageSourcePropType; focused: boolean }) {
  return (
    <Image
      source={source}
      resizeMode="contain"
      style={{
        height: 24,
        tintColor: focused ? "#2563eb" : "#94a3b8",
        width: 24,
      }}
    />
  );
}

function MainNavigator() {
  const { initialMainTab } = useWorkoutPlanner();

  return (
    <MainTabs.Navigator
      initialRouteName={initialMainTab}
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
      <MainTabs.Screen
        name="Home"
        component={HomeScreen}
        options={{ tabBarIcon: ({ focused }) => <TabIcon focused={focused} source={tabIcons.Home} /> }}
      />
      <MainTabs.Screen
        name="Workouts"
        component={WorkoutsScreen}
        options={{ tabBarIcon: ({ focused }) => <TabIcon focused={focused} source={tabIcons.Workouts} /> }}
      />
      <MainTabs.Screen
        name="Research"
        component={ResearchScreen}
        options={{ tabBarIcon: ({ focused }) => <TabIcon focused={focused} source={tabIcons.Research} /> }}
      />
      <MainTabs.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ tabBarIcon: ({ focused }) => <TabIcon focused={focused} source={tabIcons.Profile} /> }}
      />
    </MainTabs.Navigator>
  );
}

function RootNavigator() {
  const { authComplete, onboardingComplete, isAiProcessing } = useWorkoutPlanner();

  return (
    <>
      <NavigationContainer>
        {!authComplete ? <AuthScreen /> : onboardingComplete ? <MainNavigator /> : <OnboardingNavigator />}
      </NavigationContainer>
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
