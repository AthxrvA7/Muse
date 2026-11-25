import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

const LABEL = {
  checking: "Checking status…",
  ready: "All systems working",
  degraded: "Running without database",
  not_ready: "Service problem",
};

/** Live status from GET /ready (monitoring), refreshed every 30 seconds. */
export function HealthDot() {
  const { ready } = useApp();
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-ink-soft" title="Live status from /ready">
      <span
        className={cn(
          "size-2 rounded-full",
          ready === "ready" && "bg-moss",
          ready === "degraded" && "bg-amber-400",
          ready === "not_ready" && "bg-danger",
          ready === "checking" && "bg-line",
        )}
        aria-hidden="true"
      />
      {LABEL[ready]}
    </span>
  );
}
