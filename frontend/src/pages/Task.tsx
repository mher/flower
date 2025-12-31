import type { FC, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { buildApiUrl, fetchJson } from "../api/client";
import { getUrlPrefix, joinWithPrefix } from "../lib/urlPrefix";

type ApiTaskInfo = Record<string, unknown> & {
  name?: string;
  state?: string;
  args?: string;
  kwargs?: string;
  result?: unknown;
  traceback?: string | null;
  worker?: string | null;
  exception?: unknown;
  "task-id"?: string;
};

type TaskProps = {
  taskId: string;
};

function formatUnixSeconds(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    return "-";
  }
  const ms = value * 1000;
  const d = new Date(ms);
  if (Number.isNaN(d.getTime())) return "-";
  return d.toLocaleString();
}

function humanizeKey(key: string): string {
  const normalized = key.replace(/[-_]+/g, " ").replace(/\s+/g, " ").trim();

  if (!normalized) return "-";

  return normalized
    .split(" ")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");
}

function getStateChipColor(
  state?: string
): "default" | "success" | "error" | "info" | "warning" {
  switch (state) {
    case "SUCCESS":
      return "success";
    case "FAILURE":
      return "error";
    case "STARTED":
      return "info";
    case "RETRY":
      return "warning";
    default:
      return "default";
  }
}

function renderValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean")
    return String(value);

  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

async function postJson(
  url: string,
  signal?: AbortSignal
): Promise<Record<string, unknown>> {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
    credentials: "same-origin",
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed: ${res.status} ${res.statusText}`);
  }

  return (await res.json()) as Record<string, unknown>;
}

export const Task: FC<TaskProps> = ({ taskId }) => {
  const urlPrefix = getUrlPrefix();
  const appRoot = useMemo(
    () => joinWithPrefix(urlPrefix, "/index.html"),
    [urlPrefix]
  );

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [task, setTask] = useState<ApiTaskInfo | null>(null);
  const [refreshTick, setRefreshTick] = useState<number>(0);

  useEffect(() => {
    const controller = new AbortController();
    const url = buildApiUrl(
      `/api/task/info/${encodeURIComponent(taskId)}`,
      undefined,
      urlPrefix
    );

    setLoading(true);
    setError(null);
    setMessage(null);

    fetchJson<ApiTaskInfo>(url, controller.signal)
      .then((data) => setTask(data))
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : String(e));
        setTask(null);
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setLoading(false);
      });

    return () => controller.abort();
  }, [taskId, urlPrefix, refreshTick]);

  const state = task?.state;
  const name = task?.name ?? "-";
  const canTerminate = state === "STARTED";
  const canRevoke = state === "RECEIVED" || state === "RETRY";

  const extraRows = useMemo(() => {
    if (!task) return [] as Array<{ key: string; value: unknown }>;

    const excluded = new Set([
      "name",
      "uuid",
      "state",
      "args",
      "kwargs",
      "result",
      "task-id",
    ]);

    const entries = Object.entries(task)
      .filter(([k, v]) => !excluded.has(k) && v !== null && v !== undefined)
      .sort(([a], [b]) => a.localeCompare(b));

    return entries.map(([key, value]) => ({ key, value }));
  }, [task]);

  const timeKeys = useMemo(
    () =>
      new Set([
        "sent",
        "received",
        "started",
        "succeeded",
        "retried",
        "timestamp",
        "failed",
        "revoked",
      ]),
    []
  );

  function renderCell(key: string, value: unknown): ReactNode {
    if (timeKeys.has(key)) return formatUnixSeconds(value);

    if (key === "worker" && typeof value === "string" && value) {
      const workerHref = joinWithPrefix(
        urlPrefix,
        `/worker/${encodeURIComponent(value)}`
      );
      return (
        <Box component="a" href={workerHref} sx={{ color: "inherit" }}>
          {value}
        </Box>
      );
    }

    if (key === "traceback" && typeof value === "string" && value) {
      return (
        <Box
          component="pre"
          sx={{ whiteSpace: "pre-wrap", margin: 0, fontSize: "0.85rem" }}
        >
          {value}
        </Box>
      );
    }

    if (
      (key === "parent_id" || key === "root_id") &&
      typeof value === "string"
    ) {
      const href = `${appRoot}#/tasks/${encodeURIComponent(value)}`;
      return (
        <Box component="a" href={href} sx={{ color: "inherit" }}>
          {value}
        </Box>
      );
    }

    if (key === "children") {
      const children: string[] = [];
      if (Array.isArray(value)) {
        for (const item of value) {
          if (typeof item === "string") children.push(item);
          else if (
            typeof item === "object" &&
            item !== null &&
            "id" in (item as Record<string, unknown>)
          ) {
            const id = (item as Record<string, unknown>).id;
            if (typeof id === "string") children.push(id);
          }
        }
      }

      if (children.length === 0) return renderValue(value);

      return (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
          {children.map((id) => (
            <Box
              key={id}
              component="a"
              href={`${appRoot}#/tasks/${encodeURIComponent(id)}`}
              sx={{ color: "inherit" }}
            >
              {id}
            </Box>
          ))}
        </Box>
      );
    }

    return renderValue(value);
  }

  async function revokeTask(terminate: boolean): Promise<void> {
    const controller = new AbortController();
    const url = buildApiUrl(
      `/api/task/revoke/${encodeURIComponent(taskId)}`,
      terminate ? { terminate: true } : undefined,
      urlPrefix
    );

    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      const res = await postJson(url, controller.signal);
      const msgRaw = res.message;
      setMessage(typeof msgRaw === "string" ? msgRaw : "Task updated.");
      setRefreshTick((v) => v + 1);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Container maxWidth={false} sx={{ my: 2 }}>
      {error && (
        <Typography
          variant="body2"
          color="error"
          sx={{ mb: 2, whiteSpace: "pre-wrap" }}
        >
          {error}
        </Typography>
      )}
      {message && (
        <Typography variant="body2" sx={{ mb: 2, whiteSpace: "pre-wrap" }}>
          {message}
        </Typography>
      )}

      <Box
        sx={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 2,
          flexWrap: "wrap",
          mb: 2,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h5" component="h1" noWrap title={name}>
            {name}
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {taskId}
          </Typography>
        </Box>

        {canTerminate ? (
          <Button
            variant="contained"
            color="error"
            disabled={loading}
            onClick={() => revokeTask(true)}
          >
            Terminate
          </Button>
        ) : canRevoke ? (
          <Button
            variant="contained"
            color="error"
            disabled={loading}
            onClick={() => revokeTask(false)}
          >
            Revoke
          </Button>
        ) : null}
      </Box>

      <Table
        size="small"
        sx={{
          maxWidth: 900,
          border: "0.5px solid #c7ecb8",
          borderCollapse: "separate",
          "& .MuiTableRow-root:nth-of-type(odd)": {
            bgcolor: "#f0ffeb",
          },
          "& .MuiTableCell-root": {
            border: 0,
          },
        }}
        aria-label="Task details"
      >
        <TableBody>
          <TableRow>
            <TableCell sx={{ width: 200 }}>Name</TableCell>
            <TableCell>{task?.name ?? "-"}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>UUID</TableCell>
            <TableCell>{taskId}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>State</TableCell>
            <TableCell>
              <Chip
                size="small"
                label={state || "-"}
                color={getStateChipColor(state)}
                sx={
                  getStateChipColor(state) === "default"
                    ? { bgcolor: "grey.300", color: "text.primary" }
                    : undefined
                }
              />
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell>args</TableCell>
            <TableCell>{task?.args ?? "-"}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>kwargs</TableCell>
            <TableCell>{task?.kwargs ?? "-"}</TableCell>
          </TableRow>
          <TableRow>
            <TableCell>Result</TableCell>
            <TableCell>{renderValue(task?.result ?? "")}</TableCell>
          </TableRow>

          {extraRows.map(({ key, value }) => (
            <TableRow key={key}>
              <TableCell>{humanizeKey(key)}</TableCell>
              <TableCell>{renderCell(key, value)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Container>
  );
};
