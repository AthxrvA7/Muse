import { LogIn } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api, DEMO_MODE } from "@/lib/api/services";
import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

/** Small, quiet Spotify connection indicator for the sidebar and settings. */
export function SpotifyStatus({ compact = false }: { compact?: boolean }) {
  const { user, loginAvailable } = useApp();
  if (user === undefined) return <div className="h-10" />;
  if (user) {
    return (
      <div className={cn("flex items-center gap-2.5 rounded-2xl bg-sage-soft px-3 py-2", compact && "px-2")}>
        <span className="size-2 shrink-0 rounded-full bg-moss" aria-hidden="true" />
        <div className="min-w-0 text-xs leading-tight">
          <div className="font-semibold text-moss">{DEMO_MODE ? "Demo mode" : "Spotify connected"}</div>
          {!compact && <div className="truncate text-ink-soft">{user.display_name ?? "Listener"}</div>}
        </div>
      </div>
    );
  }
  if (!loginAvailable) return <p className="px-1 text-xs text-ink-soft">Login isn&apos;t set up on this server.</p>;
  return (
    <Button asChild variant="spotify" size="sm" className="w-full">
      <a href={api.auth.loginUrl}>
        <LogIn /> Connect Spotify
      </a>
    </Button>
  );
}
