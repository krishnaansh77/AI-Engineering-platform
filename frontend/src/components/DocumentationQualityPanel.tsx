"use client";

import { useEffect, useState } from "react";
import { BookMarked, FileWarning } from "lucide-react";
import { api, DocumentationQuality, getErrorMessage } from "@/lib/api";

export default function DocumentationQualityPanel({ repoId }: { repoId: string }) {
  const [quality, setQuality] = useState<DocumentationQuality | null>(null);
  const [, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDocumentationQuality(repoId).then(setQuality).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (!quality || quality.symbol_count === 0) return null;
  const percent = Math.round(quality.coverage * 100);

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1"><BookMarked className="w-4 h-4 text-amber-600" /><h2 className="text-sm font-semibold text-slate-700">Documentation Quality</h2></div>
      <p className="text-xs text-slate-500 mb-4">Symbol-level docstring coverage to guide future documentation work.</p>
      <div className="flex items-center gap-3 mb-3"><div className="h-2 flex-1 rounded-full bg-slate-100 overflow-hidden"><div className="h-full bg-amber-500 rounded-full" style={{ width: `${percent}%` }} /></div><span className="text-sm font-semibold text-slate-700">{percent}%</span></div>
      <div className="grid grid-cols-3 gap-2 text-xs mb-4"><Metric label="Symbols" value={quality.symbol_count} /><Metric label="Documented" value={quality.documented_symbol_count} /><Metric label="Missing docs" value={quality.undocumented_symbol_count} /></div>
      {quality.gaps.length > 0 && <div className="border border-amber-100 bg-amber-50/50 rounded-lg p-3"><p className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 mb-2"><FileWarning className="w-3.5 h-3.5" />Largest documentation gaps</p>{quality.gaps.slice(0, 6).map((gap) => <p key={gap.file_path} className="text-[11px] text-amber-900 truncate" title={gap.file_path}>{gap.file_path} · {gap.undocumented_symbols} undocumented symbols</p>)}</div>}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2"><p className="font-semibold text-slate-800">{value}</p><p className="text-[11px] text-slate-500">{label}</p></div>;
}
