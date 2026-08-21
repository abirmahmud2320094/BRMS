import { useEffect, useMemo, useState } from 'react'
import { DoorOpen, Pencil, Plus, RefreshCw, Trash2, UserRoundPlus } from 'lucide-react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import PageHeader from '../components/PageHeader'
import DataToolbar from '../components/DataToolbar'
import Modal from '../components/Modal'
import DeleteConfirmationModal from '../components/DeleteConfirmationModal'
import Toast from '../components/Toast'
import Loading from '../components/Loading'
import EmptyState from '../components/EmptyState'
import StatusBadge from '../components/StatusBadge'
import { money, dateText } from '../utils/format'
import { getApiErrorMessage } from '../utils/apiError'
import { getTenancyDateError, serializeTenancyAssignment } from '../utils/tenancy'

const tenantEmpty = {name:'', business_name:'', phone:'', email:'', national_id:'', address:'', status:'active'}
const tenancyEmpty = {tenant_id:'', shop_id:'', start_date:'', end_date:'', monthly_rent:'', security_deposit:'', status:'active', notes:''}

export default function TenantsPage() {
  const { user } = useAuth()
  const canWrite = ['administrator','building_manager'].includes(user?.role)
  const [tenants, setTenants] = useState([])
  const [shops, setShops] = useState([])
  const [tenancies, setTenancies] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [tenantModal, setTenantModal] = useState(false)
  const [assignModal, setAssignModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [endTarget, setEndTarget] = useState(null)
  const [ending, setEnding] = useState(false)
  const [form, setForm] = useState(tenantEmpty)
  const [assign, setAssign] = useState(tenancyEmpty)
  const [toast, setToast] = useState(null)

  async function load() {
    setLoading(true)
    try {
      const [tenantRows, shopRows, tenancyRows] = await Promise.all([api.get('/tenants'), api.get('/shops'), api.get('/tenancies')])
      setTenants(tenantRows); setShops(shopRows); setTenancies(tenancyRows)
    } catch (error) {
      setToast({type:'error', message:getApiErrorMessage(error)})
    } finally { setLoading(false) }
  }

  useEffect(()=>{ load() }, [])

  const filtered = useMemo(()=>tenants.filter(tenant=>!search||JSON.stringify(tenant).toLowerCase().includes(search.toLowerCase())), [tenants,search])
  const activeByTenant = Object.fromEntries(tenancies.filter(tenancy=>tenancy.status==='active').map(tenancy=>[tenancy.tenant_id, tenancy]))
  const shopMap = Object.fromEntries(shops.map(shop=>[shop.id, shop]))
  const tenantMap = Object.fromEntries(tenants.map(tenant=>[tenant.id, tenant]))

  function editTenant(tenant) {
    setEditing(tenant)
    setForm(Object.fromEntries(Object.keys(tenantEmpty).map(key=>[key, tenant[key]??''])))
    setTenantModal(true)
  }

  async function saveTenant(event) {
    event.preventDefault()
    try {
      const payload = {...form, email:form.email||null, national_id:form.national_id||null, address:form.address||null, business_name:form.business_name||null}
      if (editing) await api.patch(`/tenants/${editing.id}`, payload)
      else await api.post('/tenants', payload)
      setTenantModal(false)
      setToast({message:editing?'Tenant updated.':'Tenant registered.'})
      await load()
    } catch (error) { setToast({type:'error', message:getApiErrorMessage(error)}) }
  }

  function openAssign(tenant) {
    setAssign({...tenancyEmpty, tenant_id:tenant.id, start_date:new Date().toISOString().slice(0,10)})
    setAssignModal(true)
  }

  async function saveAssign(event) {
    event.preventDefault()
    const dateError = getTenancyDateError(assign)
    if (dateError) { setToast({type:'error', message:dateError}); return }
    try {
      await api.post('/tenancies', serializeTenancyAssignment(assign))
      setAssignModal(false)
      setToast({message:'Shop assigned successfully.'})
      await load()
    } catch (error) { setToast({type:'error', message:getApiErrorMessage(error)}) }
  }

  async function endAssignment() {
    if (!endTarget || ending) return
    setEnding(true)
    try {
      await api.post(`/tenancies/${endTarget.id}/end`, {})
      setEndTarget(null)
      setToast({message:'Tenancy ended and shop released.'})
      await load()
    } catch (error) {
      setToast({type:'error', message:getApiErrorMessage(error)})
    } finally { setEnding(false) }
  }

  async function remove() {
    if (!deleteTarget || deleting) return
    setDeleting(true)
    const { type, record } = deleteTarget
    try {
      await api.delete(type==='tenant' ? `/tenants/${record.id}` : `/tenancies/${record.id}`)
      if (type==='tenant') setTenants(current=>current.filter(item=>item.id!==record.id))
      else setTenancies(current=>current.filter(item=>item.id!==record.id))
      setDeleteTarget(null)
      setToast({message:`${type==='tenant'?'Tenant':'Tenancy'} deleted successfully.`})
      await load()
    } catch (error) {
      setToast({type:'error', message:getApiErrorMessage(error)})
    } finally { setDeleting(false) }
  }

  return <>
    <PageHeader title="Tenant & Assignment Hub" subtitle="Keep tenant profiles and shop assignments connected in one operational workspace." actions={<>
      <button className="btn-secondary" onClick={load}><RefreshCw size={16}/>Refresh</button>
      {canWrite&&<button className="btn-primary" onClick={()=>{setEditing(null);setForm(tenantEmpty);setTenantModal(true)}}><Plus size={16}/>Register tenant</button>}
    </>}/>

    <div className="card p-4 sm:p-5">
      <DataToolbar search={search} setSearch={setSearch} right={<span className="text-xs font-semibold text-slate-400">{filtered.length} tenants</span>}/>
      {loading?<Loading/>:!filtered.length?<EmptyState/>:<div className="table-wrap"><table className="data-table">
        <thead><tr><th>Tenant / Business</th><th>Contact</th><th>Current Shop</th><th>Rent</th><th>Status</th>{canWrite&&<th className="text-right">Actions</th>}</tr></thead>
        <tbody>{filtered.map(tenant=>{const active=activeByTenant[tenant.id];const shop=active?shopMap[active.shop_id]:null;return <tr key={tenant.id}>
          <td><p className="font-bold text-slate-900">{tenant.business_name||tenant.name}</p><p className="mt-0.5 text-xs text-slate-400">{tenant.name}</p></td>
          <td><p>{tenant.phone}</p><p className="text-xs text-slate-400">{tenant.email||'No email'}</p></td>
          <td>{shop?<><p className="font-semibold">Shop {shop.shop_number}</p><p className="text-xs text-slate-400">Since {dateText(active.start_date)}</p></>:<span className="text-slate-400">Unassigned</span>}</td>
          <td>{active?money(active.monthly_rent):'—'}</td><td><StatusBadge value={tenant.status}/></td>
          {canWrite&&<td><div className="flex justify-end gap-1">
            <button onClick={()=>editTenant(tenant)} className="rounded-lg p-2 text-slate-400 hover:bg-sky-50 hover:text-sky-700" title="Edit tenant" aria-label={`Edit ${tenant.name}`}><Pencil size={16}/></button>
            {active?<button onClick={()=>setEndTarget(active)} className="rounded-lg p-2 text-slate-400 hover:bg-amber-50 hover:text-amber-700" title="End tenancy" aria-label={`End tenancy for ${tenant.name}`}><DoorOpen size={16}/></button>:<button onClick={()=>openAssign(tenant)} className="rounded-lg p-2 text-slate-400 hover:bg-emerald-50 hover:text-emerald-700" title="Assign shop" aria-label={`Assign shop to ${tenant.name}`}><UserRoundPlus size={16}/></button>}
            <button onClick={()=>setDeleteTarget({type:'tenant',record:tenant})} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700" title="Delete tenant" aria-label={`Delete ${tenant.name}`}><Trash2 size={16}/></button>
          </div></td>}
        </tr>})}</tbody>
      </table></div>}
    </div>

    <div className="card mt-5 p-4 sm:p-5">
      <div className="mb-4"><p className="panel-title">Shop Assignments</p><p className="mt-1 text-sm text-slate-500">Current and historical tenancy records.</p></div>
      {loading?<Loading/>:!tenancies.length?<EmptyState/>:<div className="table-wrap"><table className="data-table">
        <thead><tr><th>Tenant</th><th>Shop</th><th>Period</th><th>Monthly Rent</th><th>Status</th>{canWrite&&<th className="text-right">Actions</th>}</tr></thead>
        <tbody>{tenancies.map(tenancy=>{const tenant=tenantMap[tenancy.tenant_id];const shop=shopMap[tenancy.shop_id];return <tr key={tenancy.id}>
          <td className="font-bold text-slate-900">{tenancy.tenant_name||tenant?.business_name||tenant?.name||'Unknown tenant'}</td>
          <td>Shop {tenancy.shop_number||shop?.shop_number||'—'}</td><td>{dateText(tenancy.start_date)} — {tenancy.end_date?dateText(tenancy.end_date):'Present'}</td><td>{money(tenancy.monthly_rent)}</td><td><StatusBadge value={tenancy.status}/></td>
          {canWrite&&<td><div className="flex justify-end gap-1">{tenancy.status==='active'&&<button onClick={()=>setEndTarget(tenancy)} className="rounded-lg p-2 text-slate-400 hover:bg-amber-50 hover:text-amber-700" title="End tenancy" aria-label="End tenancy"><DoorOpen size={16}/></button>}<button onClick={()=>setDeleteTarget({type:'tenancy',record:tenancy})} className="rounded-lg p-2 text-slate-400 hover:bg-rose-50 hover:text-rose-700" title="Delete tenancy" aria-label="Delete tenancy"><Trash2 size={16}/></button></div></td>}
        </tr>})}</tbody>
      </table></div>}
    </div>

    <Modal open={tenantModal} onClose={()=>setTenantModal(false)} title={editing?'Edit tenant':'Register tenant'}><form onSubmit={saveTenant} className="grid gap-4 sm:grid-cols-2">
      <Field label="Tenant name" name="name" form={form} set={setForm}/><Field label="Business name" name="business_name" form={form} set={setForm} optional/><Field label="Phone" name="phone" form={form} set={setForm}/><Field label="Email" name="email" type="email" form={form} set={setForm} optional/><Field label="National ID" name="national_id" form={form} set={setForm} optional/>
      <div><label className="label">Status *</label><select className="field" value={form.status} onChange={event=>setForm({...form,status:event.target.value})}><option value="active">Active</option><option value="inactive">Inactive</option></select></div>
      <div className="sm:col-span-2"><label className="label">Address</label><textarea className="field" value={form.address||''} onChange={event=>setForm({...form,address:event.target.value})}/></div>
      <div className="sm:col-span-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={()=>setTenantModal(false)}>Cancel</button><button className="btn-primary">{editing?'Save changes':'Register tenant'}</button></div>
    </form></Modal>

    <Modal open={assignModal} onClose={()=>setAssignModal(false)} title="Assign tenant to shop" subtitle="Only available shops can receive an active tenancy."><form onSubmit={saveAssign} className="grid gap-4 sm:grid-cols-2">
      <div className="sm:col-span-2"><label className="label">Available shop *</label><select className="field" required value={assign.shop_id} onChange={event=>{const shop=shops.find(item=>item.id===event.target.value);setAssign({...assign,shop_id:event.target.value,monthly_rent:shop?.monthly_rent||''})}}><option value="">Select shop</option>{shops.filter(shop=>shop.status==='available').map(shop=><option key={shop.id} value={shop.id}>Shop {shop.shop_number} • {shop.name||'Unnamed'} • {money(shop.monthly_rent)}</option>)}</select></div>
      <Field label="Start date" name="start_date" type="date" form={assign} set={setAssign}/><Field label="End date" name="end_date" type="date" form={assign} set={setAssign} optional/><Field label="Monthly rent (BDT)" name="monthly_rent" type="number" form={assign} set={setAssign}/><Field label="Security deposit (BDT)" name="security_deposit" type="number" form={assign} set={setAssign} optional/>
      <div className="sm:col-span-2"><label className="label">Notes</label><textarea className="field" value={assign.notes||''} onChange={event=>setAssign({...assign,notes:event.target.value})}/></div>
      <div className="sm:col-span-2 flex justify-end gap-2"><button type="button" className="btn-secondary" onClick={()=>setAssignModal(false)}>Cancel</button><button className="btn-primary">Create assignment</button></div>
    </form></Modal>

    <Modal open={!!endTarget} onClose={ending?()=>{}:()=>setEndTarget(null)} title="End Tenancy?" subtitle="The linked shop will become available for a new assignment.">
      <p className="text-sm leading-6 text-slate-600">End this active tenancy and release Shop {endTarget?.shop_number||shopMap[endTarget?.shop_id]?.shop_number||'—'}?</p>
      <div className="mt-7 flex justify-end gap-2"><button className="btn-secondary" disabled={ending} onClick={()=>setEndTarget(null)}>Cancel</button><button className="btn-primary" disabled={ending} onClick={endAssignment}>{ending?'Ending…':'End Tenancy'}</button></div>
    </Modal>

    <DeleteConfirmationModal open={!!deleteTarget} title={`Delete ${deleteTarget?.type==='tenant'?'Tenant':'Tenancy'}?`} description={deleteTarget?.type==='tenant'?'The tenant can only be deleted when no active or historical tenancy records depend on it.':'The assignment can only be deleted when no financial records depend on it. An active shop will be released automatically.'} recordName={deleteTarget?.type==='tenant'?(deleteTarget.record.business_name||deleteTarget.record.name):`${deleteTarget?.record.tenant_name||'Tenant'} • Shop ${deleteTarget?.record.shop_number||'—'}`} confirmLabel={`Delete ${deleteTarget?.type==='tenant'?'Tenant':'Tenancy'}`} loading={deleting} onConfirm={remove} onCancel={()=>setDeleteTarget(null)}/>
    <Toast toast={toast} onClose={()=>setToast(null)}/>
  </>
}

function Field({label, name, form, set, type='text', optional}) {
  return <div><label className="label">{label}{!optional&&' *'}</label><input className="field" required={!optional} type={type} value={form[name]??''} onChange={event=>set({...form,[name]:event.target.value})}/></div>
}
