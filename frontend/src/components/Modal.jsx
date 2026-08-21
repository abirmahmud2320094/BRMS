import { X } from 'lucide-react'
export default function Modal({ open, title, subtitle, children, onClose, size='max-w-2xl' }) {
  if (!open) return null
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4 backdrop-blur-sm" onMouseDown={(e)=>e.target===e.currentTarget&&onClose()}>
    <div role="dialog" aria-modal="true" aria-label={title} className={`max-h-[92vh] w-full ${size} overflow-hidden rounded-3xl border border-white/10 bg-white shadow-2xl`}>
      <div className="flex items-start justify-between border-b border-slate-100 px-6 py-5">
        <div><h3 className="text-lg font-extrabold text-slate-900">{title}</h3>{subtitle&&<p className="mt-1 text-sm text-slate-500">{subtitle}</p>}</div>
        <button className="rounded-xl p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700" onClick={onClose} aria-label="Close dialog"><X size={18}/></button>
      </div>
      <div className="max-h-[calc(92vh-84px)] overflow-y-auto p-6">{children}</div>
    </div>
  </div>
}
