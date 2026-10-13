# Entity-Relationship Diagram (ERD) & Schema Relationships

## 1. Overview
The **Entity-Relationship Diagram (ERD)** module enables interactive, visual exploration of relational database schemas in DataSpeakAI. It features high-performance schema reflection using SQLAlchemy 2.0 bulk inspection, catalog-first persistence, heuristic foreign key inference, and a responsive React Flow visual canvas.

---

## 2. API Specification

### Endpoint
`GET /api/databases/{id}/erd`

### Query Parameters
| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `schema` | `string` | `null` | Target database schema name (e.g., PostgreSQL schema like `public` or `sales`). |
| `refresh` | `boolean` | `false` | When `true`, bypasses catalog cache and triggers live database reflection. Subject to refresh cooldown. |
| `include_inferred` | `boolean` | `false` | When `true`, runs name-based heuristics to infer implicit relationships for schemas lacking physical foreign keys. |

### Response Schema (`DatabaseErdResponse`)
```json
{
  "database_id": 5,
  "dialect": "sqlite",
  "schema": "main",
  "last_sync": "2026-10-14T02:17:11.466Z",
  "source": "catalog",
  "truncated": false,
  "table_count": 13,
  "warnings": [],
  "tables": [
    {
      "id": "Orders",
      "name": "Orders",
      "schema": null,
      "kind": "table",
      "columns": [
        {
          "name": "OrderID",
          "type": "INTEGER",
          "nullable": false,
          "is_pk": true,
          "is_fk": false,
          "is_unique": false
        },
        {
          "name": "CustomerID",
          "type": "TEXT",
          "nullable": true,
          "is_pk": false,
          "is_fk": true,
          "is_unique": false
        }
      ]
    }
  ],
  "relationships": [
    {
      "id": "rel_Orders_Customers_1",
      "kind": "foreign_key",
      "constraint_name": "fk_orders_customer",
      "confidence": null,
      "reason": null,
      "source_table": "Orders",
      "source_columns": ["CustomerID"],
      "target_table": "Customers",
      "target_columns": ["CustomerID"]
    }
  ]
}
```

---

## 3. Architecture & Design Decisions

### D1: Catalog-First
The ERD endpoint first queries the local database catalog (`TableMetadata`, `ColumnMetadata`, `TableRelationship`). If cached metadata exists and `refresh=false`, the response is generated immediately from the catalog with `"source": "catalog"`. If the catalog is empty or `refresh=true`, live reflection is executed and the catalog is updated in a single transaction.

### D2: Constraint-Level Relationships
Physical foreign keys are persisted in the `table_relationships` table (`TableRelationship` ORM model). Each constraint is represented as a single relationship containing lists of source and target columns (`source_columns`, `target_columns`), properly supporting composite foreign keys and multiple distinct foreign keys between the same pair of tables.

### D3: SQLAlchemy 2.0 Bulk Reflection
Reflection uses SQLAlchemy 2.0 inspector methods:
- `inspector.get_multi_columns()`
- `inspector.get_multi_pk_constraint()`
- `inspector.get_multi_foreign_keys()`

Falls back to individual `get_columns` / `get_foreign_keys` calls only if the dialect raises `NotImplementedError` (or for database views where multi-column reflection is unsupported).

### D4: Relational Dialects Only
ERD reflection is supported exclusively for relational databases (`postgresql`, `mysql`, `mariadb`, `sqlite`). Document databases (`mongodb`, `firebase`) reject ERD requests with HTTP 400 (`ERD is supported only for relational databases`).

### D5: SSRF Prevention & Host Validation
- **Host Validation**: Network-based database connections (PostgreSQL, MySQL, MariaDB) validate host IP addresses prior to connecting. Loopback (`127.0.0.0/8`), link-local (`169.254.0.0/16`), and private RFC 1918 networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) are blocked by default.
  - Can be relaxed in controlled environments via `ALLOW_PRIVATE_DB_HOSTS=true`.
- **SQLite Confinement**: File paths must exist on disk and must not contain directory traversal sequences (`..`).

### D6: Strict Tenant Scoping
Database connection lookup is strictly scoped to the authenticated user's `tenant_id`. Accessing an ID belonging to another tenant returns HTTP 404.

### D7: Cooldown Rate Limiting (No In-Memory Cache)
Refresh requests (`refresh=true`) enforce a per-tenant, per-database cooldown window (default 30 seconds, configurable via `ERD_REFRESH_COOLDOWN_SECONDS`). Repeated refresh attempts within this window return HTTP 429 with a standard `Retry-After` header.

### D8: Frontend Architecture
- **Frameworks**: `@xyflow/react` v12, `@dagrejs/dagre`, and `vitest`.
- **Lazy Routing**: The `/dashboard/databases/:id/erd` page is loaded with `React.lazy` to keep the initial application bundle lightweight.
- **Large Schema Virtualization**: Schemas with >60 tables automatically enable viewport element virtualization (`onlyRenderVisibleElements={true}`) and compact node headers to maintain 60 FPS panning.
- **Position Persistence**: User node positions are persisted in `localStorage` under `dataspeak_erd_positions_{id}_{schema}`.

---

## 4. Known Limitations
1. **Mocked Testing for PostgreSQL and MySQL**: In the local test suite, PostgreSQL and MySQL reflection behaviors are verified using mocked inspectors and schema fixtures. *No live server used* for PostgreSQL or MySQL.
2. **Document Databases Unsupported**: MongoDB and Firebase do not support relational ERDs.
3. **SQLite Path Confinement**: Confinement is based on path validation and traversal token rejection.
