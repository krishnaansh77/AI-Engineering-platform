"use client";

import { useEffect, useState } from "react";
import { Bug, ExternalLink, Loader2, Search } from "lucide-react";
import { api, getErrorMessage, IssueAnalysis, RepositoryIssue } from "@/lib/api";

export default function IssueIntelligencePanel({ repoId }: { repoId: string }) {
  const [issues, setIssues] = useState<RepositoryIssue[]>([]);
  const [state, setState] = useState<"open" | "closed" | "all">("open");
  const [analysis, setAnalysis] = useState<IssueAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api.listIssues(repoId, state).then((data) => setIssues(data.issues)).catch((reason) => setError(getErrorMessage(reason))).finally(() => setLoading(false));
  }, [repoId, state]);

  const handleAnalyze = async (number: number) => {
    setAnalyzing(number);
    try { setAnalysis(await api.analyzeIssue(repoId, number)); } catch (reason) { setError(getErrorMessage(reason)); } finally { setAnalyzing(null); }
  };

  if (loading) return null;
  if (error) return <section aria-label="Issue intelligence error" className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5"><p role="alert" className="text-xs text-red-600">{error}</p></section>;
  if (issues.length === 0) return null;

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1"><Bug className="w-4 h-4 text-red-600" /><h2 className="text-sm font-semibold text-slate-700">Issue Intelligence</h2></div>
      <div className="flex items-center justify-between mb-4"><p className="text-xs text-slate-500">Connect GitHub issues to likely relevant files using hybrid code search.</p><select aria-label="Issue state" value={state} onChange={(event) => setState(event.target.value as typeof state)} className="text-xs border border-slate-300 rounded px-2 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"><option value="open">Open</option><option value="closed">Closed</option><option value="all">All</option></select></div>
      <div className="space-y-2">{issues.slice(0, 8).map((issue) => <div key={issue.number} className="flex items-center gap-2 border border-slate-100 rounded-lg p-3"><span className="text-xs text-slate-400">#{issue.number}</span><p className="text-xs text-slate-700 truncate flex-1" title={issue.title}>{issue.title}</p><a href={issue.html_url} target="_blank" rel="noopener noreferrer" aria-label={`Open issue ${issue.number}`}><ExternalLink className="w-3.5 h-3.5 text-slate-400 hover:text-sky-600" /></a><button type="button" aria-label={`Analyze issue ${issue.number}`} onClick={() => handleAnalyze(issue.number)} disabled={analyzing !== null} className="inline-flex items-center gap-1 px-2 py-1 rounded bg-sky-50 text-sky-700 text-[11px] hover:bg-sky-100 disabled:opacity-50">{analyzing === issue.number ? <Loader2 className="w-3 h-3 animate-spin" /> : <Search className="w-3 h-3" />}Analyze</button></div>)}</div>
      {analysis && <div className="mt-4 border border-sky-100 bg-sky-50/50 rounded-lg p-3"><p className="text-xs font-semibold text-slate-700 mb-2">Likely relevant files for #{analysis.issue.number}</p>{analysis.relevant_files.map((file) => <p key={`${file.file_path}-${file.start_line}`} className="text-[11px] text-sky-800 truncate" title={file.file_path}>{file.file_path}{file.symbol_name ? ` · ${file.symbol_name}` : ""} · L{file.start_line}–{file.end_line}</p>)}</div>}
    </section>
  );
}
