# Presentation run-sheet

The deck is part of Muse: **`/app/#/present`** on the live site. Students join on their
phones at **`/app/#/join`** (the QR code on the first slide), with no login.

## 30 minutes before
1. Open the live site to wake the Render instance (the free plan sleeps after 15 minutes).
2. **Put the presenting laptop on your phone's hotspot**, not the college Wi-Fi. Per-IP
   limits are shared by everyone on one network; on its own IP the laptop always has its
   full budget for the live demos.
3. Log in to Muse on that laptop (Settings shows "Spotify connected"). Only a logged-in
   presenter can open a room, and the Rewind slide shows your own Rewind.
4. Open `/app/#/present`, press **F** for fullscreen. The first slide opens a room.
5. Press **R** to check the room slides with rehearsal votes (only on this laptop), then
   **R** again to remove them.

## Keys
| Key | Does |
|---|---|
| → / Space | next (reveals steps first) |
| ← | back |
| F | fullscreen |
| N | speaker notes |
| L | lock the room: nobody new can join (stops fake voters); people in can still change |
| X | clear all votes |
| R | rehearsal votes, this laptop only |
| ? | key list |

## Flow (about 15 minutes)
1. **Title**: everyone scans and taps a mood. Wait for most of the room.
2. **The room right now**: the live mood map. Lock the room (L) once everyone is in.
3. **The problem** (3 reveals) → **Meet Muse** (3 reveals).
4. **Live: play the room**: press *Curate for this room*, play a 30-second preview.
5. **How Muse reads a feeling**: take a sentence from the audience.
6. **The recommender**: nine steps, click any.
7. **Cover art lab**: drag the sliders.
8. **It learns from you**: tap 👍/👎.
9. **Muse Rewind**: your real Rewind and the room's personality.
10. **Architecture & security** → **DevOps pipeline** (press *Run the pipeline*), then
    switch to GitHub for ma'am.
11. **Honest limits** → **Thank you** (the room's personality), questions.

## If something goes wrong
- **"Log in to open a room"**: log in on the laptop, come back to the deck.
- **Room code stops working** (the server restarted): the deck opens a new room by
  itself; the new code and QR are on the first slide and in the top-right corner.
- **Curate says "busy"**: someone is spamming; you're on your own IP, so press again.
- **Wi-Fi down for the audience**: press R for rehearsal votes and carry on.

## Safety built in
- Students can only tap chips from Muse's fixed list: no free text reaches the screen.
- One vote per phone; new voters per minute are capped; L locks the room; X resets it.
- Rooms live in memory for 4 hours; nothing about them is stored.
- Visitors share one curation budget, so the app's Spotify quota can't be drained.
- Request bodies over 64 KB are refused before they are read.
