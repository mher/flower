import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import "./index.css";
import App from "./App.tsx";
import { theme } from "./theme";
import { AutoRefreshProvider } from "./lib/autoRefresh";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AutoRefreshProvider>
        <App />
      </AutoRefreshProvider>
    </ThemeProvider>
  </StrictMode>
);
