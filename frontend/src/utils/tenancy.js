export const TENANCY_DATE_ERROR = 'End date must be later than the start date.'

export function getTenancyDateError({ start_date: startDate, end_date: endDate }) {
  if (startDate && endDate && endDate < startDate) return TENANCY_DATE_ERROR
  return null
}

export function serializeTenancyAssignment(assignment) {
  return {
    ...assignment,
    start_date: assignment.start_date,
    end_date: assignment.end_date || null,
    monthly_rent: Number(assignment.monthly_rent),
    security_deposit: Number(assignment.security_deposit || 0),
    notes: assignment.notes || null,
  }
}
