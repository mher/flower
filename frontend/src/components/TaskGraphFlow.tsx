import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";
import ReactFlow, {
  MarkerType,
  Position,
  type ReactFlowInstance,
  type Edge,
  type Node,
} from "reactflow";
import "reactflow/dist/style.css";
import { buildApiUrl, fetchJson } from "../api/client";
import { getUrlPrefix } from "../lib/urlPrefix";

type ApiTaskInfo = Record<string, unknown> & {
  name?: string;
  state?: string;
  parent_id?: string;
  children?: unknown;
};

type TaskGraphFlowProps = {
  taskId: string;
};

const MAX_DEPTH = 10;
const ROW_Y_SPACING = 140;
const MAX_NODES = 400;

function getTaskName(
  info: ApiTaskInfo | null | undefined,
  taskId: string
): string {
  const name = info?.name;
  if (typeof name === "string" && name.trim()) return name;
  return taskId;
}

function getParentId(info: ApiTaskInfo | null | undefined): string | null {
  const raw = info?.parent_id;
  return typeof raw === "string" && raw ? raw : null;
}

function extractChildrenIds(info: ApiTaskInfo | null | undefined): string[] {
  const value = info?.children;
  const children: string[] = [];

  if (!Array.isArray(value)) return children;

  for (const item of value) {
    if (typeof item === "string") {
      children.push(item);
      continue;
    }
    if (typeof item === "object" && item !== null) {
      const rec = item as Record<string, unknown>;
      const id = rec.id;
      if (typeof id === "string" && id) children.push(id);
    }
  }

  return children;
}

function edgeId(source: string, target: string): string {
  return `${source}__${target}`;
}

export function TaskGraphFlow({ taskId }: TaskGraphFlowProps) {
  const urlPrefix = getUrlPrefix();
  const theme = useTheme();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [reactFlowInstance, setReactFlowInstance] =
    useState<ReactFlowInstance | null>(null);

  const fetchTaskInfo = useMemo(() => {
    return async (
      id: string,
      signal: AbortSignal
    ): Promise<ApiTaskInfo | null> => {
      const url = buildApiUrl(
        `/api/task/info/${encodeURIComponent(id)}`,
        undefined,
        urlPrefix
      );

      try {
        return await fetchJson<ApiTaskInfo>(url, signal);
      } catch {
        // Best-effort fetching: if a task is missing (e.g. 404) or temporarily unavailable,
        // we still render the rest of the graph.
        return null;
      }
    };
  }, [urlPrefix]);

  const measureLabelWidth = useMemo(() => {
    const cache = new Map<string, number>();
    const fallback = (label: string) => Math.max(0, label.length) * 8;

    // Canvas-based measurement for more accurate sizing.
    const canvas =
      typeof document !== "undefined" ? document.createElement("canvas") : null;
    const ctx = canvas?.getContext("2d") ?? null;

    // ReactFlow default nodes use inherited styles; we approximate with MUI body2.
    const fontFamily = theme.typography.fontFamily;
    const fontSizePx = 14;
    const font = `${fontSizePx}px ${fontFamily}`;

    return (label: string): number => {
      if (!label) return 0;
      const cached = cache.get(label);
      if (cached !== undefined) return cached;
      if (!ctx) {
        const w = fallback(label);
        cache.set(label, w);
        return w;
      }

      ctx.font = font;
      const w = ctx.measureText(label).width;
      cache.set(label, w);
      return w;
    };
  }, [theme.typography.fontFamily]);

  const getNodeStyle = useMemo(() => {
    return (
      state: unknown,
      isCurrent: boolean,
      label: string
    ): Node["style"] => {
      const s = typeof state === "string" ? state : undefined;

      const textWidth = measureLabelWidth(label);
      const horizontalPadding = 10 * 2;
      const borderAllowance = isCurrent ? 6 : 2;
      const computedWidth = Math.min(
        900,
        Math.max(
          180,
          Math.ceil(textWidth + horizontalPadding + borderAllowance)
        )
      );

      const base = {
        borderRadius: 8,
        padding: 10,
        width: computedWidth,
        whiteSpace: "nowrap",
        cursor: "pointer",
        border: `${isCurrent ? 3 : 1}px solid ${
          isCurrent ? theme.palette.text.primary : theme.palette.divider
        }`,
      } as const;

      switch (s) {
        case "SUCCESS":
          return {
            ...base,
            background: theme.palette.success.light,
            color: theme.palette.success.contrastText,
          };
        case "FAILURE":
          return {
            ...base,
            background: theme.palette.error.light,
            color: theme.palette.error.contrastText,
          };
        case "STARTED":
          return {
            ...base,
            background: theme.palette.info.light,
            color: theme.palette.info.contrastText,
          };
        case "RETRY":
          return {
            ...base,
            background: theme.palette.warning.light,
            color: theme.palette.warning.contrastText,
          };
        default:
          return {
            ...base,
            background: theme.palette.grey[300],
            color: theme.palette.text.primary,
          };
      }
    };
  }, [measureLabelWidth, theme]);

  const arrowMarker = useMemo(() => {
    return {
      type: MarkerType.ArrowClosed,
      width: 18,
      height: 18,
      color: theme.palette.text.secondary,
    };
  }, [theme.palette.text.secondary]);

  const defaultEdgeOptions = useMemo(() => {
    return {
      type: "smoothstep",
      markerEnd: arrowMarker,
      style: { stroke: theme.palette.text.secondary },
    } as const;
  }, [arrowMarker, theme.palette.text.secondary]);

  useEffect(() => {
    const controller = new AbortController();

    setLoading(true);
    setError(null);

    (async () => {
      const visited = new Set<string>();
      const infoById = new Map<string, ApiTaskInfo | null>();
      const depthById = new Map<string, number>();
      const discoveryIndexById = new Map<string, number>();

      const nodesOut: Node[] = [];

      const edgesOut: Edge[] = [];
      const edgeIds = new Set<string>();

      let discoveryIndex = 0;

      const ensureTaskInfo = async (
        id: string
      ): Promise<ApiTaskInfo | null> => {
        if (infoById.has(id)) return infoById.get(id) ?? null;

        const info = await fetchTaskInfo(id, controller.signal);
        infoById.set(id, info);
        if (!discoveryIndexById.has(id)) {
          discoveryIndexById.set(id, discoveryIndex++);
        }
        return info;
      };

      const addEdge = (source: string, target: string): void => {
        const id = edgeId(source, target);
        if (edgeIds.has(id)) return;
        edgeIds.add(id);
        edgesOut.push({
          id,
          source,
          target,
          animated: false,
        });
      };

      visited.add(taskId);
      depthById.set(taskId, 0);
      const rootInfo = await ensureTaskInfo(taskId);

      // Walk parents chain up to MAX_DEPTH.
      let currentId = taskId;
      for (let i = 0; i < MAX_DEPTH; i += 1) {
        const currentInfo = await ensureTaskInfo(currentId);
        const parentId = getParentId(currentInfo);
        if (!parentId) break;

        if (!depthById.has(parentId)) depthById.set(parentId, -(i + 1));
        addEdge(parentId, currentId);

        await ensureTaskInfo(parentId);

        if (visited.has(parentId)) break;
        visited.add(parentId);
        currentId = parentId;

        if (visited.size >= MAX_NODES) break;
      }

      // BFS children up to MAX_DEPTH.
      const queue: Array<{ id: string; depth: number }> = [
        {
          id: taskId,
          depth: 0,
        },
      ];

      while (queue.length > 0) {
        const next = queue.shift();
        if (!next) break;

        if (next.depth >= MAX_DEPTH) continue;

        const info = await ensureTaskInfo(next.id);
        if (!info) continue;
        const childIds = extractChildrenIds(info);

        for (const childId of childIds) {
          addEdge(next.id, childId);

          if (!depthById.has(childId)) depthById.set(childId, next.depth + 1);

          await ensureTaskInfo(childId);

          if (!visited.has(childId)) {
            visited.add(childId);
            queue.push({ id: childId, depth: next.depth + 1 });
          }

          if (visited.size >= MAX_NODES) break;
        }

        if (visited.size >= MAX_NODES) break;
      }

      // Layout: vertical flow. Parents above (negative depth), children below (positive depth).
      const nodesByDepth = new Map<number, string[]>();
      for (const id of visited) {
        const depth = depthById.get(id) ?? 0;
        if (!nodesByDepth.has(depth)) nodesByDepth.set(depth, []);
        nodesByDepth.get(depth)?.push(id);
      }

      const sortedDepths = [...nodesByDepth.keys()].sort((a, b) => a - b);

      for (const depth of sortedDepths) {
        const ids = nodesByDepth.get(depth) ?? [];
        ids.sort((a, b) => {
          const ia = discoveryIndexById.get(a) ?? 0;
          const ib = discoveryIndexById.get(b) ?? 0;
          return ia - ib;
        });

        // Keep parent chain stable (single node per depth typically), and center siblings around x=0.
        // For children depths, use dynamic widths to avoid overlap.
        const gap = 40;

        const labels = ids.map((id) => {
          const info = infoById.get(id);
          return getTaskName(info, id);
        });

        const widths = labels.map((label, idx) => {
          const id = ids[idx] ?? "";
          const info = infoById.get(id);
          const isCurrent = id === taskId;
          const style = getNodeStyle(info?.state, isCurrent, label);
          const w = style?.width;
          return typeof w === "number" ? w : 180;
        });

        const totalWidth =
          widths.reduce((acc, w) => acc + w, 0) +
          Math.max(0, widths.length - 1) * gap;
        const xStart = -totalWidth / 2;

        for (let idx = 0; idx < ids.length; idx += 1) {
          const id = ids[idx];
          const info = infoById.get(id);

          const label = labels[idx] ?? id;
          const style = getNodeStyle(info?.state, id === taskId, label);
          const xOffsetBefore =
            widths.slice(0, idx).reduce((acc, w) => acc + w, 0) + idx * gap;
          const xLeft = xStart + xOffsetBefore;

          const nodeWidth = widths[idx] ?? 180;

          // For the parent chain (negative depth) and the current task, keep the node centered
          // on the vertical axis by placing its center at x=0.
          const x = depth < 0 || id === taskId ? -nodeWidth / 2 : xLeft;
          const y = depth * ROW_Y_SPACING;

          nodesOut.push({
            id,
            position: { x, y },
            data: { label },
            type: "default",
            sourcePosition: Position.Bottom,
            targetPosition: Position.Top,
            style,
          });
        }
      }

      // Ensure root exists even if the task fetch failed.
      if (!nodesOut.some((n) => n.id === taskId)) {
        const rootLabel = getTaskName(rootInfo, taskId);
        const style = getNodeStyle(rootInfo?.state, true, rootLabel);
        const width = typeof style?.width === "number" ? style.width : 180;
        nodesOut.push({
          id: taskId,
          position: { x: -width / 2, y: 0 },
          data: { label: rootLabel },
          type: "default",
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
          style,
        });
      }

      setNodes(nodesOut);
      setEdges(edgesOut);
    })()
      .catch((e: unknown) => {
        if (controller.signal.aborted) return;
        setError(e instanceof Error ? e.message : String(e));
        setNodes([]);
        setEdges([]);
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setLoading(false);
      });

    return () => controller.abort();
  }, [fetchTaskInfo, taskId]);

  useEffect(() => {
    if (!reactFlowInstance) return;
    if (nodes.length === 0) return;

    let rafId: number | null = null;
    let attempts = 0;

    const centerOnCurrentTask = () => {
      const node = reactFlowInstance.getNode(taskId);
      if (!node) return;

      const widthFromStyle =
        typeof node.style?.width === "number" ? node.style.width : undefined;

      const width = node.width ?? widthFromStyle ?? 180;
      const height = node.height ?? 44;

      const position =
        node.positionAbsolute !== undefined
          ? node.positionAbsolute
          : node.position;

      const x = position.x + width / 2;
      const y = position.y + height / 2;

      const { zoom } = reactFlowInstance.getViewport();
      reactFlowInstance.setCenter(x, y, { zoom, duration: 0 });

      attempts += 1;
      if ((node.width == null || node.height == null) && attempts < 10) {
        rafId = requestAnimationFrame(centerOnCurrentTask);
      }
    };

    rafId = requestAnimationFrame(centerOnCurrentTask);

    return () => {
      if (rafId !== null) cancelAnimationFrame(rafId);
    };
  }, [nodes.length, reactFlowInstance, taskId]);

  if (error) {
    return (
      <Typography variant="body2" color="error" sx={{ whiteSpace: "pre-wrap" }}>
        {error}
      </Typography>
    );
  }

  if (loading && nodes.length === 0) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Loading graph...
      </Typography>
    );
  }

  return (
    <Box sx={{ width: "100%", height: "100%" }} aria-label="Task graph">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        defaultEdgeOptions={defaultEdgeOptions}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        onInit={setReactFlowInstance}
        onNodeClick={(_evt, node) => {
          const id = String(node.id);
          window.location.hash = `#/tasks/${encodeURIComponent(id)}`;
        }}
      />
    </Box>
  );
}
