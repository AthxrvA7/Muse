import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { toast } from "sonner";

import { previewUrl } from "@/lib/preview";

/**
 * One audio player for the whole site: pressing play on a song stops any other.
 * The source is Muse's own /api/v1/previews/{id}, which redirects to a fresh 30-second
 * clip on Deezer's CDN (links expire within minutes, so they're never kept here).
 */
interface PreviewState {
  playingId: number | null; // the Deezer ID being played (or loading)
  loading: boolean;
  progress: number; // 0-1 through the clip
  toggle: (deezerId: number, title: string) => void;
  stop: () => void;
}

const PreviewContext = createContext<PreviewState | null>(null);

export function PreviewProvider({ children }: { children: ReactNode }) {
  const audio = useRef<HTMLAudioElement | null>(null);
  const [playingId, setPlayingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const current = useRef<{ id: number; title: string } | null>(null);

  const stop = useCallback(() => {
    audio.current?.pause();
    current.current = null;
    setPlayingId(null);
    setLoading(false);
    setProgress(0);
  }, []);

  useEffect(() => {
    const player = new Audio();
    player.preload = "none";
    audio.current = player;
    const onTime = () => setProgress(player.duration ? player.currentTime / player.duration : 0);
    const onPlaying = () => setLoading(false);
    const onEnded = () => {
      current.current = null;
      setPlayingId(null);
      setProgress(0);
    };
    const onError = () => {
      if (!current.current) return; // stopped on purpose
      toast.message("No preview for this song", { description: current.current.title });
      onEnded();
      setLoading(false);
    };
    player.addEventListener("timeupdate", onTime);
    player.addEventListener("playing", onPlaying);
    player.addEventListener("ended", onEnded);
    player.addEventListener("error", onError);
    return () => {
      player.pause();
      player.removeEventListener("timeupdate", onTime);
      player.removeEventListener("playing", onPlaying);
      player.removeEventListener("ended", onEnded);
      player.removeEventListener("error", onError);
      audio.current = null;
    };
  }, []);

  const toggle = useCallback(
    (deezerId: number, title: string) => {
      const player = audio.current;
      if (!player) return;
      if (current.current?.id === deezerId) {
        stop();
        return;
      }
      current.current = { id: deezerId, title };
      setPlayingId(deezerId);
      setLoading(true);
      setProgress(0);
      player.src = previewUrl(deezerId); // asks Muse for a fresh link each time
      player.volume = 0.85;
      player.play().catch(() => {
        // autoplay blocked or no preview: the error event (if any) explains it
        if (current.current?.id === deezerId) {
          setLoading(false);
        }
      });
    },
    [stop],
  );

  const value = useMemo(() => ({ playingId, loading, progress, toggle, stop }), [playingId, loading, progress, toggle, stop]);
  return <PreviewContext.Provider value={value}>{children}</PreviewContext.Provider>;
}

export function usePreview(): PreviewState {
  const value = useContext(PreviewContext);
  if (!value) throw new Error("usePreview must be used inside PreviewProvider");
  return value;
}
