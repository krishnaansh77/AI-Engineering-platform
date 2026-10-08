"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, GitBranch, Loader2, AlertCircle } from "lucide-react";
import { api, getErrorMessage } from "@/lib/api";

function isValidGitHubUrl(url: string): boolean {
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean);
    return u.hostname === "github.com" && parts.length >= 2;
  } catch {
    return false;
  }
}

export default function ConnectRepoPage() {
  const router = useRouter();
  const [githubUrl, setGithubUrl] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [urlError, setUrlError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isValidGitHubUrl(githubUrl)) {
      setUrlError("Please enter a valid GitHub URL (e.g. https://github.com/owner/repo)");
      return;
    }
    setUrlError(null);
    setLoading(true);

    try {
      const repo = await api.connectRepo({
        github_url: githubUrl.trim(),
        name: name.trim() || undefined,
      });
      router.push(`/repos/${repo.id}`);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-2xl mx-auto">
      {/* Back */}
      <Link
        href="/"
        className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 text-sm mb-8"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to repositories
      </Link>

      {/* Card */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-sky-50 flex items-center justify-center">
            <GitBranch className="w-5 h-5 text-sky-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              Connect a Repository
            </h1>
            <p className="text-slate-500 text-sm">
              Index a GitHub repository for AI-powered code analysis
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* GitHub URL */}
          <div>
            <label htmlFor="github-repository-url" className="block text-sm font-medium text-slate-700 mb-1.5">
              GitHub Repository URL
              <span className="text-red-500 ml-0.5">*</span>
            </label>
            <input
              id="github-repository-url"
              type="url"
              aria-invalid={Boolean(urlError)}
              aria-describedby={urlError ? "github-url-error" : undefined}
              value={githubUrl}
              onChange={(e) => {
                setGithubUrl(e.target.value);
                if (urlError) setUrlError(null);
              }}
              placeholder="https://github.com/tiangolo/fastapi"
              required
              className={`w-full px-3.5 py-2.5 border rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent ${
                urlError
                  ? "border-red-300 bg-red-50"
                  : "border-slate-300 bg-white"
              }`}
            />
            {urlError && (
              <p id="github-url-error" role="alert" className="mt-1.5 text-xs text-red-600 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                {urlError}
              </p>
            )}
          </div>

          {/* Optional name */}
          <div>
            <label htmlFor="repository-display-name" className="block text-sm font-medium text-slate-700 mb-1.5">
              Display Name{" "}
              <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <input
              id="repository-display-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Awesome Project"
              className="w-full px-3.5 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent"
            />
          </div>

          {/* Info box */}
          <div className="bg-sky-50 border border-sky-100 rounded-lg px-4 py-3 text-xs text-sky-700">
            <p className="font-medium mb-1">What happens when you connect:</p>
            <ol className="list-decimal list-inside space-y-0.5 text-sky-600">
              <li>The repository is cloned locally</li>
              <li>Python, JavaScript, and TypeScript files are parsed with AST</li>
              <li>Code is chunked by function/class boundaries</li>
              <li>Embeddings are generated and stored in the vector database</li>
              <li>You can start asking questions immediately</li>
            </ol>
          </div>

          {/* Error */}
          {error && (
            <div role="alert" className="flex items-start gap-2.5 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <p>{error}</p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            aria-busy={loading}
            disabled={loading || !githubUrl}
            className="w-full flex items-center justify-center gap-2 bg-sky-600 hover:bg-sky-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white px-4 py-2.5 rounded-lg text-sm font-medium shadow-sm"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Connecting repository…
              </>
            ) : (
              <>
                <GitBranch className="w-4 h-4" />
                Connect &amp; Index Repository
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
