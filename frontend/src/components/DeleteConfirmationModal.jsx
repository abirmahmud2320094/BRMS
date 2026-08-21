import { LoaderCircle, Trash2 } from 'lucide-react'
import Modal from './Modal'

export default function DeleteConfirmationModal({
  open,
  title,
  description,
  recordName,
  confirmLabel = 'Delete Record',
  loading = false,
  onConfirm,
  onCancel,
}) {
  return <Modal
    open={open}
    onClose={loading ? () => {} : onCancel}
    title={title}
    subtitle="Please review this permanent action carefully."
    size="max-w-lg"
  >
    <div className="flex gap-4">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-rose-50 text-rose-600"><Trash2 size={20}/></div>
      <div className="min-w-0">
        <p className="text-sm leading-6 text-slate-600">{description}</p>
        {recordName&&<p className="mt-3 break-words rounded-xl bg-slate-50 px-4 py-3 text-sm font-bold text-slate-900">{recordName}</p>}
        <p className="mt-3 text-sm font-semibold text-rose-700">This action cannot be undone.</p>
      </div>
    </div>
    <div className="mt-7 flex justify-end gap-2">
      <button type="button" className="btn-secondary" disabled={loading} onClick={onCancel}>Cancel</button>
      <button type="button" className="inline-flex items-center justify-center gap-2 rounded-xl bg-rose-600 px-4 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-60" disabled={loading} onClick={onConfirm}>
        {loading?<LoaderCircle className="animate-spin" size={16}/>:<Trash2 size={16}/>} {loading?'Deleting…':confirmLabel}
      </button>
    </div>
  </Modal>
}
