import React from "react";
import { X, Key, Link2, Eye, Table2, ArrowRight, ArrowLeft } from "lucide-react";
import { ErdTable, ErdRelationship } from "../../utils/erdTransform";

interface TableDetailsDrawerProps {
  table: ErdTable | null;
  relationships: ErdRelationship[];
  onClose: () => void;
  onSelectTable: (tableName: string) => void;
}

export function TableDetailsDrawer({
  table,
  relationships,
  onClose,
  onSelectTable,
}: TableDetailsDrawerProps) {
  if (!table) return null;

  const isView = table.kind === "view";

  // Outbound: this table is child referencing a parent
  const outboundRels = relationships.filter((r) => r.source_table === table.name);
  // Inbound: other tables reference this table
  const inboundRels = relationships.filter((r) => r.target_table === table.name);

  return (
    <div
      role="complementary"
      aria-label={`Details for table ${table.name}`}
      className="absolute top-4 right-4 z-20 w-80 max-h-[calc(100%-2rem)] flex flex-col rounded-xl border border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md shadow-2xl transition-all duration-200 text-xs overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-start justify-between gap-2">
        <div className="overflow-hidden">
          <div className="flex items-center gap-1.5 mb-1">
            {isView ? (
              <Eye className="w-4 h-4 text-purple-600 dark:text-purple-400 shrink-0" />
            ) : (
              <Table2 className="w-4 h-4 text-slate-500 dark:text-slate-400 shrink-0" />
            )}
            <h3
              className="font-bold text-sm text-slate-900 dark:text-slate-100 truncate"
              title={table.name}
            >
              {table.name}
            </h3>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
              {table.kind}
            </span>
            {table.schema && (
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400">
                schema: {table.schema}
              </span>
            )}
          </div>
        </div>

        <button
          onClick={onClose}
          aria-label="Close details panel"
          className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content scroll area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Columns list */}
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-2 flex items-center justify-between">
            <span>Columns</span>
            <span className="text-[11px] font-normal text-slate-400">
              {table.columns.length} total
            </span>
          </h4>
          <div className="space-y-1">
            {table.columns.map((c) => (
              <div
                key={c.name}
                className="p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800/80 flex items-center justify-between"
              >
                <div className="flex items-center gap-1.5 overflow-hidden">
                  {c.is_pk && (
                    <Key className="w-3.5 h-3.5 text-amber-500 shrink-0" title="Primary Key" />
                  )}
                  {c.is_fk && (
                    <Link2 className="w-3.5 h-3.5 text-indigo-500 shrink-0" title="Foreign Key" />
                  )}
                  <span
                    className={`font-medium truncate ${
                      c.is_pk ? "text-slate-900 dark:text-slate-100" : "text-slate-700 dark:text-slate-300"
                    }`}
                  >
                    {c.name}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <span className="font-mono text-[10px] text-slate-500 uppercase">
                    {c.type}
                  </span>
                  {!c.nullable && (
                    <span className="px-1 py-0.2 rounded text-[9px] bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400">
                      NOT NULL
                    </span>
                  )}
                  {c.is_unique && (
                    <span className="px-1 py-0.2 rounded text-[9px] bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400">
                      UNIQUE
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Outbound Relationships (References) */}
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-2 flex items-center gap-1">
            <ArrowRight className="w-3.5 h-3.5 text-indigo-500" />
            <span>References (Outbound)</span>
            <span className="text-[11px] font-normal text-slate-400 ml-auto">
              {outboundRels.length}
            </span>
          </h4>
          {outboundRels.length === 0 ? (
            <p className="text-[11px] text-slate-400 italic">No outgoing foreign keys</p>
          ) : (
            <div className="space-y-1.5">
              {outboundRels.map((r) => (
                <div
                  key={r.id}
                  onClick={() => onSelectTable(r.target_table)}
                  className="p-2 rounded-lg bg-indigo-50/60 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900/60 hover:border-indigo-300 dark:hover:border-indigo-700 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between font-medium text-indigo-700 dark:text-indigo-300">
                    <span>{r.target_table}</span>
                    {r.kind === "inferred" && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400">
                        Inferred
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                    ({r.source_columns.join(", ")}) → ({r.target_columns.join(", ")})
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Inbound Relationships (Referenced By) */}
        <div>
          <h4 className="font-semibold text-slate-900 dark:text-slate-100 mb-2 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5 text-emerald-500" />
            <span>Referenced By (Inbound)</span>
            <span className="text-[11px] font-normal text-slate-400 ml-auto">
              {inboundRels.length}
            </span>
          </h4>
          {inboundRels.length === 0 ? (
            <p className="text-[11px] text-slate-400 italic">No tables reference this table</p>
          ) : (
            <div className="space-y-1.5">
              {inboundRels.map((r) => (
                <div
                  key={r.id}
                  onClick={() => onSelectTable(r.source_table)}
                  className="p-2 rounded-lg bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-900/60 hover:border-emerald-300 dark:hover:border-emerald-700 cursor-pointer transition-colors"
                >
                  <div className="flex items-center justify-between font-medium text-emerald-700 dark:text-emerald-300">
                    <span>{r.source_table}</span>
                    {r.kind === "inferred" && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-amber-100 text-amber-700 dark:bg-amber-950/60 dark:text-amber-400">
                        Inferred
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                    ({r.source_columns.join(", ")}) → ({r.target_columns.join(", ")})
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
