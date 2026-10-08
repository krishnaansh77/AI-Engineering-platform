"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  MessageSquare,
  RefreshCw,
  Trash2,
  ExternalLink,
  Files,
  Layers,
  Calendar,
  AlertCircle,
} from "lucide-react";
import { api, Repository, getErrorMessage } from "@/lib/api";
import StatusBadge from "@/components/StatusBadge";
import IndexingProgress from "@/components/IndexingProgress";
import DependencyGraphPanel from "@/components/DependencyGraphPanel";
import GitHistoryPanel from "@/components/GitHistoryPanel";
import ArchitecturePanel from "@/components/ArchitecturePanel";
import TestIntelligencePanel from "@/components/TestIntelligencePanel";
import FeedbackSummaryPanel from "@/components/FeedbackSummaryPanel";
import QueryMetricsPanel from "@/components/QueryMetricsPanel";
import { formatRelativeTime, getLanguageIcon } from "@/lib/utils";

export default function RepoDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const fetchRepo = useCallback(async () => {
    try {
      const r = await api.getRepo(id);
      setRepo(r);
      return r;
    } catch (e) {
      setError(getErrorMessage(e));
      return null;
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRepo();
  }, [fetchRepo]);

  const handleReindex = async () => {
    setReindexing(true);
    try {
      await api.reindexRepo(id);
      await fetchRepo();
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setReindexing(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Delete "${repo?.name}"? This cannot be undone.`)) return;
    setDeleting(true);
    try {
      await api.deleteRepo(id);
      router.push("/");
    } catch (e) {
      setError(getErrorMessage(e));
      setDeleting(false);
    }
  };

  if (loading)
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="h-6 w-40 bg-slate-200 rounded animate-pulse mb-8" />
        <div className="h-56 bg-white rounded-xl border border-slate-200 animate-pulse" />
      </div>
    );

  if (error || !repo)
    return (
      <div className="p-8 max-w-4xl mx-auto">
        <div className="flex items-center gap-3 text-red-600 bg-red-50 border border-red-200 rounded-lg p-4">
          <AlertCircle className="w-5 h-5" />
          <p className="text-sm">{error || "Repository not found."}</p>
        </div>
      </div>
    );

  return (
    <div className="p-8 max-w-4xl mx-auto">
      {/* Back */}
      <Link
        href="/"
        className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 text-sm mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        All repositories
      </Link>

      {/* Header card */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-6 mb-5">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-xl font-bold text-slate-900 truncate">
                {repo.name}
              </h1>
              <StatusBadge status={repo.status} />
            </div>
            <a
              href={repo.github_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-sky-600 hover:text-sky-700 text-sm"
            >
              {repo.full_name}
              <ExternalLink className="w-3 h-3" />
            </a>
            {repo.description && (
              <p className="text-slate-500 text-sm mt-2">{repo.description}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={handleReindex}
              disabled={reindexing || repo.status === "indexing"}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 rounded-lg text-sm text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw
                className={`w-3.5 h-3.5 ${reindexing ? "animate-spin" : ""}`}
              />
              Re-index
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-red-200 rounded-lg text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete
            </button>
          </div>
        </div>

        {/* Indexing progress */}
        {(repo.status === "indexing" || repo.status === "pending") && (
          <IndexingProgress repoId={id} onComplete={setRepo} />
        )}

        {/* Error */}
        {repo.status === "error" && repo.error_message && (
          <div className="flex items-start gap-2.5 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mt-4">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Indexing failed</p>
              <p className="mt-0.5 text-red-600">{repo.error_message}</p>
            </div>
          </div>
        )}

        {/* Stats row */}
        {repo.status === "ready" && (
          <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                <Files className="w-4 h-4 text-slate-500" />
              </div>
              <div>
                <p className="text-lg font-bold text-slate-900">
                  {repo.file_count.toLocaleString()}
                </p>
                <p className="text-xs text-slate-500">Files indexed</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                <Layers className="w-4 h-4 text-slate-500" />
              </div>
              <div>
                <p className="text-lg font-bold text-slate-900">
                  {repo.chunk_count.toLocaleString()}
                </p>
                <p className="text-xs text-slate-500">Code chunks</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                <Calendar className="w-4 h-4 text-slate-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">
                  {repo.last_indexed_at
                    ? formatRelativeTime(repo.last_indexed_at)
                    : "—"}
                </p>
                <p className="text-xs text-slate-500">Last indexed</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Languages */}
      {repo.languages.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">
            Languages Detected
          </h2>
          <div className="flex flex-wrap gap-2">
            {repo.languages.map((lang) => (
              <span
                key={lang}
                className="flex items-center gap-1.5 px-3 py-1 bg-slate-100 rounded-full text-sm text-slate-700"
              >
                <span>{getLanguageIcon(lang)}</span>
                {lang}
              </span>
            ))}
          </div>
        </div>
      )}

      {repo.status === "ready" && <DependencyGraphPanel repoId={id} />}

      {repo.status === "ready" && <ArchitecturePanel repoId={id} />}

      {repo.status === "ready" && <TestIntelligencePanel repoId={id} />}

      {repo.status === "ready" && <FeedbackSummaryPanel repoId={id} />}

      {repo.status === "ready" && <QueryMetricsPanel repoId={id} />}

      {repo.status === "ready" && <GitHistoryPanel repoId={id} />}

      {/* CTA — Ask a question */}
      {repo.status === "ready" && (
        <Link
          href={`/repos/${id}/chat`}
          className="flex items-center justify-center gap-2 w-full bg-sky-600 hover:bg-sky-700 text-white py-3 rounded-xl text-sm font-semibold shadow-sm"
        >
          <MessageSquare className="w-4 h-4" />
          Ask Questions About This Codebase
        </Link>
      )}
    </div>
  );
}
