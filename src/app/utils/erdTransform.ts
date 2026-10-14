import { Node, Edge, MarkerType } from "@xyflow/react";

export interface ErdColumn {
  name: string;
  type: string;
  nullable: boolean;
  is_pk: boolean;
  is_fk: boolean;
  is_unique: boolean;
}

export interface ErdTable {
  id: string;
  name: string;
  schema?: string | null;
  kind: string; // "table" | "view"
  columns: ErdColumn[];
}

export interface ErdRelationship {
  id: string;
  kind: "foreign_key" | "inferred";
  constraint_name?: string | null;
  confidence?: number | null;
  reason?: string | null;
  source_table: string; // Child table (referencing)
  source_columns: string[];
  target_table: string; // Parent table (referenced)
  target_columns: string[];
}

export interface DatabaseErdResponse {
  database_id: number;
  dialect: string;
  schema?: string | null;
  last_sync?: string | null;
  source: "catalog" | "live";
  truncated: boolean;
  table_count: number;
  warnings: string[];
  tables: ErdTable[];
  relationships: ErdRelationship[];
}

export interface TransformOptions {
  showPkFkOnly?: boolean;
  showInferred?: boolean;
  savedPositions?: Record<string, { x: number; y: number }>;
  direction?: "LR" | "TB";
}

export interface TableNodeData {
  table: ErdTable;
  isLargeSchema: boolean;
  showPkFkOnly: boolean;
  selected?: boolean;
  columnsToDisplay: ErdColumn[];
  inboundCount: number;
  outboundCount: number;
}

export function transformErdDataToGraph(
  data: DatabaseErdResponse,
  options: TransformOptions = {}
): { nodes: Node<TableNodeData>[]; edges: Edge[] } {
  const { showPkFkOnly = false, showInferred = false, savedPositions = {}, direction = "LR" } = options;

  const isLargeSchema = data.tables.length > 60;
  const tableMap = new Map<string, ErdTable>();
  for (const t of data.tables) {
    tableMap.set(t.name, t);
    tableMap.set(t.id, t);
  }

  // Count inbound and outbound relationships per table name
  const inboundCountMap = new Map<string, number>();
  const outboundCountMap = new Map<string, number>();

  for (const rel of data.relationships) {
    if (rel.kind === "inferred" && !showInferred) continue;
    if (!tableMap.has(rel.source_table) || !tableMap.has(rel.target_table)) continue;

    outboundCountMap.set(rel.source_table, (outboundCountMap.get(rel.source_table) || 0) + 1);
    inboundCountMap.set(rel.target_table, (inboundCountMap.get(rel.target_table) || 0) + 1);
  }

  // Transform tables to React Flow nodes
  const nodes: Node<TableNodeData>[] = data.tables.map((table) => {
    const columnsToDisplay = showPkFkOnly
      ? table.columns.filter((c) => c.is_pk || c.is_fk)
      : table.columns;

    const savedPos = savedPositions[table.id] || savedPositions[table.name];

    return {
      id: table.name,
      type: "tableNode",
      position: savedPos || { x: 0, y: 0 },
      data: {
        table,
        isLargeSchema,
        showPkFkOnly,
        columnsToDisplay,
        inboundCount: inboundCountMap.get(table.name) || 0,
        outboundCount: outboundCountMap.get(table.name) || 0,
      },
    };
  });

  // Transform relationships to React Flow edges
  const edges: Edge[] = [];

  for (const rel of data.relationships) {
    // 1. Inferred filter: drop inferred edges if showInferred is false
    if (rel.kind === "inferred" && !showInferred) {
      continue;
    }

    // 2. Dangling edge check: drop if source or target table is missing
    if (!tableMap.has(rel.source_table) || !tableMap.has(rel.target_table)) {
      continue;
    }

    const isSelfLoop = rel.source_table === rel.target_table;
    const isComposite = rel.source_columns.length > 1;
    const isInferred = rel.kind === "inferred";

    let label = "";
    if (isInferred) {
      const confPct = rel.confidence ? Math.round(rel.confidence * 100) : 80;
      label = `Inferred (${confPct}%)`;
    } else if (isComposite) {
      label = `[${rel.source_columns.join(", ")}]`;
    }

    const isVertical = direction === "TB";
    const edge: Edge = {
      id: rel.id,
      source: rel.source_table,
      target: rel.target_table,
      sourceHandle: isVertical ? "bottom" : "right",
      targetHandle: isVertical ? "top" : "left",
      animated: false, // MANDATORY: NO animated edges
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 16,
        height: 16,
        color: isInferred ? "#f59e0b" : "#6366f1",
      },
      style: {
        stroke: isInferred ? "#f59e0b" : "#6366f1",
        strokeWidth: isComposite ? 2.5 : 1.75,
        strokeDasharray: isInferred ? "5,5" : undefined,
      },
      data: {
        relationship: rel,
        isSelfLoop,
        isComposite,
        isInferred,
      },
    };

    if (label) {
      edge.label = label;
      edge.labelStyle = {
        fill: isInferred ? "#b45309" : "#4338ca",
        fontWeight: 600,
        fontSize: 11,
      };
      edge.labelBgStyle = {
        fill: "#ffffff",
        fillOpacity: 0.9,
        rx: 4,
        ry: 4,
      };
    }

    edges.push(edge);
  }

  return { nodes, edges };
}
