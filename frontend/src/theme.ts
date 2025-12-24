import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  typography: {
    fontFamily:
      'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji"',
  },
  palette: {
    mode: "light",
    background: {
      default: "#ffffff",
    },
  },
});
