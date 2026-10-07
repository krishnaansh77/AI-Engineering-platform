import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

/** Merge Tailwind classes safely */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Format an ISO date string to a readable date */
export function formatDate(date: string): string {
  return format(new Date(date), "MMM d, yyyy");
}

/** Format an ISO date string to a relative time ("2 hours ago") */
export function formatRelativeTime(date: string): string {
  return formatDistanceToNow(new Date(date), { addSuffix: true });
}

/** Return a Tailwind color class based on indexing status */
export function getStatusColor(status: string): string {
  switch (status) {
    case "ready":
      return "text-emerald-600 bg-emerald-50 border-emerald-200";
    case "indexing":
      return "text-amber-600 bg-amber-50 border-amber-200";
    case "pending":
      return "text-slate-500 bg-slate-50 border-slate-200";
    case "error":
      return "text-red-600 bg-red-50 border-red-200";
    default:
      return "text-slate-500 bg-slate-50 border-slate-200";
  }
}

/** Return a language emoji icon */
export function getLanguageIcon(language: string): string {
  switch (language.toLowerCase()) {
    case "python":
      return "🐍";
    case "javascript":
      return "🟨";
    case "typescript":
      return "🔷";
    case "go":
      return "🐹";
    case "rust":
      return "🦀";
    case "java":
      return "☕";
    default:
      return "📄";
  }
}

/** Generate a unique message ID */
export function generateId(): string {
  return Math.random().toString(36).slice(2, 10);
}

/** Capitalize first letter */
export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
