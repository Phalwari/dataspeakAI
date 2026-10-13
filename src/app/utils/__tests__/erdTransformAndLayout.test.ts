import { describe, it, expect } from "vitest";
import {
  transformErdDataToGraph,
  DatabaseErdResponse,
} from "../erdTransform";
import { getLayoutedElements } from "../erdLayout";

describe("erdTransform & erdLayout Pure Utilities", () => {
  const sampleResponse: DatabaseErdResponse = {
    database_id: 1,
    dialect: "sqlite",
    schema: "main",
    last_sync: "2026-10-14T00:00:00Z",
    source: "catalog",
    truncated: false,
    table_count: 4,
    warnings: [],
    tables: [
      {
        id: "users",
        name: "users",
        schema: "main",
        kind: "table",
        columns: [
          { name: "id", type: "INTEGER", nullable: false, is_pk: true, is_fk: false, is_unique: true },
          { name: "email", type: "TEXT", nullable: false, is_pk: false, is_fk: false, is_unique: true },
          { name: "manager_id", type: "INTEGER", nullable: true, is_pk: false, is_fk: true, is_unique: false },
        ],
      },
      {
        id: "orders",
        name: "orders",
        schema: "main",
        kind: "table",
        columns: [
          { name: "id", type: "INTEGER", nullable: false, is_pk: true, is_fk: false, is_unique: true },
          { name: "user_id", type: "INTEGER", nullable: false, is_pk: false, is_fk: true, is_unique: false },
          { name: "store_code", type: "TEXT", nullable: false, is_pk: false, is_fk: true, is_unique: false },
          { name: "pos_id", type: "INTEGER", nullable: false, is_pk: false, is_fk: true, is_unique: false },
        ],
      },
      {
        id: "stores",
        name: "stores",
        schema: "main",
        kind: "table",
        columns: [
          { name: "store_code", type: "TEXT", nullable: false, is_pk: true, is_fk: false, is_unique: false },
          { name: "pos_id", type: "INTEGER", nullable: false, is_pk: true, is_fk: false, is_unique: false },
          { name: "name", type: "TEXT", nullable: false, is_pk: false, is_fk: false, is_unique: false },
        ],
      },
      {
        id: "invoices",
        name: "invoices",
        schema: "main",
        kind: "table",
        columns: [
          { name: "id", type: "INTEGER", nullable: false, is_pk: true, is_fk: false, is_unique: true },
          { name: "customer_id", type: "INTEGER", nullable: false, is_pk: false, is_fk: false, is_unique: false },
        ],
      },
    ],
    relationships: [
      // 1. Standard FK: orders -> users
      {
        id: "fk_orders_users",
        kind: "foreign_key",
        source_table: "orders",
        source_columns: ["user_id"],
        target_table: "users",
        target_columns: ["id"],
      },
      // 2. Self-loop FK: users -> users (manager_id)
      {
        id: "fk_users_self",
        kind: "foreign_key",
        source_table: "users",
        source_columns: ["manager_id"],
        target_table: "users",
        target_columns: ["id"],
      },
      // 3. Composite FK: orders -> stores (store_code, pos_id)
      {
        id: "fk_orders_stores_comp",
        kind: "foreign_key",
        source_table: "orders",
        source_columns: ["store_code", "pos_id"],
        target_table: "stores",
        target_columns: ["store_code", "pos_id"],
      },
      // 4. Inferred relationship: invoices -> users
      {
        id: "inferred_invoices_users",
        kind: "inferred",
        confidence: 0.85,
        reason: "Column matches primary key",
        source_table: "invoices",
        source_columns: ["customer_id"],
        target_table: "users",
        target_columns: ["id"],
      },
      // 5. Dangling edge: references non-existent table "archived_logs"
      {
        id: "fk_dangling",
        kind: "foreign_key",
        source_table: "orders",
        source_columns: ["log_id"],
        target_table: "archived_logs",
        target_columns: ["id"],
      },
    ],
  };

  it("transforms tables to nodes with column metadata", () => {
    const { nodes } = transformErdDataToGraph(sampleResponse);
    expect(nodes.length).toBe(4);
    const userNode = nodes.find((n) => n.id === "users");
    expect(userNode).toBeDefined();
    expect(userNode?.data.table.kind).toBe("table");
    expect(userNode?.data.columnsToDisplay.length).toBe(3);
  });

  it("filters columns when showPkFkOnly=true", () => {
    const { nodes } = transformErdDataToGraph(sampleResponse, { showPkFkOnly: true });
    const userNode = nodes.find((n) => n.id === "users");
    // "id" is PK, "manager_id" is FK, "email" is neither
    expect(userNode?.data.columnsToDisplay.map((c) => c.name)).toEqual(["id", "manager_id"]);
  });

  it("drops dangling relationships whose target table is missing", () => {
    const { edges } = transformErdDataToGraph(sampleResponse);
    const dangling = edges.find((e) => e.id === "fk_dangling");
    expect(dangling).toBeUndefined();
  });

  it("handles self-loop relationships properly without crashing", () => {
    const { edges } = transformErdDataToGraph(sampleResponse);
    const selfEdge = edges.find((e) => e.id === "fk_users_self");
    expect(selfEdge).toBeDefined();
    expect(selfEdge?.source).toBe("users");
    expect(selfEdge?.target).toBe("users");
    expect(selfEdge?.data.isSelfLoop).toBe(true);
  });

  it("handles composite foreign keys as a single edge with column list", () => {
    const { edges } = transformErdDataToGraph(sampleResponse);
    const compEdge = edges.find((e) => e.id === "fk_orders_stores_comp");
    expect(compEdge).toBeDefined();
    expect(compEdge?.source).toBe("orders");
    expect(compEdge?.target).toBe("stores");
    expect(compEdge?.data.isComposite).toBe(true);
    expect(compEdge?.label).toContain("store_code, pos_id");
  });

  it("omits inferred relationships by default, and includes them when showInferred=true", () => {
    // Default: showInferred=false
    const { edges: defaultEdges } = transformErdDataToGraph(sampleResponse);
    const defaultInferred = defaultEdges.find((e) => e.id === "inferred_invoices_users");
    expect(defaultInferred).toBeUndefined();

    // showInferred=true
    const { edges: withInferred } = transformErdDataToGraph(sampleResponse, { showInferred: true });
    const inferredEdge = withInferred.find((e) => e.id === "inferred_invoices_users");
    expect(inferredEdge).toBeDefined();
    expect(inferredEdge?.style?.strokeDasharray).toBe("5,5");
    expect(inferredEdge?.label).toContain("Inferred (85%)");
  });

  it("ensures NO edges are animated", () => {
    const { edges } = transformErdDataToGraph(sampleResponse, { showInferred: true });
    for (const e of edges) {
      expect(e.animated).toBe(false);
    }
  });

  it("computes dagre layout and preserves user positions over auto-layout", () => {
    const { nodes, edges } = transformErdDataToGraph(sampleResponse, { showInferred: true });
    
    // Auto-layout with dagre
    const layouted = getLayoutedElements(nodes, edges, { direction: "LR" });
    expect(layouted.nodes.length).toBe(4);
    // Nodes should have computed coordinates
    for (const n of layouted.nodes) {
      expect(typeof n.position.x).toBe("number");
      expect(typeof n.position.y).toBe("number");
    }

    // Now test saved user positions override
    const customPositions = {
      users: { x: 999, y: 888 },
    };
    const overridden = getLayoutedElements(nodes, edges, {
      direction: "LR",
      savedPositions: customPositions,
    });
    const userNode = overridden.nodes.find((n) => n.id === "users");
    expect(userNode?.position.x).toBe(999);
    expect(userNode?.position.y).toBe(888);
  });
});
