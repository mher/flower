import { Layout } from "./components/Layout";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import type { FC } from "react";
import { useEffect, useState } from "react";
import { TasksPage } from "./pages/TasksPage";

type Route = "home" | "workers" | "tasks" | "broker";

function getRouteFromHash(hash: string): Route {
  const h = (hash || "").replace(/^#/, "");
  const path = h.startsWith("/") ? h : `/${h}`;
  if (path.startsWith("/tasks")) return "tasks";
  if (path.startsWith("/workers")) return "workers";
  if (path.startsWith("/broker")) return "broker";
  return "home";
}

const App: FC = () => {
  const [route, setRoute] = useState<Route>(() =>
    getRouteFromHash(window.location.hash)
  );

  useEffect(() => {
    const onHashChange = () => setRoute(getRouteFromHash(window.location.hash));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return (
    <Layout>
      {route === "tasks" ? (
        <TasksPage />
      ) : (
        <Container maxWidth={false} sx={{ my: 2 }}>
          <Typography variant="h6" component="h1">
            {route === "workers"
              ? "Workers"
              : route === "broker"
              ? "Broker"
              : "Flower"}
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {route === "home"
              ? "Select a page from the navbar."
              : "Not implemented yet."}
          </Typography>
        </Container>
      )}
    </Layout>
  );
};

export default App;
