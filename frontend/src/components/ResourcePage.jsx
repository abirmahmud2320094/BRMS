import { useEffect, useMemo, useState } from 'react'
import { Plus, Pencil, Trash2, RefreshCw, ShieldAlert } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import PageHeader from './PageHeader'
import DataToolbar from './DataToolbar'
import Modal from './Modal'
import Toast from './Toast'
import Loading from './Loading'
import EmptyState from './EmptyState'
import StatusBadge from './StatusBadge'
import DeleteConfirmationModal from './DeleteConfirmationModal'
import { dateText, money, titleCase } from '../utils/format'
import { getApiErrorMessage } from '../utils/apiError'

function defaultForm(fields) {
  return Object.fromEntries(fields.map(f => [f.name, f.default ?? (f.type === 'number' ? '' : '')]))
}

function displayValue(field, value, lookups) {
  if (field.render) return field.render(value, lookups)
  if (field.kind === 'money') return money(value)
  if (field.kind === 'date') return dateText(value)
  if (field.kind === 'status') return <StatusBadge value={value}/>
  if (field.lookup) {
    const rows = lookups[field.lookup.endpoint] || []
    const match = rows.find(r => r.id === value)
    return match ? field.lookup.label(match) : '—'
  }
  return value === null || value === undefined || value === '' ? '—' : titleCase(value)
}

export default function ResourcePage({ config }) {
  const { user } = useAuth()
  const [records, setRecords] = useState([])
  const [lookups, setLookups] = useState({})
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState(defaultForm(config.formFields))
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [toast, setToast] = useState(null)

  const canWrite = (config.writeRoles || ['administrator','building_manager']).includes(user?.role)

  async function load() {
    setLoading(true)
    try {
      const endpoints = [...new Set(config.formFields.filter(f=>f.lookup).map(f=>f.lookup.endpoint))]
      const [data, ...lookupData] = await Promise.all([api.get(config.endpoint), ...endpoints.map(e=>api.get(e))])
      setRecords(data)
      setLookups(Object.fromEntries(endpoints.map((e,i)=>[e, lookupData[i]])))
    } catch (e) { setToast({type:'error', message:getApiErrorMessage(e)}) }
    finally { setLoading(false) }
  }

  useEffect(()=>{ load() }, [config.endpoint])

  const filtered = useMemo(()=> {
    if (!search) return records
    const s = search.toLowerCase()
    return records.filter(r=>JSON.stringify(r).toLowerCase().includes(s))
  }, [records, search])

  function openCreate() {
    setEditing(null)
    setForm(defaultForm(config.formFields))
    setModal(true)
  }
  function openEdit(record) {
    setEditing(record)
    const next = {}
    config.formFields.forEach(f => next[f.name] = record[f.name] ?? f.default ?? '')
    setForm(next); setModal(true)
  }

  async function submit(e) {
    e.preventDefault(); setSaving(true)
    try {
      const payload = {}
      for (const field of config.formFields) {
        let value = form[field.name]
        if (field.type === 'number') value = value === '' ? 0 : Number(value)
        if (field.optional && value === '') value = null
        payload[field.name] = value
      }
      if (editing) await api.patch(`${config.endpoint}/${editing.id}`, payload)
      else await api.post(config.endpoint, payload)
      setToast({message: editing ? `${config.singular} updated.` : `${config.singular} created.`})
      setModal(false); await load()
    } catch (e2) { setToast({type:'error', message:getApiErrorMessage(e2)}) }
    finally { setSaving(false) }
  }

  async function remove() {
    if (!deleteTarget || deleting) return
    setDeleting(true)
    try {
      await api.delete(`${config.endpoint}/${deleteTarget.id}`)
      setRecords(current => current.filter(record => record.id !== deleteTarget.id))
      setDeleteTarget(null)
      setToast({message:`${config.singular} deleted successfully.`})
      await load()
    } catch(e) {
      setToast({type:'error', message:getApiErrorMessage(e)})
    } finally {
      setDeleting(false)
    }
  }

  return <>
    <PageHeader title={config.title} subtitle={config.subtitle} actions={<><button className="btn-secondary" onClick={load}><RefreshCw size={16}/>Refresh</button>{canWrite&&<button className="btn-primary" onClick={openCreate}><Plus size={16}/>Add {config.singular}</button>}</>}/>
    {!canWrite && <div className="mb-4 flex items-center gap-2 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800"><ShieldAlert size={17}/>Your role has read-only access to this module.</div>}
    <div className="card p-4 sm:p-5">
      <DataToolbar search={search} setSearch={setSearch} right={<span className="text-xs font-semibold text-slate-400">{filtered.length} record{filtered.length!==1?'s':''}</span>}/>
      {loading ? <Loading/> : filtered.length===0 ? <EmptyState/> : <div className="table-wrap"><table className="data-table"><thead><tr>{config.columns.map(c=><th key={c.key}>{c.label}</th>)}{canWrite&&<th className="text-right">Actions</th>}</tr></thead><tbody>{filtered.map(r=><tr key={r.id}>{config.columns.map(c=><td key={c.key} className={c.className||''}>{displayValue(c, r[c.key], lookups)}</td>)}{canWrite&&<td><div className="flex justify-end gap-1"><button className="rounded-lg p-2 text-slate-400 hover:bg-sky-50 hover:text-sky-700" onClick={()=>openEdit(r)} title={`Edit ${config.singular.toLowerCase()}`} aria-label={`Edit ${config.singular.toLowerCase()}`}><Pencil size={16}/></button>{config.allowDelete!==false&&<button className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700" onClick={()=>setDeleteTarget(r)} title={`Delete ${config.singular.toLowerCase()}`} aria-label={`Delete ${config.singular.toLowerCase()}`}><Trash2 size={16}/></button>}</div></td>}</tr>)}</tbody></table></div>}
    </div>

    <Modal open={modal} onClose={()=>setModal(false)} title={`${editing?'Edit':'Add'} ${config.singular}`} subtitle="Fields marked required must be completed before saving.">
      <form onSubmit={submit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {config.formFields.map(field => <div key={field.name} className={field.full?'sm:col-span-2':''}><label className="label">{field.label}{!field.optional&&' *'}</label>
          {field.type === 'textarea' ? <textarea className="field min-h-28 resize-y" required={!field.optional} value={form[field.name]??''} onChange={e=>setForm({...form,[field.name]:e.target.value})}/>
          : field.type === 'select' ? <select className="field" required={!field.optional} value={form[field.name]??''} onChange={e=>setForm({...form,[field.name]:e.target.value})}><option value="">Select {field.label}</option>{(field.options ? field.options : (lookups[field.lookup?.endpoint]||[]).map(x=>({value:x.id,label:field.lookup.label(x)}))).map(o=><option key={o.value} value={o.value}>{o.label}</option>)}</select>
          : <input className="field" type={field.type||'text'} step={field.type==='number'?'0.01':undefined} required={!field.optional} value={form[field.name]??''} onChange={e=>setForm({...form,[field.name]:e.target.value})} placeholder={field.placeholder||''}/>} 
        </div>)}
        <div className="sm:col-span-2 mt-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={()=>setModal(false)}>Cancel</button><button className="btn-primary" disabled={saving}>{saving?'Saving…':editing?'Save changes':`Create ${config.singular}`}</button></div>
      </form>
    </Modal>
    <DeleteConfirmationModal open={!!deleteTarget} title={`Delete ${config.singular}?`} description={config.deleteDescription || `Are you sure you want to permanently delete this ${config.singular.toLowerCase()}?`} recordName={deleteTarget ? config.rowName(deleteTarget) : ''} confirmLabel={`Delete ${config.deleteLabel || config.singular}`} loading={deleting} onConfirm={remove} onCancel={()=>setDeleteTarget(null)}/>
    <Toast toast={toast} onClose={()=>setToast(null)}/>
  </>
}
