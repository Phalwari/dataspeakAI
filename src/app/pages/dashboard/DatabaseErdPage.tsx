import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useParams, useNavigate } from "react-router";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  ReactFlowInstance,
  Panel,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import {
  ArrowLeft,
  RotateCw,
  Search,
  Sparkles,
  Layers,
  LayoutGrid,
  Maximize2,
  RefreshCw,
  AlertTriangle,
  Info,
  Clock,
  Database,
  Filter,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";

import { API_BASE_URL } from "../../config/api";
import { TableNode } from "../../components/erd/TableNode";
import { TableDetailsDrawer } from "../../components/erd/TableDetailsDrawer";
import {
  DatabaseErdResponse,
  ErdTable,
  transformErdDataToGraph,
  TableNodeData,
} from "../../utils/erdTransform";
import { getLayoutedElements, LayoutDirection } from "../../utils/erdLayout";

const nodeTypes = {
  tableNode: TableNode,
};

export function DatabaseErdPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  // API Data state
  const [erdData, setErdData] = useState<DatabaseErdResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Graph state
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<TableNodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const reactFlowInstance = useRef<ReactFlowInstance<Node<TableNodeData>, Edge> | null>(null);
  const hasInitialFitRef = useRef(false);

  // UI Interactive state
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTable, setSelectedTable] = useState<ErdTable | null>(null);
  const [showPkFkOnly, setShowPkFkOnly] = useState(false);
  const [showInferred, setShowInferred] = useState(false);
  const [direction, setDirection] = useState<LayoutDirection>("LR");

  // LocalStorage storage key for user-dragged node positions
  const storageKey = useMemo(() => {
    const s = erdData?.schema || "default";
    return `dataspeak_erd_positions_${id}_${s}`;
  }, [id, erdData?.schema]);

  const loadSavedPositions = useCallback((): Record<string, { x: number; y: number }> => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) return JSON.parse(raw);
    } catch (e) {
      console.warn("Failed to load ERD node positions from localStorage", e);
    }
    return {};
  }, [storageKey]);

  const savePositions = useCallback(
    (currentNodes: Node<TableNodeData>[]) => {
      try {
        const posMap: Record<string, { x: number; y: number }> = {};
        for (const n of currentNodes) {
          posMap[n.id] = { x: Math.round(n.position.x), y: Math.round(n.position.y) };
        }
        localStorage.setItem(storageKey, JSON.stringify(posMap));
      } catch (e) {
        console.warn("Failed to save ERD node positions to localStorage", e);
      }
    },
    [storageKey]
  );

  // Fetch ERD Data from Backend
  const fetchErdData = useCallback(
    async (refresh = false) => {
      if (!id) return;
      if (refresh) setIsRefreshing(true);
      else setIsLoading(true);
      setErrorMessage(null);

      try {
        const token = localStorage.getItem("token") || "";
        const queryParams = new URLSearchParams();
        if (refresh) queryParams.set("refresh", "true");
        if (showInferred) queryParams.set("include_inferred", "true");

        const url = `${API_BASE_URL}/api/databases/${id}/erd?${queryParams.toString()}`;
        const response = await fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (response.status === 429) {
          const retryAfter = response.headers.get("Retry-After") || "30";
          const errData = await response.json().catch(() => ({}));
          const msg =
            errData.detail ||
            `Refresh cooldown active. Please wait ${retryAfter}s before refreshing.`;
          toast.warning(msg);
          return;
        }

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          const detail =
            errData.detail || `Failed to fetch ERD data (HTTP ${response.status})`;
          throw new Error(detail);
        }

        const data: DatabaseErdResponse = await response.json();
        setErdData(data);
        if (refresh) {
          toast.success("Database schema refreshed successfully");
        }
      } catch (err: any) {
        const msg = err.message || "An unexpected error occurred while loading the ERD.";
        setErrorMessage(msg);
        toast.error(msg);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [id, showInferred]
  );

  useEffect(() => {
    hasInitialFitRef.current = false;
    fetchErdData(false);
  }, [fetchErdData]);

  // Transform and Layout Graph whenever data or layout toggles change
  useEffect(() => {
    if (!erdData) return;

    const savedPositions = loadSavedPositions();
    const { nodes: rawNodes, edges: rawEdges } = transformErdDataToGraph(erdData, {
      showPkFkOnly,
      showInferred,
      savedPositions,
      direction,
    });

    // Compute dagre layout with saved positions prioritized
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      rawNodes,
      rawEdges,
      {
        direction,
        savedPositions,
      }
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    // Initial fit view only (preserved across filter/toggle changes)
    if (!hasInitialFitRef.current) {
      setTimeout(() => {
        if (reactFlowInstance.current) {
          reactFlowInstance.current.fitView({ padding: 0.15, duration: 400 });
        }
      }, 50);
      hasInitialFitRef.current = true;
    }
  }, [erdData, showPkFkOnly, showInferred, direction, loadSavedPositions, setNodes, setEdges]);

  // Handle Drag Stop: persist dragged positions
  const onNodeDragStop = useCallback(
    (_: any, node: Node) => {
      setNodes((currentNodes) => {
        const updated = currentNodes.map((n) => (n.id === node.id ? { ...n, position: node.position } : n));
        savePositions(updated);
        return updated;
      });
    },
    [savePositions, setNodes]
  );

  // Reset Layout: clear stored positions and re-apply dagre
  const handleResetLayout = useCallback(() => {
    try {
      localStorage.removeItem(storageKey);
    } catch (e) {
      console.warn("Failed to clear localStorage positions", e);
    }

    if (!erdData) return;
    const { nodes: rawNodes, edges: rawEdges } = transformErdDataToGraph(erdData, {
      showPkFkOnly,
      showInferred,
      savedPositions: {},
      direction,
    });

    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      rawNodes,
      rawEdges,
      {
        direction,
        savedPositions: {},
      }
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    setTimeout(() => {
      if (reactFlowInstance.current) {
        reactFlowInstance.current.fitView({ padding: 0.15, duration: 500 });
      }
    }, 50);

    toast.info("Layout reset to default positions");
  }, [storageKey, erdData, showPkFkOnly, showInferred, direction, setNodes, setEdges]);

  // Node Click: open side panel with table details
  const onNodeClick = useCallback(
    (_: any, node: Node) => {
      const found = erdData?.tables.find((t) => t.name === node.id || t.id === node.id);
      setSelectedTable(found || null);

      // Highlight selected node
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          selected: n.id === node.id,
        }))
      );
    },
    [erdData, setNodes]
  );

  // Search filter and center match
  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query);
      if (!query.trim() || !reactFlowInstance.current) return;

      const q = query.trim().toLowerCase();
      const match = nodes.find(
        (n) => n.id.toLowerCase().includes(q) || (n.data?.table?.name || "").toLowerCase().includes(q)
      );

      if (match) {
        setNodes((nds) =>
          nds.map((n) => ({
            ...n,
            selected: n.id === match.id,
          }))
        );

        reactFlowInstance.current.setCenter(match.position.x + 130, match.position.y + 40, {
          zoom: 1.1,
          duration: 600,
        });

        const found = erdData?.tables.find((t) => t.name === match.id);
        if (found) setSelectedTable(found);
      }
    },
    [nodes, erdData, setNodes]
  );

  // Select table from drawer (e.g. clicking inbound/outbound reference)
  const handleSelectTableFromDrawer = useCallback(
    (tableName: string) => {
      const match = nodes.find((n) => n.id === tableName);
      if (match && reactFlowInstance.current) {
        setNodes((nds) =>
          nds.map((n) => ({
            ...n,
            selected: n.id === match.id,
          }))
        );
        reactFlowInstance.current.setCenter(match.position.x + 130, match.position.y + 40, {
          zoom: 1.1,
          duration: 600,
        });
      }
      const found = erdData?.tables.find((t) => t.name === tableName);
      if (found) setSelectedTable(found);
    },
    [nodes, erdData, setNodes]
  );

  const isLargeSchema = (erdData?.tables.length || 0) > 60;
  const noFkFound = (erdData?.relationships.length || 0) === 0 && (erdData?.tables.length || 0) > 0;

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
      {/* Top Header / Toolbar */}
      <header className="h-14 px-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between gap-3 shrink-0 z-10 shadow-sm">
        {/* Left: Back button & Title */}
        <div className="flex items-center gap-3 overflow-hidden">
          <button
            onClick={() => navigate("/dashboard/databases")}
            aria-label="Back to databases"
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-2 overflow-hidden">
            <Database className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0" />
            <h1 className="font-semibold text-slate-900 dark:text-slate-100 text-sm truncate">
              Entity-Relationship Diagram
            </h1>
            {erdData && (
              <span className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                <span className="capitalize">{erdData.dialect}</span>
                <span>•</span>
                <span>{erdData.table_count} tables</span>
              </span>
            )}
          </div>
        </div>

        {/* Center: Search Table */}
        <div className="relative w-48 sm:w-64 max-w-xs">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Find table..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full h-8 pl-8 pr-3 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Right: Controls & Toggles */}
        <div className="flex items-center gap-1.5">
          {/* PK/FK Only toggle */}
          <button
            onClick={() => setShowPkFkOnly((prev) => !prev)}
            title="Toggle showing only PK & FK columns"
            aria-label="Toggle PK and FK columns only"
            className={`px-2.5 h-8 rounded-lg text-xs font-medium flex items-center gap-1.5 border transition-colors ${
              showPkFkOnly
                ? "bg-indigo-50 dark:bg-indigo-950/60 border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400"
                : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <Filter className="w-3 h-3" />
            <span className="hidden md:inline">PK/FK Only</span>
          </button>

          {/* Show Inferred toggle */}
          <button
            onClick={() => setShowInferred((prev) => !prev)}
            title="Toggle heuristic inferred foreign keys"
            aria-label="Toggle inferred foreign keys"
            className={`px-2.5 h-8 rounded-lg text-xs font-medium flex items-center gap-1.5 border transition-colors ${
              showInferred
                ? "bg-amber-50 dark:bg-amber-950/60 border-amber-200 dark:border-amber-800 text-amber-600 dark:text-amber-400"
                : "border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
            }`}
          >
            <Sparkles className="w-3 h-3" />
            <span className="hidden md:inline">Inferred</span>
          </button>

          {/* Direction toggle */}
          <button
            onClick={() => setDirection((d) => (d === "LR" ? "TB" : "LR"))}
            title={`Switch layout direction (current: ${direction})`}
            aria-label="Switch layout direction"
            className="px-2.5 h-8 rounded-lg text-xs font-medium border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors hidden sm:flex items-center gap-1.5"
          >
            <LayoutGrid className="w-3 h-3" />
            <span>{direction}</span>
          </button>

          {/* Reset Layout */}
          <button
            onClick={handleResetLayout}
            title="Reset layout to default positions"
            aria-label="Reset layout"
            className="p-1.5 h-8 w-8 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>

          {/* Refresh from Database */}
          <button
            onClick={() => fetchErdData(true)}
            disabled={isRefreshing}
            title="Force re-sync schema from live database"
            aria-label="Refresh database schema"
            className="px-2.5 h-8 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium flex items-center gap-1.5 shadow-sm transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </header>

      {/* Warning & Info Banners */}
      {erdData && (
        <div className="shrink-0 flex flex-col gap-1 px-4 py-1.5 bg-slate-100/60 dark:bg-slate-900/40 border-b border-slate-200 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-400">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 font-mono text-[11px]">
                <Clock className="w-3 h-3 text-slate-400" />
                <span>
                  Source: <strong className="font-semibold">{erdData.source}</strong>
                </span>
                {erdData.last_sync && (
                  <span className="text-slate-400">
                    ({new Date(erdData.last_sync).toLocaleTimeString()})
                  </span>
                )}
              </span>

              {erdData.schema && (
                <span className="text-[11px] text-slate-500">
                  Schema: <strong className="font-semibold">{erdData.schema}</strong>
                </span>
              )}
            </div>

            {/* Truncated notice */}
            {erdData.truncated && (
              <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                <AlertTriangle className="w-3.5 h-3.5" />
                Truncated to first {nodes.length} tables (Limit reached)
              </span>
            )}
          </div>

          {/* No foreign keys suggestion banner */}
          {noFkFound && !showInferred && (
            <div className="flex items-center justify-between p-2 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900 text-amber-800 dark:text-amber-300">
              <span className="flex items-center gap-1.5">
                <Info className="w-4 h-4 shrink-0" />
                No physical foreign key relationships found in this schema.
              </span>
              <button
                onClick={() => setShowInferred(true)}
                className="underline font-semibold hover:text-amber-900 dark:hover:text-amber-100 ml-2"
              >
                Enable Inferred Relationships
              </button>
            </div>
          )}
        </div>
      )}

      {/* Main Canvas Area */}
      <main className="relative flex-1 w-full h-full overflow-hidden">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-slate-400">
            <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
            <p className="text-sm font-medium">Loading schema diagram...</p>
          </div>
        ) : errorMessage ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
            <div className="p-3 rounded-full bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400">
              <AlertTriangle className="w-8 h-8" />
            </div>
            <div className="max-w-md">
              <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-1">
                Unable to load ERD
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">{errorMessage}</p>
            </div>
            <button
              onClick={() => fetchErdData(false)}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium shadow-sm transition-colors"
            >
              Retry Connection
            </button>
          </div>
        ) : nodes.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-slate-400 text-center px-4">
            <Layers className="w-10 h-10 text-slate-300 dark:text-slate-700" />
            <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
              No tables found
            </h3>
            <p className="text-xs max-w-sm">
              The connected database returned 0 tables or views for this schema.
            </p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onNodeDragStop={onNodeDragStop}
            nodeTypes={nodeTypes}
            onInit={(instance) => {
              reactFlowInstance.current = instance;
            }}
            fitView
            minZoom={0.08}
            maxZoom={2.2}
            onlyRenderVisibleElements={isLargeSchema}
            proOptions={{ hideAttribution: true }}
            className="bg-slate-50/50 dark:bg-slate-950/50"
          >
            <Background gap={18} size={1} color="#cbd5e1" />
            <Controls
              className="!bg-white dark:!bg-slate-900 !border-slate-200 dark:!border-slate-800 !shadow-lg !rounded-lg"
              showInteractive={false}
            />
            <MiniMap
              nodeColor={(n) => {
                if (n.data?.table?.kind === "view") return "#c084fc";
                return "#818cf8";
              }}
              maskColor="rgba(15, 23, 42, 0.4)"
              className="!bg-white dark:!bg-slate-900 !border-slate-200 dark:!border-slate-800 !shadow-lg !rounded-lg overflow-hidden"
              zoomable
              pannable
            />
          </ReactFlow>
        )}

        {/* Side Panel Drawer */}
        <TableDetailsDrawer
          table={selectedTable}
          relationships={erdData?.relationships || []}
          onClose={() => setSelectedTable(null)}
          onSelectTable={handleSelectTableFromDrawer}
        />
      </main>
    </div>
  );
}

export default DatabaseErdPage;
