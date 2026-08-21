import { useEffect, useState } from 'react'
import { Pencil, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import PageHeader from '../components/PageHeader'
import Modal from '../components/Modal'
import DeleteConfirmationModal from '../components/DeleteConfirmationModal'
import Toast from '../components/Toast'
import Loading from '../components/Loading'
import StatusBadge from '../components/StatusBadge'
import { titleCase } from '../utils/format'
import { getApiErrorMessage } from '../utils/apiError'

const empty = {name:'', email:'', password:'', role:'building_manager', status:'active'}

export default function UsersPage() {
  const { user } = useAuth()
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [form, setForm] = useState(empty)
  const [toast, setToast] = useState(null)

  async function load() {
    setLoading(true)
    try { setRows(await api.get('/users')) }
    catch (error) { setToast({type:'error', message:getApiErrorMessage(error)}) }
    finally { setLoading(false) }
  }

  useEffect(()=>{ load() }, [])

  function edit(record) {
    setEditing(record)
    setForm({name:record.name, email:record.email, password:'', role:record.role, status:record.status})
    setModal(true)
  }

  async function save(event) {
    event.preventDefault()
    try {
      if (editing) await api.patch(`/users/${editing.id}`, {name:form.name, role:form.role, status:form.status})
      else await api.post('/users', form)
      setModal(false)
      setToast({message:editing?'User access updated.':'Firebase user created.'})
      await load()
    } catch (error) {
      setToast({type:'error', message:getApiErrorMessage(error)})
    }
  }

  async function remove() {
    if (!deleteTarget || deleting) return
    setDeleting(true)
    try {
      await api.delete(`/users/${deleteTarget.id}`)
      setRows(current => current.filter(record => record.id !== deleteTarget.id))
      setDeleteTarget(null)
      setToast({message:'User deleted successfully.'})
      await load()
    } catch (error) {
      setToast({type:'error', message:getApiErrorMessage(error)})
    } finally {
      setDeleting(false)
    }
  }

  return <>
    <PageHeader title="User Access Control" subtitle="Administrator-only role and account lifecycle management." actions={<>
      <button className="btn-secondary" onClick={load}><RefreshCw size={16}/>Refresh</button>
      <button className="btn-primary" onClick={()=>{setEditing(null);setForm(empty);setModal(true)}}><Plus size={16}/>Create user</button>
    </>}/>
    <div className="card p-5">
      {loading?<Loading/>:<div className="table-wrap"><table className="data-table">
        <thead><tr><th>User</th><th>Email</th><th>Role</th><th>Status</th><th className="text-right">Actions</th></tr></thead>
        <tbody>{rows.map(record=><tr key={record.id}>
          <td className="font-bold text-slate-900">{record.name}</td><td>{record.email}</td><td>{titleCase(record.role)}</td><td><StatusBadge value={record.status}/></td>
          <td><div className="flex justify-end gap-1">
            <button className="rounded-lg p-2 text-slate-400 hover:bg-sky-50 hover:text-sky-700" onClick={()=>edit(record)} title="Edit user" aria-label={`Edit ${record.name}`}><Pencil size={16}/></button>
            {record.id!==user?.uid&&<button className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700" onClick={()=>setDeleteTarget(record)} title="Delete user" aria-label={`Delete ${record.name}`}><Trash2 size={16}/></button>}
          </div></td>
        </tr>)}</tbody>
      </table></div>}
    </div>
    <Modal open={modal} onClose={()=>setModal(false)} title={editing?'Edit user access':'Create authorized user'}>
      <form onSubmit={save} className="grid gap-4 sm:grid-cols-2">
        <Field label="Full name" name="name" form={form} set={setForm}/><Field label="Email" name="email" type="email" form={form} set={setForm} disabled={!!editing}/>
        {!editing&&<Field label="Temporary password" name="password" type="password" form={form} set={setForm}/>}
        <div><label className="label">Role *</label><select className="field" value={form.role} onChange={event=>setForm({...form,role:event.target.value})}><option value="administrator">Administrator</option><option value="building_manager">Building Manager</option><option value="accountant">Accountant</option></select></div>
        <div><label className="label">Status *</label><select className="field" value={form.status} onChange={event=>setForm({...form,status:event.target.value})}><option value="active">Active</option><option value="inactive">Inactive</option></select></div>
        <div className="sm:col-span-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={()=>setModal(false)}>Cancel</button><button className="btn-primary">{editing?'Save access':'Create Firebase user'}</button></div>
      </form>
    </Modal>
    <DeleteConfirmationModal open={!!deleteTarget} title="Delete User?" description="This will revoke the user's BRMS access and disable the linked Firebase Authentication account." recordName={deleteTarget ? `${deleteTarget.name} • ${deleteTarget.email}` : ''} confirmLabel="Delete User" loading={deleting} onConfirm={remove} onCancel={()=>setDeleteTarget(null)}/>
    <Toast toast={toast} onClose={()=>setToast(null)}/>
  </>
}

function Field({label, name, form, set, type='text', disabled}) {
  return <div><label className="label">{label} *</label><input className="field disabled:bg-slate-100" disabled={disabled} required type={type} value={form[name]} onChange={event=>set({...form,[name]:event.target.value})}/></div>
}
