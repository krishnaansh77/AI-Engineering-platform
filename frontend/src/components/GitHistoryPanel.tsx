"use client";

import { useEffect, useState } from "react";
import { GitCommit as GitCommitIcon, GitBranch, Plus, Minus } from "lucide-react";
import { api, GitHistory, getErrorMessage, LatestChangeAnalysis } from "@/lib/api";

export default function GitHistoryPanel({ repoId }: { repoId: string }) {
  const [history, setHistory] = useState<GitHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<LatestChangeAnalysis | null>(null);
  const [reviewing, setReviewing] = useState<string | null>(null);

  useEffect(() => {
    api.getHistory(repoId).then(setHistory).catch((reason) => setError(getErrorMessage(reason)));
  }, [repoId]);

  const reviewCommit = async (sha: string) => {
    setReviewing(sha);
    try { setAnalysis(await api.getCommitAnalysis(repoId, sha)); } catch (reason) { setError(getErrorMessage(reason)); } finally { setReviewing(null); }
  };

  if (error) {
    return <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5 text-sm text-slate-500">Git history unavailable: {error}</div>;
  }
  if (!history) {
    return <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5 animate-pulse h-48" />;
  }

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-sky-600" />
          <div>
            <h2 className="text-sm font-semibold text-slate-700">Git History</h2>
            <p className="text-xs text-slate-500 mt-1">Recent commits from the indexed repository.</p>
          </div>
        </div>
        <span className="text-xs text-slate-400">{history.count} commits</span>
      </div>
      {history.commits.length === 0 ? (
        <p className="text-sm text-slate-500">No commits found.</p>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {history.commits.map((commit) => (
            <article key={commit.sha} className="border border-slate-100 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <GitCommitIcon className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-700 truncate" title={commit.message}>{commit.message}</p>
                  <p className="text-xs text-slate-400 mt-1">{commit.author} · {new Date(commit.committed_at).toLocaleString()} · <span className="font-mono">{commit.short_sha}</span></p>
                  <div className="flex items-center gap-3 text-[11px] mt-2">
                    <span className="text-slate-500">{commit.files_changed} files</span>
                    {commit.impact_count !== undefined && <span className="text-violet-600">{commit.impact_count} downstream impact</span>}
                    <span className="flex items-center gap-0.5 text-emerald-600"><Plus className="w-3 h-3" />{commit.insertions}</span>
                    <span className="flex items-center gap-0.5 text-red-500"><Minus className="w-3 h-3" />{commit.deletions}</span>
                    <button onClick={() => reviewCommit(commit.sha)} disabled={reviewing !== null} className="ml-auto text-sky-600 hover:text-sky-700 disabled:opacity-50">{reviewing === commit.sha ? "Reviewing…" : "Review"}</button>
                  </div>
                  {commit.files.length > 0 && <p className="text-[11px] text-slate-400 mt-2 truncate" title={commit.files.join(", ")}>{commit.files.slice(0, 3).join(", ")}{commit.files.length > 3 ? ` +${commit.files.length - 3} more` : ""}</p>}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
      {analysis && <div className="mt-4 border border-violet-100 bg-violet-50/50 rounded-lg p-3"><p className="text-xs font-semibold text-slate-700 mb-2">Review for {analysis.short_sha}: {analysis.message}</p><div className="flex gap-3 text-[11px] text-slate-600 mb-2"><span>{analysis.source_files.length} source</span><span>{analysis.test_files.length} test</span><span>{analysis.documentation_files.length} docs</span></div>{analysis.recommendations.map((recommendation) => <p key={recommendation} className="text-[11px] text-violet-900">• {recommendation}</p>)}</div>}
    </section>
  );
}
