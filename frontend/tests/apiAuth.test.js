import test from 'node:test'
import assert from 'node:assert/strict'

import { api, setTokenProvider, setUnauthorizedHandler } from '../src/services/api.js'

test('refreshes a stale Firebase ID token once after a 401', async () => {
  const originalFetch = globalThis.fetch
  const refreshFlags = []
  const authHeaders = []
  let requestCount = 0
  setTokenProvider(async forceRefresh=>{refreshFlags.push(forceRefresh);return forceRefresh?'fresh-token':'stale-token'})
  setUnauthorizedHandler(async ()=>assert.fail('unauthorized handler should not run after a successful refresh'))
  globalThis.fetch = async (_url, options) => {
    requestCount += 1
    authHeaders.push(options.headers.Authorization)
    return requestCount === 1
      ? new Response(JSON.stringify({detail:'expired'}), {status:401, headers:{'Content-Type':'application/json'}})
      : new Response(JSON.stringify({ok:true}), {status:200, headers:{'Content-Type':'application/json'}})
  }
  try {
    assert.deepEqual(await api.get('/token-refresh-test'), {ok:true})
    assert.deepEqual(refreshFlags, [false,true])
    assert.deepEqual(authHeaders, ['Bearer stale-token','Bearer fresh-token'])
  } finally {
    globalThis.fetch = originalFetch
    setTokenProvider(async ()=>null)
    setUnauthorizedHandler(async ()=>{})
  }
})
