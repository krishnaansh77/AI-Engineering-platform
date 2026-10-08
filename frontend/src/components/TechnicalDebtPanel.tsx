"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Ruler } from "lucide-react";
import { api, getErrorMessage, TechnicalDebtSummary } from "@/lib/api";

export default function TechnicalDebtPanel({ repoId }: { repoId: string }) {
  const [summary, setSummary] = useState<TechnicalDebtSummary | null>(null);
  const [, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getTechnicalDebt(repoId).then(setSummary).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (!summary) return null;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1"><AlertTriangle className="w-4 h-4 text-amber-600" /><h2 className="text-sm font-semibold text-slate-700">Technical Debt Signals</h2></div>
      <p className="text-xs text-slate-500 mb-4">Structural indicators for review—not an automated quality verdict. Analyzed {summary.files_analyzed} files and {summary.chunks_analyzed} chunks.</p>
      {summary.signals.length === 0 ? <p className="text-sm text-emerald-700">No high-connectivity or large-chunk signals detected.</p> : <div className="space-y-2">{summary.signals.slice(0, 8).map((signal) => <div key={`${signal.file_path}-${signal.signal}`} className="flex items-center gap-2 border border-amber-100 bg-amber-50/50 rounded-lg px-3 py-2"><Ruler className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" /><p className="text-xs text-slate-700 truncate flex-1" title={signal.file_path}>{signal.file_path}</p><span className="text-[11px] text-amber-800 whitespace-nowrap">{signal.signal} · {signal.value} {signal.unit}</span></div>)}</div>}
    </section>
  );
}
