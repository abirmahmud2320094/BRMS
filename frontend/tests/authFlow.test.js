import test from 'node:test'
import assert from 'node:assert/strict'

import {
  endFirebaseSession,
  getFirebaseAuthErrorMessage,
  restoreAuthorizedProfile,
  signInAndLoadProfile,
} from '../src/services/authFlow.js'
import { hasAllowedRole, isAdministrator } from '../src/utils/access.js'

test('loads the backend BRMS profile after Firebase login', async () => {
  const calls = []
  const profile = {uid:'firebase-user', role:'building_manager', status:'active'}
  const result = await signInAndLoadProfile({
    auth:{name:'auth'}, email:'manager@brms.com', password:'not-recorded',
    signIn:async (...args)=>calls.push(['signIn', ...args]),
    getProfile:async ()=>{calls.push(['profile']); return profile},
    signOutUser:async ()=>calls.push(['signOut']),
  })
  assert.equal(result, profile)
  assert.deepEqual(calls.map(call=>call[0]), ['signIn','profile'])
})

test('maps Firebase login failures to readable messages', async () => {
  await assert.rejects(
    signInAndLoadProfile({
      auth:{}, email:'invalid@example.com', password:'invalid',
      signIn:async ()=>{throw {code:'auth/invalid-credential'}},
      getProfile:async ()=>({}), signOutUser:async ()=>{},
    }),
    {message:'Invalid email or password.'},
  )
  assert.equal(getFirebaseAuthErrorMessage({code:'auth/user-disabled'}), 'This account has been disabled. Contact the administrator.')
  assert.equal(getFirebaseAuthErrorMessage({code:'auth/network-request-failed'}), 'Unable to connect. Check your internet connection and try again.')
})

test('signs out authenticated users without an active BRMS profile', async () => {
  let signedOut = false
  await assert.rejects(
    restoreAuthorizedProfile({
      auth:{}, firebaseUser:{uid:'unregistered'},
      getProfile:async ()=>{const error=new Error('No profile');error.status=403;error.body={detail:'No BRMS user profile is assigned to this account'};throw error},
      signOutUser:async ()=>{signedOut=true},
    }),
    {message:'Your account does not have access to BRMS. Contact the administrator.'},
  )
  assert.equal(signedOut, true)
})

test('restores sessions, logs out, and enforces role helpers', async () => {
  const profile = {uid:'accountant', role:'accountant', status:'active'}
  assert.equal(await restoreAuthorizedProfile({auth:{}, firebaseUser:{uid:'accountant'}, getProfile:async()=>profile, signOutUser:async()=>{}}), profile)
  assert.equal(await restoreAuthorizedProfile({auth:{}, firebaseUser:null, getProfile:async()=>profile, signOutUser:async()=>{}}), null)
  let logoutCalled = false
  assert.equal(await endFirebaseSession({auth:{}, signOutUser:async()=>{logoutCalled=true}}), null)
  assert.equal(logoutCalled, true)
  assert.equal(hasAllowedRole(profile, ['accountant']), true)
  assert.equal(hasAllowedRole(profile, ['administrator']), false)
  assert.equal(isAdministrator({role:'administrator'}), true)
  assert.equal(isAdministrator(profile), false)
})
