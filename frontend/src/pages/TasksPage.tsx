import type { FC } from "react";
import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import {
  type GridColDef,
  type GridRenderCellParams,
  DataGrid,
} from "@mui/x-data-grid";
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

type ApiTasksEnvelope = {
  tasks: ApiTasksResponse;
  total: number;
};

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
  const [rowCount, setRowCount] = useState<number>(0);

  const offset = useMemo(() => page * pageSize, [page, pageSize]);

  useEffect(() => {
    const controller = new AbortController();
    const url = buildApiUrl(
      "/api/v2/tasks",
      {
        limit: pageSize,
        offset,
        sort_by: "-received",
      },
      urlPrefix
    );

    setLoading(true);
    setError(null);

    fetchJson<ApiTasksEnvelope>(url, controller.signal)
      .then((data) => {
        const entries = Object.entries(data.tasks);
        const nextRows = entries.map(([id, task]) => ({ id, ...task }));
        setRows(nextRows);
        setRowCount(data.total);
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : String(e));
        setRows([]);
        setRowCount(0);
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setLoading(false);
      });

    return () => controller.abort();
  }, [offset, pageSize, urlPrefix]);

  const taskLinkBase = joinWithPrefix(urlPrefix, "/task/");

  const columns = useMemo<Array<GridColDef<TaskRow>>>(
    () => [
      {
        field: "name",
        headerName: "Name",
        minWidth: 220,
        flex: 1,
        sortable: false,
        valueGetter: (_value, row) => row.name || "-",
      },
      {
        field: "uuid",
        headerName: "UUID",
        minWidth: 320,
        flex: 1,
        sortable: false,
        renderCell: (params: GridRenderCellParams<TaskRow>) => {
          const uuid = params.row.uuid || params.row.id;
          const detailsHref = `${taskLinkBase}${encodeURIComponent(uuid)}`;
          return (
            <Box component="a" href={detailsHref} sx={{ color: "inherit" }}>
              {uuid}
            </Box>
          );
        },
      },
      {
        field: "state",
        headerName: "State",
        minWidth: 120,
        sortable: false,
        valueGetter: (_value, row) => row.state || "-",
      },
      {
        field: "args",
        headerName: "Args",
        minWidth: 220,
        flex: 1,
        sortable: false,
        renderCell: (
          params: GridRenderCellParams<TaskRow, string | undefined>
        ) => (
          <Typography variant="body2" noWrap title={params.value || ""}>
            {params.value || "-"}
          </Typography>
        ),
      },
      {
        field: "kwargs",
        headerName: "Kwargs",
        minWidth: 220,
        flex: 1,
        sortable: false,
        renderCell: (
          params: GridRenderCellParams<TaskRow, string | undefined>
        ) => (
          <Typography variant="body2" noWrap title={params.value || ""}>
            {params.value || "-"}
          </Typography>
        ),
      },
      {
        field: "result",
        headerName: "Result / Exception",
        minWidth: 260,
        flex: 1,
        sortable: false,
        valueGetter: (_value, row) =>
          row.state === "FAILURE" ? row.exception : row.result,
        renderCell: (
          params: GridRenderCellParams<TaskRow, string | undefined>
        ) => (
          <Typography variant="body2" noWrap title={params.value || ""}>
            {params.value || "-"}
          </Typography>
        ),
      },
      {
        field: "received",
        headerName: "Received",
        minWidth: 180,
        sortable: false,
        valueFormatter: (value) => formatUnixSeconds(value as number),
      },
      {
        field: "started",
        headerName: "Started",
        minWidth: 180,
        sortable: false,
        valueFormatter: (value) => formatUnixSeconds(value as number),
      },
      {
        field: "runtime",
        headerName: "Runtime",
        minWidth: 120,
        sortable: false,
        valueFormatter: (value) => formatRuntime(value as number),
      },
      {
        field: "worker",
        headerName: "Worker",
        minWidth: 200,
        flex: 1,
        sortable: false,
        valueGetter: (_value, row) => row.worker || "-",
      },
    ],
    [taskLinkBase]
  );

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

      <DataGrid
        autoHeight
        rows={rows}
        columns={columns}
        loading={loading}
        disableRowSelectionOnClick
        pagination
        paginationMode="server"
        rowCount={rowCount}
        paginationModel={{ page, pageSize }}
        onPaginationModelChange={(model) => {
          if (model.pageSize !== pageSize) {
            setPage(0);
            setPageSize(model.pageSize);
            return;
          }
          setPage(model.page);
        }}
        pageSizeOptions={[10, 25, 50, 100]}
        sx={{ minWidth: 1200 }}
      />
    </Container>
  );
};
