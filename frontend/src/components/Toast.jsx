import { CheckCircle2, AlertTriangle, X } from 'lucide-react'
export default function Toast({ toast, onClose }) {
  if (!toast) return null
  const ok = toast.type !== 'error'
  return <div className="fixed bottom-5 right-5 z-[60] w-[min(92vw,380px)] rounded-2xl border border-slate-200 bg-white p-4 shadow-2xl">
    <div className="flex gap-3">{ok?<CheckCircle2 className="mt-0.5 text-emerald-600" size={20}/>:<AlertTriangle className="mt-0.5 text-rose-600" size={20}/>}<div className="min-w-0 flex-1"><p className="font-bold text-slate-900">{ok?'Success':'Action failed'}</p><p className="mt-1 text-sm text-slate-500">{toast.message}</p></div><button onClick={onClose}><X size={17} className="text-slate-400"/></button></div>
  </div>
}
