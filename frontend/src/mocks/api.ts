import sampleData from "./sampleData.json";
import { BackendUser, Regimen, Workout } from "../types/planning";

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function getMockUser(): Promise<BackendUser> {
  await wait(150);
  return sampleData.user as BackendUser;
}

export async function getMockRegimen(): Promise<Regimen> {
  await wait(250);
  return sampleData.regimen as Regimen;
}

export async function getMockReplacementRegimen(): Promise<Regimen> {
  await wait(1100);
  return sampleData.replacementRegimen as Regimen;
}

export async function getMockWorkouts(): Promise<Workout[]> {
  await wait(250);
  return sampleData.workouts as Workout[];
}

export async function getMockWorkoutById(id: number): Promise<Workout | null> {
  await wait(300);
  return ((sampleData.workouts as Workout[]).find((workout) => workout.id === id) ?? null);
}
