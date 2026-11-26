import { MotionConfig } from "framer-motion";
import { lazy, Suspense } from "react";
import { HashRouter, Route, Routes } from "react-router";
import { Toaster } from "sonner";

import { Layout } from "@/components/Layout";
import { TooltipProvider } from "@/components/ui/tooltip";
import Curate from "@/pages/Curate";
import Discover from "@/pages/Discover";
import Results from "@/pages/Results";
import Settings from "@/pages/Settings";
import { PreviewProvider } from "@/state/PreviewPlayer";
import { AppStateProvider } from "@/state/AppState";

// The chart library is only needed on the Music DNA and History pages, so they load on demand
const MusicDna = lazy(() => import("@/pages/MusicDna"));
const History = lazy(() => import("@/pages/History"));
const Rewind = lazy(() => import("@/pages/Rewind"));
// Room mode: the phone page and the presentation deck, both full screen (no menu)
const Join = lazy(() => import("@/pages/Join"));
const Present = lazy(() => import("@/present/Present"));

// Hash routing (/app/#/dna) keeps every page reachable on refresh without server rules
export default function App() {
  return (
    // reducedMotion="user": people who ask their device for less motion get fades, not movement
    <MotionConfig reducedMotion="user">
    <AppStateProvider>
      <PreviewProvider>
      <TooltipProvider>
        <HashRouter>
          <Routes>
            <Route path="join/:code?" element={<Suspense fallback={null}><Join /></Suspense>} />
            <Route path="present" element={<Suspense fallback={null}><Present /></Suspense>} />
            <Route element={<Layout />}>
              <Route index element={<Discover />} />
              <Route path="dna" element={<Suspense fallback={null}><MusicDna /></Suspense>} />
              <Route path="curate" element={<Curate />} />
              <Route path="results" element={<Results />} />
              <Route path="history" element={<Suspense fallback={null}><History /></Suspense>} />
              <Route path="rewind" element={<Suspense fallback={null}><Rewind /></Suspense>} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<Discover />} />
            </Route>
          </Routes>
        </HashRouter>
        {/* lifted above the mini player at the bottom of the screen */}
        <Toaster position="bottom-right" richColors closeButton offset={{ bottom: "6rem" }} mobileOffset={{ bottom: "6.5rem" }} />
      </TooltipProvider>
      </PreviewProvider>
    </AppStateProvider>
    </MotionConfig>
  );
}
