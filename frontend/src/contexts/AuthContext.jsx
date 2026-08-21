import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { browserLocalPersistence, onAuthStateChanged, setPersistence, signInWithEmailAndPassword, signOut } from 'firebase/auth'
import { getFirebaseAuth } from '../services/firebase'
import { api, setTokenProvider, setUnauthorizedHandler } from '../services/api'
import { endFirebaseSession, restoreAuthorizedProfile, signInAndLoadProfile } from '../services/authFlow'

const AuthContext = createContext(null)

function clearLegacyStoredTokens() {
  Object.keys(localStorage)
    .filter(key => key.startsWith('brms_') && key.endsWith('_token'))
    .forEach(key => localStorage.removeItem(key))
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState('')

  useEffect(() => {
    const firebaseAuth = getFirebaseAuth()
    clearLegacyStoredTokens()
    setTokenProvider(async (forceRefresh = false) => firebaseAuth.currentUser ? firebaseAuth.currentUser.getIdToken(forceRefresh) : null)
    setUnauthorizedHandler(async () => {
      await signOut(firebaseAuth).catch(() => {})
      setUser(null)
      setAuthError('Your session has expired. Please sign in again.')
    })
    setPersistence(firebaseAuth, browserLocalPersistence).catch(() => {
      setAuthError('Unable to preserve your session. Please sign in again.')
    })
    return onAuthStateChanged(firebaseAuth, async (firebaseUser) => {
      if (!firebaseUser) { setUser(null); setLoading(false); return }
      try {
        const profile = await restoreAuthorizedProfile({auth:firebaseAuth, firebaseUser, getProfile:()=>api.get('/auth/me'), signOutUser:signOut})
        setUser(profile)
        setAuthError('')
      } catch (error) {
        setUser(null)
        setAuthError(error.message)
      }
      finally { setLoading(false) }
    })
  }, [])

  async function login(email, password) {
    const firebaseAuth = getFirebaseAuth()
    setAuthError('')
    const profile = await signInAndLoadProfile({auth:firebaseAuth, email, password, signIn:signInWithEmailAndPassword, getProfile:()=>api.get('/auth/me'), signOutUser:signOut})
    setUser(profile)
    return profile
  }

  async function logout() {
    try { await endFirebaseSession({auth:getFirebaseAuth(), signOutUser:signOut}) }
    finally { clearLegacyStoredTokens(); setUser(null); setAuthError('') }
  }

  const value = useMemo(() => ({ user, loading, authError, clearAuthError:()=>setAuthError(''), login, logout }), [user, loading, authError])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
