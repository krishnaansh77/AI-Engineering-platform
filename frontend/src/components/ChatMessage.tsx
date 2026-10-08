import { ChatMessage, FeedbackRating } from "@/lib/api";
import { cn, formatRelativeTime } from "@/lib/utils";
import CitationCard from "./CitationCard";
import { Bot, User, ThumbsDown, ThumbsUp } from "lucide-react";

interface ChatMessageProps {
  message: ChatMessage;
  onFeedback?: (messageId: string, rating: FeedbackRating) => void;
}

/** Very simple inline markdown renderer — handles bold, inline code, and newlines */
function renderMarkdown(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\n)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={i}
          className="font-mono text-sky-700 bg-sky-50 px-1 py-0.5 rounded text-xs"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (part === "\n") {
      return <br key={i} />;
    }
    return <span key={i}>{part}</span>;
  });
}

export default function ChatMessageComponent({ message, onFeedback }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center",
          isUser ? "bg-sky-600" : "bg-slate-200"
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Bot className="w-4 h-4 text-slate-600" />
        )}
      </div>

      {/* Content */}
      <div className={cn("flex flex-col gap-2 max-w-2xl", isUser && "items-end")}>
        {/* Bubble */}
        {message.isLoading ? (
          <div className="px-4 py-3 bg-white border border-slate-200 rounded-2xl rounded-tl-sm shadow-sm">
            <div className="flex gap-1.5 items-center h-5">
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce [animation-delay:-0.3s]" />
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce [animation-delay:-0.15s]" />
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" />
            </div>
          </div>
        ) : (
          <div
            className={cn(
              "px-4 py-3 rounded-2xl shadow-sm text-sm leading-relaxed",
              isUser
                ? "bg-sky-600 text-white rounded-tr-sm"
                : "bg-white border border-slate-200 text-slate-800 rounded-tl-sm"
            )}
          >
            {isUser ? (
              message.content
            ) : (
              <p className="whitespace-pre-wrap">{renderMarkdown(message.content)}</p>
            )}
          </div>
        )}

        {/* Citations */}
        {!isUser && !message.isLoading && message.citations && message.citations.length > 0 && (
          <div className="w-full">
            <p className="text-xs text-slate-400 mb-1.5 font-medium">
              Sources ({message.citations.length})
            </p>
            <div className="flex flex-col gap-1.5">
              {message.citations.map((citation, i) => (
                <CitationCard key={i} citation={citation} index={i} />
              ))}
            </div>
          </div>
        )}

        {!isUser && !message.isLoading && message.question && (
          <div className="flex items-center gap-1 text-xs text-slate-400">
            <span>Was this helpful?</span>
            <button
              onClick={() => onFeedback?.(message.id, "helpful")}
              disabled={Boolean(message.feedback)}
              className={cn("p-1 rounded hover:bg-emerald-50 hover:text-emerald-600 disabled:cursor-default", message.feedback === "helpful" && "bg-emerald-50 text-emerald-600")}
              aria-label="Mark answer helpful"
            ><ThumbsUp className="w-3.5 h-3.5" /></button>
            <button
              onClick={() => onFeedback?.(message.id, "not_helpful")}
              disabled={Boolean(message.feedback)}
              className={cn("p-1 rounded hover:bg-red-50 hover:text-red-600 disabled:cursor-default", message.feedback === "not_helpful" && "bg-red-50 text-red-600")}
              aria-label="Mark answer not helpful"
            ><ThumbsDown className="w-3.5 h-3.5" /></button>
          </div>
        )}

        {/* Timestamp */}
        <p className="text-xs text-slate-400">
          {formatRelativeTime(message.timestamp.toISOString())}
        </p>
      </div>
    </div>
  );
}
