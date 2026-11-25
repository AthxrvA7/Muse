import { Download, LogOut, Music2, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { toast } from "sonner";

import { SpotifyStatus } from "@/components/SpotifyStatus";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api/services";
import { shortDate } from "@/lib/format";
import { useApp } from "@/state/AppState";

export default function Settings() {
  const navigate = useNavigate();
  const { user, logout, refreshUser, setSession } = useApp();
  const [confirm, setConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);

  async function deleteAccount() {
    setDeleting(true);
    try {
      await api.privacy.deleteAccount();
      clearBrowserHistory();
      await refreshUser();
      toast.success("Your Muse account and data are deleted.", {
        description: "To remove Muse's access completely, also visit spotify.com/account/apps.",
      });
      navigate("/");
    } catch (e) {
      toast.error("Couldn't delete the account", { description: (e as Error).message });
    } finally {
      setDeleting(false);
    }
  }

  function clearBrowserHistory() {
    try {
      localStorage.removeItem("muse.recent");
      sessionStorage.removeItem("muse.session");
    } catch {
      /* storage unavailable */
    }
    setSession(null);
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-4xl sm:text-5xl">Profile & settings</h1>
        <p className="mt-2 text-ink-soft">Your connection, your taste and your data.</p>
      </header>

      <Card className="space-y-4">
        <CardTitle className="flex items-center gap-2"><Music2 className="size-4 text-moss" /> Spotify connection</CardTitle>
        <div className="max-w-xs"><SpotifyStatus /></div>
        {user && (
          <>
            <p className="text-sm text-ink-soft">
              Connected as <strong className="text-ink">{user.display_name ?? user.spotify_id}</strong> since {shortDate(user.created_at)}. Muse can only read your name and create new private playlists.
            </p>
            <Button variant="outline" onClick={async () => { await logout(); toast.success("Logged out"); }}>
              <LogOut /> Log out
            </Button>
          </>
        )}
      </Card>

      <Card className="space-y-3">
        <CardTitle>Music preferences</CardTitle>
        <CardDescription>Artists, genres, languages and styles you&apos;ve told Muse about.</CardDescription>
        <Button asChild variant="soft"><Link to="/dna">Edit my Music DNA</Link></Button>
      </Card>

      <Card className="space-y-3">
        <CardTitle>This browser</CardTitle>
        <CardDescription>Recent curations are kept only in this browser, without the words you typed.</CardDescription>
        <Button variant="outline" onClick={() => { clearBrowserHistory(); toast.success("Cleared this browser's history"); }}>
          Clear recent sessions
        </Button>
      </Card>

      {user && (
        <Card className="space-y-4">
          <CardTitle className="flex items-center gap-2"><ShieldCheck className="size-4 text-plum" /> Your data</CardTitle>
          <CardDescription>
            Muse stores your Spotify ID and name, your taste profile, login sessions and the playlists it created. Never your play history or the text you type. Your top artists are read only when you press Import from Spotify, and are not stored.
          </CardDescription>
          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline">
              <a href={api.privacy.exportUrl} download><Download /> Download my data</a>
            </Button>
            <Dialog onOpenChange={() => setConfirm("")}>
              <DialogTrigger asChild>
                <Button variant="ghost" className="text-danger hover:bg-danger-soft hover:text-danger"><Trash2 /> Delete my account</Button>
              </DialogTrigger>
              <DialogContent title="Delete your Muse account?" description="This deletes your taste profile, playlist records and every login session right away. Playlists already in your Spotify stay there.">
                <label className="block space-y-1.5 text-sm">
                  Type <strong>DELETE</strong> to confirm
                  <Input value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" />
                </label>
                <Button variant="danger" className="mt-4 w-full" disabled={confirm !== "DELETE" || deleting} onClick={deleteAccount}>
                  <Trash2 /> {deleting ? "Deleting…" : "Delete everything"}
                </Button>
              </DialogContent>
            </Dialog>
          </div>
        </Card>
      )}
    </div>
  );
}
