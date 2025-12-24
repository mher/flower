import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [["babel-plugin-react-compiler"]],
      },
    }),
  ],
  build: {
    outDir: "web-dist",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return;
          if (id.includes("/react/") || id.includes("/react-dom/")) {
            return "react";
          }
          if (id.includes("@mui/x-data-grid")) {
            return "mui-x";
          }
          if (
            id.includes("@mui/material") ||
            id.includes("@mui/system") ||
            id.includes("@mui/base") ||
            id.includes("@mui/utils")
          ) {
            return "mui-core";
          }
          if (id.includes("@emotion/react") || id.includes("@emotion/styled")) {
            return "emotion";
          }
          return "vendor";
        },
      },
    },
  },
});
