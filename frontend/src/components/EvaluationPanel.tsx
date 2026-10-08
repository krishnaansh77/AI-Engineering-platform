"use client";

import { FormEvent, useState } from "react";
import { BarChart3, FlaskConical, Loader2 } from "lucide-react";
import { api, EvaluationRun, getErrorMessage } from "@/lib/api";

export default function EvaluationPanel({ repoId }: { repoId: string }) {
  const [benchmarks, setBenchmarks] = useState("");
  const [result, setResult] = useState<EvaluationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runEvaluation = async (event: FormEvent) => {
    event.preventDefault();
    const cases = benchmarks.split("\n").map((line) => {
      const [question, expected] = line.split("=>");
      return { question: question?.trim() ?? "", expected_files: (expected ?? "").split(",").map((file) => file.trim()).filter(Boolean) };
    }).filter((item) => item.question && item.expected_files.length > 0);
    if (cases.length === 0 || loading) return;
    setLoading(true);
    setError(null);
    try { setResult(await api.evaluateRepo(repoId, cases)); } catch (reason) { setError(getErrorMessage(reason)); } finally { setLoading(false); }
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1"><BarChart3 className="w-4 h-4 text-indigo-600" /><h2 className="text-sm font-semibold text-slate-700">RAG Evaluation</h2></div>
      <p className="text-xs text-slate-500 mb-3">Measure retrieval quality without generating an AI answer. One case per line: <code>question =&gt; expected/file.py,other/file.ts</code>.</p>
      <form onSubmit={runEvaluation} className="space-y-2">
        <textarea value={benchmarks} onChange={(event) => setBenchmarks(event.target.value)} placeholder={"How is the database initialized? => backend/app/database.py\nWhere are API routes defined? => backend/app/api/repos.py"} rows={3} className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
        <div className="flex justify-end"><button type="submit" disabled={loading || !benchmarks.trim()} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">{loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}Run benchmark</button></div>
      </form>
      {error && <p className="text-xs text-red-600 mt-3">{error}</p>}
      {result && <div className="mt-4 grid grid-cols-3 gap-2"><Metric label="Recall@K" value={result.summary.recall_at_k.toFixed(2)} /><Metric label="MRR" value={result.summary.mrr.toFixed(2)} /><Metric label="Cases" value={result.summary.case_count} /></div>}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2"><p className="text-base font-semibold text-slate-800">{value}</p><p className="text-[11px] text-slate-500">{label}</p></div>;
}
