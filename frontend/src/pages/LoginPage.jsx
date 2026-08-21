import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Building2, ArrowRight, ShieldCheck, BarChart3, Store, Sparkles, Eye, EyeOff } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { user, login, authError, clearAuthError } = useAuth()
  const nav = useNavigate()
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [showPassword,setShowPassword]=useState(false)
  const [error,setError]=useState(''); const [loading,setLoading]=useState(false)
  if (user) return <Navigate to="/" replace/>
  async function submit(e){e.preventDefault();if(loading)return;setLoading(true);setError('');clearAuthError();try{await login(email,password);nav('/')}catch(err){setError(err.message)}finally{setLoading(false)}}
  return <div className="min-h-screen bg-slate-950 lg:grid lg:grid-cols-[1.08fr_.92fr]">
    <section className="relative hidden overflow-hidden p-12 lg:flex lg:flex-col lg:justify-between">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(14,165,233,.28),transparent_32%),radial-gradient(circle_at_80%_70%,rgba(34,211,238,.16),transparent_34%)]"/>
      <div className="absolute -right-20 top-32 h-80 w-80 rounded-full border border-sky-400/20"/><div className="absolute right-14 top-48 h-56 w-56 rounded-full border border-cyan-300/20"/>
      <div className="relative"><div className="flex items-center gap-3"><div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-400 to-cyan-300 text-slate-950"><Building2/></div><div><p className="font-extrabold text-white">BRMS</p><p className="text-[10px] uppercase tracking-[.22em] text-slate-400">Rental Intelligence</p></div></div></div>
      <div className="relative max-w-2xl"><div className="mb-5 inline-flex items-center gap-2 rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1.5 text-xs font-bold text-sky-300"><Sparkles size={14}/>BRMS Management Portal</div><h1 className="text-5xl font-extrabold leading-[1.08] tracking-tight text-white">Manage every rental decision from one polished workspace.</h1><p className="mt-6 max-w-xl text-base leading-7 text-slate-400">A modern Building Rental Management System for occupancy, tenant assignments, monthly rent, utilities, maintenance and financial reporting.</p>
      <div className="mt-10 grid grid-cols-3 gap-3"><Feature icon={Store} title="Occupancy" text="Live shop status"/><Feature icon={BarChart3} title="Insights" text="Monthly reports"/><Feature icon={ShieldCheck} title="Controlled" text="Role-based access"/></div></div>
      <p className="relative text-xs text-slate-600">Authorized access only • Protected management environment</p>
    </section>
    <section className="flex min-h-screen items-center justify-center bg-white p-6 sm:p-10"><div className="w-full max-w-md"><div className="mb-8 lg:hidden"><div className="flex items-center gap-3"><div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-sky-300"><Building2/></div><div><p className="font-extrabold">BRMS</p><p className="text-[10px] uppercase tracking-[.2em] text-slate-400">Rental Intelligence</p></div></div></div><p className="text-[11px] font-extrabold uppercase tracking-[.18em] text-sky-600">Secure workspace</p><h2 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-950">Welcome back</h2><p className="mt-2 text-sm leading-6 text-slate-500">Sign in with your authorized BRMS account to continue.</p>
      <form className="mt-7 space-y-4" onSubmit={submit}><div><label className="label" htmlFor="email">Email address</label><input id="email" className="field py-3" type="email" autoComplete="username" value={email} onChange={e=>{setEmail(e.target.value);setError('');clearAuthError()}} required placeholder="you@example.com"/></div><div><label className="label" htmlFor="password">Password</label><div className="relative"><input id="password" className="field py-3 pr-12" type={showPassword?'text':'password'} autoComplete="current-password" value={password} onChange={e=>{setPassword(e.target.value);setError('');clearAuthError()}} required placeholder="••••••••"/><button type="button" className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-slate-400 hover:text-slate-700" onClick={()=>setShowPassword(value=>!value)} aria-label={showPassword?'Hide password':'Show password'}>{showPassword?<EyeOff size={18}/>:<Eye size={18}/>}</button></div></div>{(error||authError)&&<p role="alert" className="rounded-xl bg-rose-50 px-3 py-2.5 text-sm font-medium text-rose-700">{error||authError}</p>}<button className="btn-primary w-full py-3.5" disabled={loading}>{loading?'Signing in…':'Sign in to BRMS'}<ArrowRight size={17}/></button></form><div className="mt-8 flex items-center gap-2 text-xs text-slate-400"><ShieldCheck size={15}/>Identity is verified before protected data is accessed.</div></div></section>
  </div>
}
function Feature({icon:Icon,title,text}){return <div className="rounded-2xl border border-white/10 bg-white/[.04] p-4 backdrop-blur"><Icon size={19} className="text-sky-300"/><p className="mt-4 text-sm font-bold text-white">{title}</p><p className="mt-1 text-xs text-slate-500">{text}</p></div>}
