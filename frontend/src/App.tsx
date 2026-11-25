import { lazy, Suspense } from "react";
import { HashRouter, Route, Routes } from "react-router";
import { Toaster } from "sonner";

import { Layout } from "@/components/Layout";
import { TooltipProvider } from "@/components/ui/tooltip";
import Curate from "@/pages/Curate";
import Discover from "@/pages/Discover";
import Results from "@/pages/Results";
import { AppStateProvider } from "@/state/AppState";

// The chart library is only needed on the Music DNA page, so it loads on demand
const MusicDna = lazy(() => import("@/pages/MusicDna"));

// Hash routing (/app/#/dna) keeps every page reachable on refresh without server rules
export default function App() {
  return (
    <AppStateProvider>
      <TooltipProvider>
        <HashRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<Discover />} />
              <Route path="dna" element={<Suspense fallback={null}><MusicDna /></Suspense>} />
              <Route path="curate" element={<Curate />} />
              <Route path="results" element={<Results />} />
              <Route path="*" element={<Discover />} />
            </Route>
          </Routes>
        </HashRouter>
        <Toaster position="bottom-right" richColors closeButton />
      </TooltipProvider>
    </AppStateProvider>
  );
}
