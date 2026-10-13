import dagre from "@dagrejs/dagre";
import { Node, Edge } from "@xyflow/react";
import { TableNodeData } from "./erdTransform";

export type LayoutDirection = "LR" | "TB";

export interface LayoutOptions {
  direction?: LayoutDirection;
  savedPositions?: Record<string, { x: number; y: number }>;
}

export function estimateNodeDimensions(node: Node<TableNodeData>): { width: number; height: number } {
  const isLarge = node.data?.isLargeSchema;
  const colCount = node.data?.columnsToDisplay?.length || 0;

  const width = isLarge ? 220 : 270;
  // Compact mode for large schemas: header only ~48px
  // Normal mode: header ~44px + ~28px per column row + 12px padding
  const height = isLarge ? 52 : Math.max(52, 44 + colCount * 28 + 12);

  return { width, height };
}

export function getLayoutedElements(
  nodes: Node<TableNodeData>[],
  edges: Edge[],
  options: LayoutOptions = {}
): { nodes: Node<TableNodeData>[]; edges: Edge[] } {
  const { direction = "LR", savedPositions = {} } = options;

  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: direction,
    nodesep: 60,
    ranksep: 90,
    marginx: 40,
    marginy: 40,
  });
  g.setDefaultEdgeLabel(() => ({}));

  // Register nodes with dimensions in dagre
  for (const node of nodes) {
    const { width, height } = estimateNodeDimensions(node);
    g.setNode(node.id, { width, height });
  }

  // Register edges in dagre (skip self-loops to avoid cycle issues in dagre)
  for (const edge of edges) {
    if (edge.source !== edge.target) {
      g.setEdge(edge.source, edge.target);
    }
  }

  // Execute dagre layout calculation
  dagre.layout(g);

  // Apply layout positions (saved user positions override auto-layout)
  const layoutedNodes = nodes.map((node) => {
    const savedPos = savedPositions[node.id] || savedPositions[node.data?.table?.id || ""];
    if (savedPos) {
      return {
        ...node,
        position: { x: Math.round(savedPos.x), y: Math.round(savedPos.y) },
      };
    }

    const dagreNode = g.node(node.id);
    const { width, height } = estimateNodeDimensions(node);

    if (dagreNode) {
      return {
        ...node,
        position: {
          x: Math.round(dagreNode.x - width / 2),
          y: Math.round(dagreNode.y - height / 2),
        },
      };
    }

    return node;
  });

  return { nodes: layoutedNodes, edges };
}
