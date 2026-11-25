import { LogIn, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api/services";
import { useApp } from "@/state/AppState";

export function LoginPrompt({ title, children }: { title: string; children?: React.ReactNode }) {
  const { user, loginAvailable } = useApp();
  if (user === undefined) return null;
  return (
    <Card className="mx-auto max-w-lg text-center">
      <div className="mx-auto grid size-12 place-items-center rounded-2xl bg-lavender-soft text-plum">
        <ShieldCheck className="size-6" />
      </div>
      <h2 className="mt-4 font-display text-2xl">{title}</h2>
      <p className="mt-2 text-sm text-ink-soft">
        {children ??
          "Muse asks Spotify only for your name and permission to create new playlists. It never reads your listening history and never changes your existing playlists."}
      </p>
      {loginAvailable ? (
        <Button asChild variant="spotify" size="lg" className="mt-6">
          <a href={api.auth.loginUrl}>
            <LogIn /> Connect Spotify
          </a>
        </Button>
      ) : (
        <p className="mt-6 text-sm text-ink-soft">Login isn&apos;t set up on this server yet.</p>
      )}
    </Card>
  );
}
