import Link from "next/link";
import { Repository } from "@/lib/api";
import { formatRelativeTime, getLanguageIcon } from "@/lib/utils";
import StatusBadge from "./StatusBadge";
import { Files, Layers } from "lucide-react";

interface RepoCardProps {
  repo: Repository;
}

export default function RepoCard({ repo }: RepoCardProps) {
  return (
    <Link
      href={`/repos/${repo.id}`}
      className="block bg-white border border-slate-200 hover:border-sky-300 hover:shadow-md rounded-xl p-5 transition-all duration-200 group"
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0">
          <h3 className="font-semibold text-slate-900 truncate group-hover:text-sky-700">
            {repo.name}
          </h3>
          <p className="text-xs text-slate-400 font-mono truncate mt-0.5">
            {repo.full_name}
          </p>
        </div>
        <StatusBadge status={repo.status} />
      </div>

      {/* Description */}
      {repo.description && (
        <p className="text-sm text-slate-500 mb-3 line-clamp-2">
          {repo.description}
        </p>
      )}

      {/* Language pills */}
      {repo.languages.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {repo.languages.slice(0, 4).map((lang) => (
            <span
              key={lang}
              className="text-xs px-2 py-0.5 bg-slate-100 rounded-full text-slate-600 flex items-center gap-1"
            >
              {getLanguageIcon(lang)} {lang}
            </span>
          ))}
        </div>
      )}

      {/* Bottom stats */}
      <div className="flex items-center justify-between text-xs text-slate-400 pt-3 border-t border-slate-100">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1">
            <Files className="w-3 h-3" />
            {repo.file_count} files
          </span>
          <span className="flex items-center gap-1">
            <Layers className="w-3 h-3" />
            {repo.chunk_count} chunks
          </span>
        </div>
        {repo.last_indexed_at && (
          <span>{formatRelativeTime(repo.last_indexed_at)}</span>
        )}
      </div>
    </Link>
  );
}
