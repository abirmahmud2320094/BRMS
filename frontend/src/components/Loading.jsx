export default function Loading({ label='Loading workspace…' }) {
  return <div className="flex min-h-[320px] items-center justify-center"><div className="text-center"><div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-slate-200 border-t-sky-600"/><p className="mt-3 text-sm font-medium text-slate-500">{label}</p></div></div>
}
