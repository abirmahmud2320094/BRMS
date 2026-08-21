import test from 'node:test'
import assert from 'node:assert/strict'

import { getApiErrorMessage } from '../src/utils/apiError.js'

test('extracts string details', () => {
  assert.equal(getApiErrorMessage({ detail: 'Shop not found' }), 'Shop not found')
})

test('extracts FastAPI validation arrays without object coercion', () => {
  const error = {
    detail: [{
      loc: ['body', 'end_date'],
      msg: 'Value error, End date must be later than the start date',
      type: 'value_error',
    }],
  }
  assert.equal(getApiErrorMessage(error), 'End date must be later than the start date')
  assert.notEqual(getApiErrorMessage(error), '[object Object]')
})

test('extracts nested object details and normal Error messages', () => {
  assert.equal(getApiErrorMessage({ detail: { message: 'Invalid assignment' } }), 'Invalid assignment')
  assert.equal(getApiErrorMessage(new Error('Permission denied')), 'Permission denied')
})

test('formats missing-field validation messages', () => {
  assert.equal(
    getApiErrorMessage({ detail: [{ loc: ['body', 'shop_id'], msg: 'Field required' }] }),
    'Shop ID is required.',
  )
})

test('formats fetch and network errors', () => {
  assert.equal(
    getApiErrorMessage(new TypeError('Failed to fetch')),
    'Unable to reach the server. Check your connection and try again.',
  )
})
