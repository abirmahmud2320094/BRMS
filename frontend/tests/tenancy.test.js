import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getTenancyDateError,
  serializeTenancyAssignment,
  TENANCY_DATE_ERROR,
} from '../src/utils/tenancy.js'

test('blocks an end date before the start date', () => {
  assert.equal(
    getTenancyDateError({ start_date: '2026-08-20', end_date: '2026-08-06' }),
    TENANCY_DATE_ERROR,
  )
})

test('accepts valid and blank optional end dates', () => {
  assert.equal(getTenancyDateError({ start_date: '2026-08-20', end_date: '2026-08-21' }), null)
  assert.equal(getTenancyDateError({ start_date: '2026-08-20', end_date: '' }), null)
})

test('serializes native date input values for FastAPI', () => {
  const payload = serializeTenancyAssignment({
    tenant_id: 'tenant',
    shop_id: 'shop',
    start_date: '2026-08-20',
    end_date: '',
    monthly_rent: '35000',
    security_deposit: '',
    status: 'active',
    notes: '',
  })
  assert.equal(payload.start_date, '2026-08-20')
  assert.equal(payload.end_date, null)
  assert.equal(payload.monthly_rent, 35000)
  assert.equal(payload.security_deposit, 0)
})
