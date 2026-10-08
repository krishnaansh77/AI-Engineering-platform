"use client";

import { FormEvent, useState } from "react";
import { BarChart3, FlaskConical, Loader2 } from "lucide-react";
import { api, EvaluationRun, getErrorMessage } from "@/lib/api";

export default function EvaluationPanel({ repoId }: { repoId: string }) {
  const [question, setQuestion] = useState("");
  const [expectedFiles, setExpectedFiles] = useState("");
  const [result, setResult] = useState<EvaluationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runEvaluation = async (event: FormEvent) => {
    event.preventDefault();
    const files = expectedFiles.split(",").map((file) => file.trim()).filter(Boolean);
    if (!question.trim() || files.length === 0 || loading) return;
    setLoading(true);
    setError(null);
    try { setResult(await api.evaluateRepo(repoId, question.trim(), files)); } catch (reason) { setError(getErrorMessage(reason)); } finally { setLoading(false); }
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1"><BarChart3 className="w-4 h-4 text-indigo-600" /><h2 className="text-sm font-semibold text-slate-700">RAG Evaluation</h2></div>
      <p className="text-xs text-slate-500 mb-3">Measure retrieval quality without generating an AI answer. Enter expected file paths separated by commas.</p>
      <form onSubmit={runEvaluation} className="space-y-2">
        <input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Question: How is the database initialized?" className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500" />
        <div className="flex gap-2"><input value={expectedFiles} onChange={(event) => setExpectedFiles(event.target.value)} placeholder="Expected files: backend/app/database.py" className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-indigo-500" /><button type="submit" disabled={loading || !question.trim() || !expectedFiles.trim()} className="inline-flex items-center gap-1.5 px-3 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">{loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}Run</button></div>
      </form>
      {error && <p className="text-xs text-red-600 mt-3">{error}</p>}
      {result && <div className="mt-4 grid grid-cols-3 gap-2"><Metric label="Recall@K" value={result.summary.recall_at_k.toFixed(2)} /><Metric label="MRR" value={result.summary.mrr.toFixed(2)} /><Metric label="Matched" value={result.cases[0]?.matched_files.length ?? 0} /></div>}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return <div className="rounded-lg bg-slate-50 border border-slate-100 px-3 py-2"><p className="text-base font-semibold text-slate-800">{value}</p><p className="text-[11px] text-slate-500">{label}</p></div>;
}
