import { Check, ExternalLink, Loader2, Music2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Burst } from "@/components/Burst";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api, DEMO_MODE } from "@/lib/api/services";
import type { Playlist } from "@/lib/types";

export function SaveToSpotify({ defaultName, trackIds }: { defaultName: string; trackIds: string[] }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(defaultName);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<Playlist | null>(null);

  async function save() {
    setSaving(true);
    try {
      const playlist = await api.playlists.create(name.trim(), trackIds);
      setSaved(playlist);
      toast.success(DEMO_MODE ? "Demo: playlist saved (not really sent to Spotify)" : "Playlist created in your Spotify", {
        description: playlist.name,
      });
    } catch (e) {
      toast.error("Couldn't create the playlist", { description: (e as Error).message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="spotify" size="lg" disabled={trackIds.length === 0}>
          <Music2 /> Create in Spotify
        </Button>
      </DialogTrigger>
      <DialogContent
        title={saved ? "It's in your Spotify" : "Create in Spotify"}
        description={
          saved
            ? `${saved.track_count} tracks, saved as a private playlist.`
            : "Muse creates a new private playlist. It never changes or deletes your existing playlists."
        }
      >
        {saved ? (
          <div className="relative flex flex-col gap-3">
            <Burst />
            <div className="flex items-center gap-3 rounded-2xl bg-sage-soft p-4 text-sm text-moss">
              <Check className="size-5" /> <span className="font-semibold">{saved.name}</span>
            </div>
            <Button asChild variant="spotify">
              <a href={saved.url} target="_blank" rel="noreferrer">
                Open in Spotify <ExternalLink />
              </a>
            </Button>
          </div>
        ) : (
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              save();
            }}
          >
            <label className="block space-y-1.5 text-sm font-medium">
              Playlist name
              <Input value={name} maxLength={100} required onChange={(e) => setName(e.target.value)} />
            </label>
            <Button type="submit" variant="spotify" className="w-full" disabled={saving || !name.trim()}>
              {saving ? <Loader2 className="animate-spin" /> : <Music2 />}
              {saving ? "Creating…" : `Create with ${trackIds.length} tracks`}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
