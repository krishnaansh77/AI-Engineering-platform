"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Send,
  Loader2,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { api, ChatMessage, FeedbackRating, QueryResponse, Repository, getErrorMessage } from "@/lib/api";
import { generateId } from "@/lib/utils";
import ChatMessageComponent from "@/components/ChatMessage";

const STARTER_QUESTIONS = [
  "Give me an overview of this codebase",
  "Where is authentication implemented?",
  "How is the database initialized?",
  "What are the main API endpoints?",
  "How does error handling work?",
];

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Fetch repo info
  useEffect(() => {
    api.getRepo(id).then(setRepo).catch(console.error);
  }, [id]);

  useEffect(() => {
    const file = searchParams.get("file");
    if (file && !input) setInput(`Explain the purpose and main responsibilities of ${file}`);
  }, [searchParams, input]);

  // Scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || isLoading) return;

      const userMessage: ChatMessage = {
        id: generateId(),
        role: "user",
        content: question.trim(),
        timestamp: new Date(),
      };

      const loadingMessage: ChatMessage = {
        id: generateId(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isLoading: true,
      };

      setMessages((prev) => [...prev, userMessage, loadingMessage]);
      setInput("");
      setIsLoading(true);
      setError(null);

      try {
        const response: QueryResponse = await api.queryRepo(id, question.trim());

        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMessage.id
              ? {
                  ...m,
                  content: response.answer,
                  citations: response.citations,
                  question: question.trim(),
                  model: response.model,
                  retrievalCount: response.retrieval_count,
                  cached: response.cached,
                  isLoading: false,
                }
              : m
          )
        );
      } catch (e) {
        const errMsg = getErrorMessage(e);
        setError(errMsg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMessage.id
              ? {
                  ...m,
                  content: `Sorry, I couldn't retrieve an answer. ${errMsg}`,
                  isLoading: false,
                }
              : m
          )
        );
      } finally {
        setIsLoading(false);
        inputRef.current?.focus();
      }
    },
    [id, isLoading]
  );

  const handleFeedback = async (messageId: string, rating: FeedbackRating) => {
    const message = messages.find((item) => item.id === messageId);
    if (!message || message.feedback || !message.question || !message.model) return;
    try {
      await api.submitFeedback(id, {
        question: message.question,
        rating,
        model: message.model,
        retrieval_count: message.retrievalCount ?? 0,
        citation_count: message.citations?.length ?? 0,
      });
      setMessages((prev) => prev.map((item) => item.id === messageId ? { ...item, feedback: rating } : item));
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="flex-shrink-0 bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-4">
        <Link
          href={`/repos/${id}`}
          className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </Link>
        <div className="h-4 w-px bg-slate-200" />
        <div className="flex items-center gap-2 min-w-0">
          <MessageSquare className="w-4 h-4 text-sky-500 flex-shrink-0" />
          <span className="text-sm font-medium text-slate-900 truncate">
            {repo?.full_name ?? "Loading…"}
          </span>
        </div>
        {repo?.status === "ready" && (
          <span className="ml-auto flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
            Ready · {repo.chunk_count.toLocaleString()} chunks
          </span>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
        {/* Welcome */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-14 h-14 rounded-2xl bg-sky-50 flex items-center justify-center mb-4">
              <Sparkles className="w-7 h-7 text-sky-500" />
            </div>
            <h2 className="text-lg font-semibold text-slate-900 mb-1">
              Ask me anything about{" "}
              <span className="text-sky-600">{repo?.name ?? "this repo"}</span>
            </h2>
            <p className="text-slate-500 text-sm max-w-md mb-8">
              I have read and indexed all the code. Ask about architecture,
              specific functions, how things work, or where features are
              implemented.
            </p>

            {/* Starter questions */}
            <div className="flex flex-wrap gap-2 justify-center max-w-xl">
              {STARTER_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => sendMessage(q)}
                  disabled={isLoading}
                  className="px-4 py-2 bg-white border border-slate-200 hover:border-sky-300 hover:bg-sky-50 rounded-full text-sm text-slate-700 hover:text-sky-700 shadow-sm disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Chat messages */}
        {messages.map((message) => (
          <ChatMessageComponent key={message.id} message={message} onFeedback={handleFeedback} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-6 mb-2 text-xs text-red-600 bg-red-50 border border-red-200 px-3 py-2 rounded-lg">
          {error}
        </div>
      )}

      {/* Input bar */}
      <div className="flex-shrink-0 bg-white border-t border-slate-200 px-6 py-4">
        <form onSubmit={handleSubmit} className="flex gap-3 items-end max-w-4xl mx-auto">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about the codebase…"
            rows={1}
            disabled={isLoading}
            className="flex-1 resize-none px-4 py-3 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent disabled:opacity-50 max-h-32"
            style={{ minHeight: "48px" }}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex-shrink-0 w-11 h-11 flex items-center justify-center bg-sky-600 hover:bg-sky-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-xl shadow-sm"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
        <p className="text-center text-xs text-slate-400 mt-2">
          ⌘ + Enter to send
        </p>
      </div>
    </div>
  );
}
