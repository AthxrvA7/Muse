import { HashRouter, Route, Routes } from "react-router";
import { Toaster } from "sonner";

import { Layout } from "@/components/Layout";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Sparkles } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { AppStateProvider } from "@/state/AppState";

// Hash routing (/app/#/dna) keeps every page reachable on refresh without server rules
export default function App() {
  return (
    <AppStateProvider>
      <TooltipProvider>
        <HashRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route
                path="*"
                element={
                  <EmptyState icon={Sparkles} title="Muse is being set up">
                    The design system, API layer and demo mode are in place. Pages arrive next.
                  </EmptyState>
                }
              />
            </Route>
          </Routes>
        </HashRouter>
        <Toaster position="bottom-right" richColors closeButton />
      </TooltipProvider>
    </AppStateProvider>
  );
}
