export default function KpiCard({ icon:Icon, label, value, detail, tone='sky' }) {
  const t = { sky:'bg-sky-50 text-sky-700', emerald:'bg-emerald-50 text-emerald-700', violet:'bg-violet-50 text-violet-700', amber:'bg-amber-50 text-amber-700', rose:'bg-rose-50 text-rose-700' }[tone]
  return <div className="card p-5"><div className="flex items-start justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.08em] text-slate-400">{label}</p><p className="mt-3 text-2xl font-extrabold tracking-tight text-slate-950">{value}</p>{detail&&<p className="mt-2 text-xs text-slate-500">{detail}</p>}</div><div className={`flex h-11 w-11 items-center justify-center rounded-2xl ${t}`}><Icon size={20}/></div></div></div>
}
