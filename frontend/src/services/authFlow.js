import { getApiErrorMessage } from '../utils/apiError.js'

const INVALID_CREDENTIAL_CODES = new Set([
  'auth/invalid-credential',
  'auth/invalid-email',
  'auth/missing-password',
  'auth/user-not-found',
  'auth/wrong-password',
])

export function getFirebaseAuthErrorMessage(error) {
  if (INVALID_CREDENTIAL_CODES.has(error?.code)) return 'Invalid email or password.'
  if (error?.code === 'auth/user-disabled') return 'This account has been disabled. Contact the administrator.'
  if (error?.code === 'auth/network-request-failed') return 'Unable to connect. Check your internet connection and try again.'
  if (error?.code === 'auth/too-many-requests') return 'Too many sign-in attempts. Please wait and try again.'

  const message = getApiErrorMessage(error)
  if (/no brms user profile/i.test(message)) return 'Your account does not have access to BRMS. Contact the administrator.'
  if (/account is inactive/i.test(message)) return 'This account is inactive. Contact the administrator.'
  if (/unable to reach the server/i.test(message)) return message
  return 'Unable to sign in. Please try again.'
}

async function loadAuthorizedProfile({ auth, getProfile, signOutUser }) {
  try {
    return await getProfile()
  } catch (error) {
    await signOutUser(auth).catch(() => {})
    throw new Error(getFirebaseAuthErrorMessage(error))
  }
}

export async function signInAndLoadProfile({ auth, email, password, signIn, getProfile, signOutUser }) {
  try {
    await signIn(auth, email, password)
  } catch (error) {
    throw new Error(getFirebaseAuthErrorMessage(error))
  }
  return loadAuthorizedProfile({ auth, getProfile, signOutUser })
}

export async function restoreAuthorizedProfile({ auth, firebaseUser, getProfile, signOutUser }) {
  if (!firebaseUser) return null
  return loadAuthorizedProfile({ auth, getProfile, signOutUser })
}

export async function endFirebaseSession({ auth, signOutUser }) {
  await signOutUser(auth)
  return null
}
