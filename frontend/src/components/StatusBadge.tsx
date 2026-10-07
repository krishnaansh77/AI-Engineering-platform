import { Loader2, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import { cn, capitalize } from "@/lib/utils";

interface StatusBadgeProps {
  status: "pending" | "indexing" | "ready" | "error";
  className?: string;
}

const config = {
  pending: {
    icon: Clock,
    color: "text-slate-500 bg-slate-50 border-slate-200",
    spin: false,
  },
  indexing: {
    icon: Loader2,
    color: "text-amber-600 bg-amber-50 border-amber-200",
    spin: true,
  },
  ready: {
    icon: CheckCircle2,
    color: "text-emerald-600 bg-emerald-50 border-emerald-200",
    spin: false,
  },
  error: {
    icon: AlertCircle,
    color: "text-red-600 bg-red-50 border-red-200",
    spin: false,
  },
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const { icon: Icon, color, spin } = config[status] ?? config.pending;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border flex-shrink-0",
        color,
        className
      )}
    >
      <Icon className={cn("w-3 h-3", spin && "animate-spin")} />
      {capitalize(status)}
    </span>
  );
}
