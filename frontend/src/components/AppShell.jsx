import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { Building2, LayoutDashboard, Layers3, Store, UsersRound, ReceiptText, Zap, Wrench, BarChart3, UserCog, Menu, X, LogOut, Bell, ChevronRight } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { titleCase } from '../utils/format'
import { hasAllowedRole } from '../utils/access'

const nav = [
  ['Dashboard','/',LayoutDashboard,['administrator','building_manager','accountant']],
  ['Building','/building',Building2,['administrator','building_manager','accountant']],
  ['Floors','/floors',Layers3,['administrator','building_manager','accountant']],
  ['Shops','/shops',Store,['administrator','building_manager','accountant']],
  ['Tenants','/tenants',UsersRound,['administrator','building_manager','accountant']],
  ['Rent Collection','/rent',ReceiptText,['administrator','building_manager','accountant']],
  ['Utility Bills','/utilities',Zap,['administrator','building_manager','accountant']],
  ['Maintenance','/maintenance',Wrench,['administrator','building_manager','accountant']],
  ['Reports','/reports',BarChart3,['administrator','building_manager','accountant']],
  ['User Access','/users',UserCog,['administrator']],
]

export default function AppShell() {
  const [mobile, setMobile] = useState(false)
  const { user, logout } = useAuth()
  const location = useLocation()
  const visible = nav.filter(n=>hasAllowedRole(user,n[3]))
  const current = visible.find(n=> n[1] === location.pathname)?.[0] || 'Workspace'
  return <div className="min-h-screen bg-slate-50">
    {mobile && <div className="fixed inset-0 z-30 bg-slate-950/40 backdrop-blur-sm lg:hidden" onClick={()=>setMobile(false)}/>} 
    <aside className={`fixed inset-y-0 left-0 z-40 w-72 transform bg-slate-950 text-white transition lg:translate-x-0 ${mobile?'translate-x-0':'-translate-x-full'}`}>
      <div className="flex h-20 items-center border-b border-white/10 px-6"><div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400 to-cyan-300 text-slate-950"><Building2 size={21}/></div><div className="ml-3"><p className="text-sm font-extrabold tracking-wide">BRMS</p><p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Rental Intelligence</p></div><button className="ml-auto lg:hidden" onClick={()=>setMobile(false)}><X size={20}/></button></div>
      <div className="px-4 py-5"><p className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">Management</p><nav className="mt-3 space-y-1">{visible.map(([label,path,Icon])=><NavLink key={path} to={path} end={path==='/'} onClick={()=>setMobile(false)} className={({isActive})=>`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${isActive?'bg-white text-slate-950 shadow-lg':'text-slate-300 hover:bg-white/8 hover:text-white'}`}><Icon size={18}/>{label}</NavLink>)}</nav></div>
      <div className="absolute bottom-0 left-0 right-0 border-t border-white/10 p-4"><div className="rounded-2xl bg-white/5 p-3"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl bg-sky-500/20 font-extrabold text-sky-300">{user?.name?.[0]||'U'}</div><div className="min-w-0 flex-1"><p className="truncate text-sm font-bold">{user?.name}</p><p className="truncate text-[11px] text-slate-400">{titleCase(user?.role)}</p></div><button onClick={logout} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white" title="Logout"><LogOut size={17}/></button></div></div></div>
    </aside>
    <div className="lg:pl-72">
      <header className="sticky top-0 z-20 flex h-20 items-center border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl sm:px-6 lg:px-8"><button className="mr-3 rounded-xl border border-slate-200 p-2 lg:hidden" onClick={()=>setMobile(true)}><Menu size={20}/></button><div className="flex items-center gap-2 text-sm text-slate-500"><span>BRMS</span><ChevronRight size={14}/><span className="font-semibold text-slate-800">{current}</span></div><div className="ml-auto flex items-center gap-3"><button className="relative rounded-xl border border-slate-200 p-2.5 text-slate-500 hover:bg-slate-50"><Bell size={18}/><span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-sky-500 ring-2 ring-white"/></button><div className="hidden text-right sm:block"><p className="text-xs font-bold text-slate-900">{user?.name}</p><p className="text-[10px] uppercase tracking-wide text-slate-400">{titleCase(user?.role)}</p></div></div></header>
      <main className="p-4 sm:p-6 lg:p-8"><Outlet/></main>
    </div>
  </div>
}
