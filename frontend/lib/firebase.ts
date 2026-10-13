import { getApp, getApps, initializeApp } from "firebase/app";
import { connectAuthEmulator, getAuth, type Auth } from "firebase/auth";
let instance: Auth | undefined;
export function firebaseAuth(): Auth {
  if (
    process.env.NODE_ENV === "production" &&
    process.env.NEXT_PUBLIC_AUTH_EMULATOR
  ) {
    throw new Error("Auth emulator is forbidden in production builds.");
  }
  if (instance) return instance;
  const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY;
  const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
  if (!apiKey || !projectId)
    throw new Error(
      "Authentication is not configured. See the hosted setup guide.",
    );
  const app = getApps().length
    ? getApp()
    : initializeApp({
        apiKey,
        projectId,
        authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
        appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
      });
  instance = getAuth(app);
  const emulator = process.env.NEXT_PUBLIC_AUTH_EMULATOR;
  if (emulator) {
    connectAuthEmulator(instance, emulator);
  }
  return instance;
}
