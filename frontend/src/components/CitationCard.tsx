import { Citation } from "@/lib/api";
import { getLanguageIcon } from "@/lib/utils";
import { FileCode } from "lucide-react";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export default function CitationCard({ citation, index }: CitationCardProps) {
  const { file_path, symbol_name, chunk_type, start_line, end_line } = citation;

  // Get just the filename for display
  const fileName = file_path.split("/").pop() ?? file_path;
  const dirPath = file_path.includes("/")
    ? file_path.slice(0, file_path.lastIndexOf("/"))
    : "";

  // Infer language from extension
  const ext = fileName.split(".").pop()?.toLowerCase() ?? "";
  const languageMap: Record<string, string> = {
    py: "python",
    js: "javascript",
    ts: "typescript",
    tsx: "typescript",
    jsx: "javascript",
  };
  const language = languageMap[ext] ?? "other";

  return (
    <div className="flex items-start gap-2.5 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg hover:bg-sky-50 hover:border-sky-200 transition-colors group">
      {/* Index number */}
      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-sky-100 text-sky-700 text-xs flex items-center justify-center font-medium mt-0.5">
        {index + 1}
      </span>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-xs">{getLanguageIcon(language)}</span>

          {/* Directory path */}
          {dirPath && (
            <span className="text-xs text-slate-400 font-mono truncate">
              {dirPath}/
            </span>
          )}

          {/* Filename */}
          <span className="text-xs font-mono font-medium text-slate-700">
            {fileName}
          </span>

          {/* Symbol */}
          {symbol_name && (
            <>
              <span className="text-slate-300 text-xs">·</span>
              <span className="text-xs font-mono text-sky-700 bg-sky-50 group-hover:bg-white px-1.5 py-0.5 rounded border border-sky-100">
                {symbol_name}
              </span>
            </>
          )}

          {/* Line range */}
          <span className="text-slate-300 text-xs">·</span>
          <span className="text-xs text-slate-500 font-mono">
            L{start_line}–{end_line}
          </span>
        </div>

        {/* Chunk type */}
        <p className="text-xs text-slate-400 mt-0.5 capitalize">{chunk_type}</p>
      </div>
    </div>
  );
}
