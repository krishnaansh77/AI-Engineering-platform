"use client";

import { FormEvent, useState } from "react";
import { Code2, Loader2, Search } from "lucide-react";
import { api, getErrorMessage, SearchResponse } from "@/lib/api";

export default function CodeSearchPanel({ repoId }: { repoId: string }) {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      setResponse(await api.searchRepo(repoId, query.trim()));
    } catch (reason) {
      setError(getErrorMessage(reason));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-white border border-slate-200 rounded-xl shadow-sm p-5 mb-5">
      <div className="flex items-center gap-2 mb-1"><Code2 className="w-4 h-4 text-indigo-600" /><h2 className="text-sm font-semibold text-slate-700">Semantic Code Search</h2></div>
      <p className="text-xs text-slate-500 mb-3">Find relevant code using meaning and keywords without generating an AI answer.</p>
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="flex items-center gap-2 flex-1 border border-slate-300 rounded-lg px-3 focus-within:ring-2 focus-within:ring-sky-500">
          <Search className="w-4 h-4 text-slate-400" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. database initialization" className="w-full py-2 text-sm outline-none" />
        </div>
        <button type="submit" disabled={loading || !query.trim()} className="px-4 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">{loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}</button>
      </form>
      {error && <p className="text-xs text-red-600 mt-3">{error}</p>}
      {response && <div className="mt-4 space-y-2">
        <p className="text-xs text-slate-500">{response.results.length} result{response.results.length === 1 ? "" : "s"} for <span className="font-medium text-slate-700">{response.query}</span></p>
        {response.results.map((result, index) => <article key={`${result.file_path}-${result.start_line}-${index}`} className="border border-slate-100 rounded-lg p-3"><div className="flex items-center justify-between gap-2"><p className="text-xs font-medium text-slate-700 truncate">{result.file_path}{result.symbol_name ? ` · ${result.symbol_name}` : ""}</p><span className="text-[10px] text-slate-400 whitespace-nowrap">L{result.start_line}–{result.end_line}</span></div><pre className="text-[11px] text-slate-500 mt-2 whitespace-pre-wrap max-h-24 overflow-hidden">{result.snippet}</pre></article>)}
        {response.results.length === 0 && <p className="text-sm text-slate-500">No relevant code found.</p>}
      </div>}
    </section>
  );
}
