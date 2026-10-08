"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { GitBranch, Plus, AlertCircle } from "lucide-react";
import { api, Repository, Workspace, getErrorMessage } from "@/lib/api";
import RepoCard from "@/components/RepoCard";
import EmptyState from "@/components/EmptyState";

export default function HomePage() {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");

  const loadRepositories = (selectedWorkspaceId?: string) => {
    setLoading(true);
    api.listRepos(selectedWorkspaceId || undefined).then(setRepos).catch((e) => setError(getErrorMessage(e))).finally(() => setLoading(false));
  };

  useEffect(() => {
    api.listWorkspaces().then((items) => {
      setWorkspaces(items);
      const stored = window.localStorage.getItem("aise_active_workspace");
      const selected = items.some((item) => item.id === stored) ? stored || "" : items[0]?.id || "";
      setWorkspaceId(selected);
      loadRepositories(selected);
    }).catch(() => loadRepositories());
  }, []);

  const changeWorkspace = (value: string) => {
    setWorkspaceId(value);
    window.localStorage.setItem("aise_active_workspace", value);
    loadRepositories(value);
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Repositories</h1>
          <p className="text-slate-500 mt-1 text-sm">
            Connect a GitHub repository to start asking questions about your
            codebase.
          </p>
        </div>
        <Link
          href="/repos/new"
          className="flex items-center gap-2 bg-sky-600 hover:bg-sky-700 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Connect Repository
        </Link>
      </div>
      {workspaces.length > 0 && <div className="mb-6 flex items-center gap-3"><label htmlFor="active-workspace" className="text-sm font-medium text-slate-700">Workspace</label><select id="active-workspace" value={workspaceId} onChange={(event) => changeWorkspace(event.target.value)} className="px-3 py-2 bg-white border border-slate-300 rounded-lg text-sm">{workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name} · {workspace.role}</option>)}</select></div>}

      {/* Error */}
      {error && (
        <div className="mb-6 flex items-center gap-3 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <p>
            Could not connect to backend:{" "}
            <span className="font-medium">{error}</span>. Make sure{" "}
            <code className="font-mono bg-red-100 px-1 rounded">
              docker-compose up
            </code>{" "}
            is running.
          </p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="h-44 bg-white rounded-xl border border-slate-200 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Repos grid */}
      {!loading && !error && repos.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {repos.map((repo) => (
            <RepoCard key={repo.id} repo={repo} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && repos.length === 0 && (
        <EmptyState
          icon={<GitBranch className="w-10 h-10 text-slate-300" />}
          title="No repositories connected"
          description="Connect your first GitHub repository to start getting AI-powered insights about your codebase."
          action={{ label: "Connect Repository", href: "/repos/new" }}
        />
      )}
    </div>
  );
}
