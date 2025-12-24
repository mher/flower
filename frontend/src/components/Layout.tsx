import type { FC, ReactNode } from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import { getUrlPrefix } from "../lib/urlPrefix";
import { Navbar } from "./Navbar";

type LayoutProps = {
  children?: ReactNode;
};

export const Layout: FC<LayoutProps> = ({ children }) => {
  const urlPrefix = getUrlPrefix();

  return (
    <Box sx={{ px: 1, py: 1 }}>
      <Navbar urlPrefix={urlPrefix} />

      <Container maxWidth={false} sx={{ my: 2 }}>
        <Box id="alert-container" />
        <input type="hidden" value={urlPrefix} id="url_prefix" readOnly />
      </Container>

      {children}
    </Box>
  );
};
