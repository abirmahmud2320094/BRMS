import { initializeApp, getApps } from 'firebase/app'
import { getAuth } from 'firebase/auth'

let authInstance = null
export function getFirebaseAuth() {
  if (authInstance) return authInstance
  const config = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID,
  }
  if (!config.apiKey || !config.projectId) throw new Error('Firebase frontend configuration is missing. Copy .env.example to .env and add your Firebase Web App values.')
  const app = getApps().length ? getApps()[0] : initializeApp(config)
  authInstance = getAuth(app)
  return authInstance
}
