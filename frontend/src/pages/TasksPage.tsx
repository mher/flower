import type { FC } from "react";
import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { buildApiUrl, fetchJson } from "../api/client";
import { getUrlPrefix, joinWithPrefix } from "../lib/urlPrefix";

type ApiTask = {
  uuid?: string;
  name?: string;
  state?: string;
  args?: string;
  kwargs?: string;
  result?: string;
  exception?: string;
  received?: number;
  started?: number;
  runtime?: number;
  worker?: string;
};

type ApiTasksResponse = Record<string, ApiTask>;

type TaskRow = ApiTask & { id: string };

function formatUnixSeconds(value?: number): string {
  if (!value) return "-";
  const ms = value * 1000;
  const d = new Date(ms);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString();
}

function formatRuntime(value?: number): string {
  if (value === undefined || value === null) return "-";
  if (!Number.isFinite(value)) return "-";
  return `${value.toFixed(3)}s`;
}

export const TasksPage: FC = () => {
  const urlPrefix = getUrlPrefix();

  const [pageSize, setPageSize] = useState<number>(25);
  const [page, setPage] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<TaskRow[]>([]);
  const [hasNext, setHasNext] = useState<boolean>(false);

  const offset = useMemo(() => page * pageSize, [page, pageSize]);

  useEffect(() => {
    const controller = new AbortController();
    const url = buildApiUrl(
      "/api/tasks",
      {
        limit: pageSize,
        offset,
        sort_by: "-received",
      },
      urlPrefix
    );

    setLoading(true);
    setError(null);

    fetchJson<ApiTasksResponse>(url, controller.signal)
      .then((data) => {
        const entries = Object.entries(data);
        const nextRows = entries.map(([id, task]) => ({ id, ...task }));
        setRows(nextRows);
        setHasNext(nextRows.length === pageSize);
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : String(e));
        setRows([]);
        setHasNext(false);
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setLoading(false);
      });

    return () => controller.abort();
  }, [offset, pageSize, urlPrefix]);

  const taskLinkBase = joinWithPrefix(urlPrefix, "/task/");

  return (
    <Container maxWidth={false} sx={{ my: 2 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
          mb: 2,
        }}
      >
        <Typography variant="h6" component="h1">
          Tasks
        </Typography>

        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            flexWrap: "wrap",
          }}
        >
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel id="tasks-page-size-label">Page size</InputLabel>
            <Select
              labelId="tasks-page-size-label"
              value={pageSize}
              label="Page size"
              onChange={(e) => {
                const next = Number(e.target.value);
                setPage(0);
                setPageSize(next);
              }}
            >
              {[10, 25, 50, 100].map((n) => (
                <MenuItem key={n} value={n}>
                  {n}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="outlined"
            disabled={loading || page === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Prev
          </Button>
          <Button
            variant="outlined"
            disabled={loading || !hasNext}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </Box>
      </Box>

      {loading && (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Loading…</Typography>
        </Box>
      )}

      {error && (
        <Typography
          variant="body2"
          color="error"
          sx={{ mb: 2, whiteSpace: "pre-wrap" }}
        >
          {error}
        </Typography>
      )}

      <Typography variant="body2" sx={{ mb: 1 }}>
        Showing offset {offset} (page {page + 1})
      </Typography>

      <Box sx={{ overflowX: "auto" }}>
        <Table size="small" sx={{ minWidth: 1200 }}>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>UUID</TableCell>
              <TableCell>State</TableCell>
              <TableCell>Args</TableCell>
              <TableCell>Kwargs</TableCell>
              <TableCell>Result / Exception</TableCell>
              <TableCell>Received</TableCell>
              <TableCell>Started</TableCell>
              <TableCell>Runtime</TableCell>
              <TableCell>Worker</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((t) => {
              const uuid = t.uuid || t.id;
              const detailsHref = `${taskLinkBase}${encodeURIComponent(uuid)}`;
              return (
                <TableRow key={t.id} hover>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {t.name || "-"}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    <Box
                      component="a"
                      href={detailsHref}
                      sx={{ color: "inherit" }}
                    >
                      {uuid}
                    </Box>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {t.state || "-"}
                  </TableCell>
                  <TableCell sx={{ maxWidth: 260 }}>
                    <Typography variant="body2" noWrap title={t.args || ""}>
                      {t.args || "-"}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ maxWidth: 260 }}>
                    <Typography variant="body2" noWrap title={t.kwargs || ""}>
                      {t.kwargs || "-"}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ maxWidth: 260 }}>
                    <Typography
                      variant="body2"
                      noWrap
                      title={
                        (t.state === "FAILURE" ? t.exception : t.result) || ""
                      }
                    >
                      {t.state === "FAILURE"
                        ? t.exception || "-"
                        : t.result || "-"}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {formatUnixSeconds(t.received)}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {formatUnixSeconds(t.started)}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {formatRuntime(t.runtime)}
                  </TableCell>
                  <TableCell sx={{ whiteSpace: "nowrap" }}>
                    {t.worker || "-"}
                  </TableCell>
                </TableRow>
              );
            })}

            {!loading && rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={10}>
                  <Typography variant="body2">No tasks found.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Box>
    </Container>
  );
};
