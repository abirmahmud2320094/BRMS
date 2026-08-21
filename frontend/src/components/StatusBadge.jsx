import { titleCase } from '../utils/format'

const styles = {
  available: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
  paid: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
  active: 'bg-sky-50 text-sky-700 ring-1 ring-sky-200',
  occupied: 'bg-violet-50 text-violet-700 ring-1 ring-violet-200',
  partial: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
  unpaid: 'bg-rose-50 text-rose-700 ring-1 ring-rose-200',
  inactive: 'bg-slate-100 text-slate-600 ring-1 ring-slate-200',
  ended: 'bg-slate-100 text-slate-600 ring-1 ring-slate-200',
  completed: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
  planned: 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200',
  in_progress: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
}
export default function StatusBadge({ value }) {
  return <span className={`badge ${styles[value] || 'bg-slate-100 text-slate-600 ring-1 ring-slate-200'}`}><span className="h-1.5 w-1.5 rounded-full bg-current" />{titleCase(value)}</span>
}
