"use client";

import { FormEvent, useEffect, useState } from "react";
import { FileDiff, GitCommit, Lightbulb, Plus, Minus } from "lucide-react";
import { api, getErrorMessage, LatestChangeAnalysis, PRComparisonAnalysis } from "@/lib/api";

export default function LatestChangePanel({ repoId }: { repoId: string }) {
  const [analysis, setAnalysis] = useState<LatestChangeAnalysis | null>(null);
  const [base, setBase] = useState("");
  const [head, setHead] = useState("");
  const [comparison, setComparison] = useState<PRComparisonAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getLatestChangeAnalysis(repoId).then(setAnalysis).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  const compare = async (event: FormEvent) => {
    event.preventDefault();
    if (!base.trim() || !head.trim() || loading) return;
    setLoading(true);
    setError(null);
    try { setComparison(await api.comparePR(repoId, base.trim(), head.trim())); } catch (reason) { setError(getErrorMessage(reason)); } finally { setLoading(false); }
  };

  if (!analysis) return error ? <p className="text-xs text-red-600 mb-4">{error}</p> : null;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1"><FileDiff className="w-4 h-4 text-violet-600" /><h2 className="text-sm font-semibold text-slate-700">Latest Change Analysis</h2></div>
      <p className="text-xs text-slate-500 mb-4">PR-style review signals for the latest commit in the indexed clone.</p>
      <div className="flex items-center gap-2 text-xs text-slate-600 mb-3"><GitCommit className="w-3.5 h-3.5" /><span className="font-medium truncate">{analysis.message}</span><span className="font-mono text-slate-400">{analysis.short_sha}</span></div>
      <div className="flex items-center gap-3 text-[11px] mb-4"><span>{analysis.changed_files.length} changed files</span><span className="flex items-center gap-0.5 text-emerald-600"><Plus className="w-3 h-3" />{analysis.insertions}</span><span className="flex items-center gap-0.5 text-red-500"><Minus className="w-3 h-3" />{analysis.deletions}</span><span className="text-slate-400">{analysis.test_files.length} test files</span></div>
      <div className="border border-amber-100 bg-amber-50/50 rounded-lg p-3"><p className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 mb-2"><Lightbulb className="w-3.5 h-3.5" />Review suggestions</p>{analysis.recommendations.map((recommendation) => <p key={recommendation} className="text-[11px] text-amber-900">• {recommendation}</p>)}</div>
      <form onSubmit={compare} className="mt-4 border-t border-slate-100 pt-4 space-y-2">
        <p className="text-xs font-semibold text-slate-700">Compare base and head</p>
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_auto] gap-2"><input aria-label="Base branch or commit SHA" value={base} onChange={(event) => setBase(event.target.value)} placeholder="Base branch or SHA" className="px-2 py-1.5 border border-slate-300 rounded text-xs" /><input aria-label="Head branch or commit SHA" value={head} onChange={(event) => setHead(event.target.value)} placeholder="Head branch or SHA" className="px-2 py-1.5 border border-slate-300 rounded text-xs" /><button type="submit" aria-label="Compare branches or commits" disabled={loading || !base.trim() || !head.trim()} className="px-3 py-1.5 rounded bg-violet-600 text-white text-xs disabled:opacity-50">{loading ? "Comparing…" : "Compare"}</button></div>
      </form>
      {error && <p role="alert" className="text-xs text-red-600 mt-2">{error}</p>}
      {comparison && <div className="mt-3 border border-violet-100 bg-violet-50/40 rounded-lg p-3"><p className="text-xs font-semibold text-slate-700">{comparison.base_short_sha} → {comparison.head_short_sha}</p><div className="flex gap-3 text-[11px] text-slate-600 mt-1"><span>{comparison.changed_files.length} changed</span><span>{comparison.impacted_files.length} impacted</span><span>{comparison.test_files.length} tests</span><span>{comparison.documentation_files.length} docs</span></div>{comparison.recommendations.map((recommendation) => <p key={recommendation} className="text-[11px] text-violet-900 mt-1">• {recommendation}</p>)}</div>}
    </section>
  );
}
