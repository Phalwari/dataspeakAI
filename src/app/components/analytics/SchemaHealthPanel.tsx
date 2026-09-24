/**
 * SchemaHealthPanel — Collapsible schema quality accordion in dark glass style.
 * Visualizes schema_summary from GET /api/analytics/dashboard/{id}.
 * Shows null% bars, cardinality pills, data type badges per column.
 * Matches mockup: full width bottom row with dark sleek aesthetic.
 * Pure frontend — zero backend changes.
 */
import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  ChevronDown, ChevronRight, Database, AlertTriangle, CheckCircle2,
} from "lucide-react";

interface SchemaEntry {
  table_name: string;
  column_name: string;
  data_type: string;
  is_measure: boolean;
  is_dimension: boolean;
  is_time_axis: boolean;
  cardinality: number | null;
  null_percentage: number | null;
}

interface SchemaHealthPanelProps {
  schemaSummary: SchemaEntry[] | null | undefined;
}

type FilterTab = "all" | "measures" | "dimensions" | "time" | "highnull";

function NullBar({ pct }: { pct: number | null }) {
  if (pct == null) return <span className="text-[10px] text-slate-500">—</span>;
  const color =
    pct < 5 ? "bg-emerald-500" : pct < 20 ? "bg-amber-500" : "bg-rose-500";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-16 h-1.5 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      <span className={`text-[10px] font-mono ${pct > 20 ? "text-rose-400" : pct > 5 ? "text-amber-400" : "text-emerald-400"}`}>
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

function DataTypeBadge({ type }: { type: string }) {
  const label = (type || "UNKNOWN").toUpperCase().slice(0, 12);
  const colorMap: Record<string, string> = {
    INTEGER: "bg-blue-500/15 text-blue-300 border-blue-500/30",
    BIGINT: "bg-blue-500/15 text-blue-300 border-blue-500/30",
    NUMERIC: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
    FLOAT: "bg-indigo-500/15 text-indigo-300 border-indigo-500/30",
    VARCHAR: "bg-violet-500/15 text-violet-300 border-violet-500/30",
    TEXT: "bg-violet-500/15 text-violet-300 border-violet-500/30",
    TIMESTAMP: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    DATE: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
    BOOLEAN: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  };
  const cls = colorMap[label] || "bg-slate-800 text-slate-300 border-slate-700";
  return (
    <span className={`inline-flex px-1.5 py-0.5 rounded text-[9px] font-mono font-bold border ${cls}`}>
      {label}
    </span>
  );
}

function RoleDot({ active, color }: { active: boolean; color: string }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${active ? color : "bg-slate-700"}`} />
  );
}

export function SchemaHealthPanel({ schemaSummary }: SchemaHealthPanelProps) {
  const [open, setOpen] = useState(false);
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<FilterTab>("all");

  if (!schemaSummary || schemaSummary.length === 0) return null;

  // Group by table
  const byTable: Record<string, SchemaEntry[]> = {};
  for (const e of schemaSummary) {
    if (!byTable[e.table_name]) byTable[e.table_name] = [];
    byTable[e.table_name].push(e);
  }

  const toggleTable = (t: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev);
      if (next.has(t)) next.delete(t);
      else next.add(t);
      return next;
    });
  };

  const filterEntry = (e: SchemaEntry): boolean => {
    if (filter === "all") return true;
    if (filter === "measures") return e.is_measure;
    if (filter === "dimensions") return e.is_dimension;
    if (filter === "time") return e.is_time_axis;
    if (filter === "highnull") return (e.null_percentage ?? 0) > 20;
    return true;
  };

  const totalCols = schemaSummary.length;
  const highNullCount = schemaSummary.filter((e) => (e.null_percentage ?? 0) > 20).length;

  const TABS: { id: FilterTab; label: string }[] = [
    { id: "all", label: `All (${totalCols})` },
    { id: "measures", label: "Measures" },
    { id: "dimensions", label: "Dimensions" },
    { id: "time", label: "Time" },
    { id: "highnull", label: `⚠️ High Null (${highNullCount})` },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="rounded-2xl border border-slate-800/80 shadow-xl overflow-hidden"
      style={{ background: "#0e1526" }}
    >
      {/* Header toggle */}
      <button
        onClick={() => setOpen((p) => !p)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-white/[0.02] transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center">
            <Database className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-left">
            <h3 className="text-sm font-bold text-white">Schema Health &amp; Data Quality</h3>
            <p className="text-[11px] text-slate-400">
              {Object.keys(byTable).length} tables · {totalCols} columns
              {highNullCount > 0 && (
                <span className="ml-2 text-amber-400">· {highNullCount} high-null columns</span>
              )}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {highNullCount > 0 && (
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-[10px] font-semibold text-amber-300">
              <AlertTriangle className="w-3 h-3" /> {highNullCount} issues
            </span>
          )}
          {highNullCount === 0 && totalCols > 0 && (
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-[10px] font-semibold text-emerald-300">
              <CheckCircle2 className="w-3 h-3" /> Healthy
            </span>
          )}
          {open ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
        </div>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
          >
            {/* Filter tabs */}
            <div className="px-5 pb-3 pt-1 border-t border-white/[0.06] flex items-center gap-1.5 flex-wrap bg-black/20">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setFilter(tab.id)}
                  className={`px-3 py-1 rounded-full text-[11px] font-semibold transition-all ${
                    filter === tab.id
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "bg-slate-900 border border-slate-700/60 text-slate-400 hover:text-white hover:bg-slate-800"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tables */}
            <div className="divide-y divide-white/[0.04] border-t border-white/[0.06]">
              {Object.entries(byTable).map(([tableName, entries]) => {
                const filtered = entries.filter(filterEntry);
                if (filtered.length === 0) return null;
                const isExpanded = expandedTables.has(tableName);
                return (
                  <div key={tableName}>
                    <button
                      onClick={() => toggleTable(tableName)}
                      className="w-full flex items-center gap-3 px-5 py-3 hover:bg-white/[0.02] transition-colors text-left"
                    >
                      {isExpanded
                        ? <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        : <ChevronRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />}
                      <span className="text-sm font-semibold text-slate-200">{tableName}</span>
                      <span className="text-[10px] text-slate-500 font-mono">{filtered.length} columns</span>
                    </button>

                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          {/* Column header row */}
                          <div className="px-10 py-2 grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 bg-black/30 border-y border-white/[0.04]">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Column</span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider w-20 text-center">Type</span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider w-16 text-center">Null%</span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider w-16 text-center">Cardinality</span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider w-20 text-center">Role</span>
                          </div>

                          {filtered.map((e) => (
                            <div
                              key={e.column_name}
                              className="px-10 py-2 grid grid-cols-[1fr_auto_auto_auto_auto] gap-3 items-center hover:bg-white/[0.02] border-b border-white/[0.02]"
                            >
                              <span className="text-xs font-mono text-slate-300 truncate">{e.column_name}</span>
                              <div className="w-20 flex justify-center">
                                <DataTypeBadge type={e.data_type} />
                              </div>
                              <div className="w-16 flex justify-center">
                                <NullBar pct={e.null_percentage} />
                              </div>
                              <div className="w-16 text-center">
                                {e.cardinality != null ? (
                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 text-slate-300 border border-slate-700">
                                    {e.cardinality.toLocaleString()}
                                  </span>
                                ) : (
                                  <span className="text-[10px] text-slate-500">—</span>
                                )}
                              </div>
                              <div className="w-20 flex items-center justify-center gap-1.5">
                                <RoleDot active={e.is_measure} color="bg-indigo-400" />
                                <RoleDot active={e.is_dimension} color="bg-violet-400" />
                                <RoleDot active={e.is_time_axis} color="bg-emerald-400" />
                              </div>
                            </div>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>

            {/* Legend */}
            <div className="px-5 py-2.5 border-t border-white/[0.06] flex items-center gap-4 bg-black/30">
              <span className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Legend:</span>
              {[
                { color: "bg-indigo-400", label: "Measure" },
                { color: "bg-violet-400", label: "Dimension" },
                { color: "bg-emerald-400", label: "Time" },
              ].map(({ color, label }) => (
                <div key={label} className="flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${color}`} />
                  <span className="text-[10px] text-slate-400">{label}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
