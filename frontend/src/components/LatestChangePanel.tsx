"use client";

import { useEffect, useState } from "react";
import { FileDiff, GitCommit, Lightbulb, Plus, Minus } from "lucide-react";
import { api, getErrorMessage, LatestChangeAnalysis } from "@/lib/api";

export default function LatestChangePanel({ repoId }: { repoId: string }) {
  const [analysis, setAnalysis] = useState<LatestChangeAnalysis | null>(null);
  const [, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getLatestChangeAnalysis(repoId).then(setAnalysis).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  if (!analysis) return null;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1"><FileDiff className="w-4 h-4 text-violet-600" /><h2 className="text-sm font-semibold text-slate-700">Latest Change Analysis</h2></div>
      <p className="text-xs text-slate-500 mb-4">PR-style review signals for the latest commit in the indexed clone.</p>
      <div className="flex items-center gap-2 text-xs text-slate-600 mb-3"><GitCommit className="w-3.5 h-3.5" /><span className="font-medium truncate">{analysis.message}</span><span className="font-mono text-slate-400">{analysis.short_sha}</span></div>
      <div className="flex items-center gap-3 text-[11px] mb-4"><span>{analysis.changed_files.length} changed files</span><span className="flex items-center gap-0.5 text-emerald-600"><Plus className="w-3 h-3" />{analysis.insertions}</span><span className="flex items-center gap-0.5 text-red-500"><Minus className="w-3 h-3" />{analysis.deletions}</span><span className="text-slate-400">{analysis.test_files.length} test files</span></div>
      <div className="border border-amber-100 bg-amber-50/50 rounded-lg p-3"><p className="flex items-center gap-1.5 text-xs font-semibold text-amber-800 mb-2"><Lightbulb className="w-3.5 h-3.5" />Review suggestions</p>{analysis.recommendations.map((recommendation) => <p key={recommendation} className="text-[11px] text-amber-900">• {recommendation}</p>)}</div>
    </section>
  );
}
