export default function PageHeader({ eyebrow='BRMS Workspace', title, subtitle, actions }) {
  return <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
    <div>
      <p className="mb-1 text-[11px] font-extrabold uppercase tracking-[0.18em] text-sky-600">{eyebrow}</p>
      <h1 className="text-2xl font-extrabold tracking-tight text-slate-950 md:text-3xl">{title}</h1>
      {subtitle && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">{subtitle}</p>}
    </div>
    {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
  </div>
}
