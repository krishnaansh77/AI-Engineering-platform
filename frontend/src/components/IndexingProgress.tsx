"use client";

import { useEffect, useCallback } from "react";
import { Loader2, CheckCircle2 } from "lucide-react";
import { api, Repository } from "@/lib/api";

interface IndexingProgressProps {
  repoId: string;
  onComplete: (repo: Repository) => void;
}

const STEPS = [
  "Cloning repository…",
  "Detecting languages and frameworks…",
  "Parsing source files with AST…",
  "Chunking code by function and class boundaries…",
  "Generating embeddings…",
  "Storing in vector database…",
  "Finalizing index…",
];

export default function IndexingProgress({
  repoId,
  onComplete,
}: IndexingProgressProps) {
  const poll = useCallback(async () => {
    try {
      const repo = await api.getRepo(repoId);
      if (repo.status === "ready" || repo.status === "error") {
        onComplete(repo);
      }
    } catch {
      // Silently ignore poll errors — will retry
    }
  }, [repoId, onComplete]);

  // Poll every 3 seconds
  useEffect(() => {
    const interval = setInterval(poll, 3000);
    return () => clearInterval(interval);
  }, [poll]);

  // Cycle through step messages for UI feedback
  const stepIndex = Math.floor((Date.now() / 3000) % STEPS.length);

  return (
    <div className="mt-4 bg-amber-50 border border-amber-200 rounded-lg px-4 py-4">
      <div className="flex items-center gap-3 mb-3">
        <div className="relative flex-shrink-0">
          <div className="w-5 h-5 rounded-full bg-amber-400" />
          <div className="absolute inset-0 rounded-full border-2 border-amber-400 animate-ping" />
        </div>
        <p className="text-sm font-medium text-amber-800">Indexing in progress</p>
      </div>

      {/* Animated step text */}
      <div className="ml-8 space-y-1.5">
        {STEPS.map((step, i) => (
          <div key={step} className="flex items-center gap-2">
            {i < stepIndex ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
            ) : i === stepIndex ? (
              <Loader2 className="w-3.5 h-3.5 text-amber-600 animate-spin flex-shrink-0" />
            ) : (
              <div className="w-3.5 h-3.5 rounded-full border border-slate-300 flex-shrink-0" />
            )}
            <span
              className={`text-xs ${
                i < stepIndex
                  ? "text-slate-400 line-through"
                  : i === stepIndex
                  ? "text-amber-700 font-medium"
                  : "text-slate-400"
              }`}
            >
              {step}
            </span>
          </div>
        ))}
      </div>

      <p className="text-xs text-amber-600 mt-3 ml-8">
        This page will update automatically when indexing is complete.
      </p>
    </div>
  );
}
