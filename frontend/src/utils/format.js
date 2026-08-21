export const money = (value = 0) => new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', maximumFractionDigits: 0 }).format(Number(value || 0))
export const dateText = (value) => value ? new Intl.DateTimeFormat('en-BD', { day: '2-digit', month: 'short', year: 'numeric' }).format(new Date(value)) : '—'
export const monthLabel = (value) => {
  if (!value) return '—'
  const [y, m] = value.split('-')
  return new Intl.DateTimeFormat('en', { month: 'long', year: 'numeric' }).format(new Date(Number(y), Number(m)-1, 1))
}
export const titleCase = (value='') => String(value).replaceAll('_',' ').replace(/\b\w/g, c => c.toUpperCase())
