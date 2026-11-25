import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./index.css";
import { applyTheme, initialTheme } from "./state/theme";

applyTheme(initialTheme()); // before the first paint, so there is no flash of the wrong theme

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
