/**
 * LiveExplorerCanvas — Dark glass panel with filter bar + interactive chart.
 * Extracted and redesigned from the original AnalyticsPage.tsx.
 * All API logic lives in the parent (AnalyticsPage) — this is display only.
 * Pure frontend — no backend files touched.
 */
import { motion, AnimatePresence } from "motion/react";
import { Activity, Loader2, Copy, Check, Table2 } from "lucide-react";
import { useState } from "react";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../ui/select";
import { ChartRenderer, CHART_COLORS } from "./ChartRenderer";

const CHART_TYPES = [
  { id: "Bar", label: "Bar" },
  { id: "Line", label: "Line" },
  { id: "Area", label: "Area" },
  { id: "Donut", label: "Donut" },
  { id: "Scatter", label: "Scatter" },
];

const AGG_OPTIONS = ["SUM", "AVG", "COUNT", "MAX", "MIN"];

interface LiveExplorerCanvasProps {
  availableTables: string[];
  availableMeasures: string[];
  availableDimensions: string[];
  selectedTable: string;
  selectedMeasure: string;
  selectedDimension: string;
  selectedAgg: string;
  chartType: string;
  queryResult: any;
  queryLoading: boolean;
  recommendedChartTypes?: string[];
  onTableChange: (t: string) => void;
  onMeasureChange: (m: string) => void;
  onDimensionChange: (d: string) => void;
  onAggChange: (a: string) => void;
  onChartTypeChange: (c: string) => void;
}

export function LiveExplorerCanvas({
  availableTables,
  availableMeasures,
  availableDimensions,
  selectedTable,
  selectedMeasure,
  selectedDimension,
  selectedAgg,
  chartType,
  queryResult,
  queryLoading,
  recommendedChartTypes = [],
  onTableChange,
  onMeasureChange,
  onDimensionChange,
  onAggChange,
  onChartTypeChange,
}: LiveExplorerCanvasProps) {
  const [copied, setCopied] = useState(false);

  if (availableTables.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: "easeOut", delay: 0.1 }}
        className="rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl flex-1 flex flex-col min-h-[380px]"
        style={{ background: "#0e1526" }}
      >
        <div className="px-5 py-3 border-b border-white/[0.06] flex items-center justify-between bg-white/[0.02]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-slate-500" />
            <h2 className="text-xs font-bold tracking-widest text-slate-300 uppercase">
              Live Explorer Canvas
            </h2>
          </div>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center">
          <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mb-3">
            <Table2 className="w-6 h-6 text-indigo-400" />
          </div>
          <h3 className="text-sm font-semibold text-slate-200 mb-1">
            No Tabular Entities Available
          </h3>
          <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
            This source does not contain tabular records or schema measures. Select a tabular document or connected database to query interactively.
          </p>
        </div>
      </motion.div>
    );
  }

  const sqlPreview = selectedDimension
    ? `SELECT "${selectedDimension}", ${selectedAgg}("${selectedMeasure}") FROM "${selectedTable}"`
    : `SELECT ${selectedAgg}("${selectedMeasure}") FROM "${selectedTable}"`;

  const handleCopySQL = () => {
    navigator.clipboard.writeText(sqlPreview).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const chartData = queryResult?.chart_data || [];

  const handleDimensionSelect = (val: string) => {
    onDimensionChange(val === "__none__" ? "" : val);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: "easeOut", delay: 0.1 }}
      className="rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl flex-1 flex flex-col"
      style={{ background: "#0e1526" }}
    >
      {/* Top Section Header */}
      <div className="px-5 py-3 border-b border-white/[0.06] flex items-center justify-between bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          <h2 className="text-xs font-bold tracking-widest text-slate-300 uppercase">
            Live Explorer Canvas
          </h2>
          {queryResult?.is_sampled && (
            <span
              className="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-500/15 text-amber-400 border border-amber-500/30"
              title={`Aggregates and KPIs reflect all ${queryResult.total_rows?.toLocaleString() ?? "total"} rows; visual plot sampled to ${queryResult.sample_size?.toLocaleString() ?? "sample"} points for smooth rendering.`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              Sampled Plot ({queryResult.sample_size?.toLocaleString()}/{queryResult.total_rows?.toLocaleString()} rows)
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 p-1 rounded-lg bg-black/30 border border-white/[0.08]">
          {CHART_TYPES.map((ct) => {
            const isRec = recommendedChartTypes?.includes(ct.id);
            return (
              <button
                key={ct.id}
                onClick={() => onChartTypeChange(ct.id)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150 flex items-center gap-1.5 ${
                  chartType === ct.id
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/40"
                    : isRec
                    ? "text-amber-300 hover:text-white hover:bg-white/[0.08] bg-amber-500/10 border border-amber-500/30"
                    : "text-slate-400 hover:text-white hover:bg-white/[0.06]"
                }`}
                title={isRec ? "⭐ Recommended by Source Archetype" : undefined}
              >
                {isRec && chartType !== ct.id && (
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                )}
                {ct.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="px-5 py-3.5 border-b border-white/[0.06] flex flex-wrap items-center gap-3 bg-white/[0.01]">
        {/* Table */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Table</label>
          <Select value={selectedTable} onValueChange={onTableChange}>
            <SelectTrigger className="w-36 bg-slate-900/90 border-slate-700/80 text-white text-xs h-8 hover:border-slate-600">
              <SelectValue placeholder="Table" />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              {availableTables.map((t) => (
                <SelectItem key={t} value={t}>{t}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Metric */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Target Metric</label>
          <Select value={selectedMeasure} onValueChange={onMeasureChange}>
            <SelectTrigger className="w-40 bg-slate-900/90 border-slate-700/80 text-white text-xs h-8 hover:border-slate-600">
              <SelectValue placeholder="Metric" />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              {availableMeasures.map((m) => (
                <SelectItem key={m} value={m}>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Group By */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Group By</label>
          <Select value={selectedDimension || "__none__"} onValueChange={handleDimensionSelect}>
            <SelectTrigger className="w-36 bg-slate-900/90 border-slate-700/80 text-white text-xs h-8 hover:border-slate-600">
              <SelectValue placeholder="Dimension" />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              <SelectItem value="__none__">None (Total)</SelectItem>
              {availableDimensions.map((d) => (
                <SelectItem key={d} value={d}>{d}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Aggregation */}
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Aggregation</label>
          <Select value={selectedAgg} onValueChange={onAggChange}>
            <SelectTrigger className="w-24 bg-slate-900/90 border-slate-700/80 text-white text-xs h-8 hover:border-slate-600">
              <SelectValue placeholder="Agg" />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              {AGG_OPTIONS.map((a) => (
                <SelectItem key={a} value={a}>{a}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* SQL preview line */}
      <div className="px-5 py-2 border-b border-white/[0.04] flex items-center justify-between gap-3 bg-black/20">
        <div className="flex items-center gap-2 flex-1 min-w-0 font-mono text-[11px]">
          <span className="px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold text-[10px]">
            SQL
          </span>
          <span className="text-slate-300 truncate">
            {sqlPreview}
          </span>
        </div>
        <button
          onClick={handleCopySQL}
          className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white transition-colors shrink-0"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {/* Chart */}
      <div className="p-5">
        <AnimatePresence mode="wait">
          {queryLoading ? (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center h-72 gap-3"
            >
              <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
              <p className="text-sm text-slate-500">Executing query...</p>
            </motion.div>
          ) : chartData.length > 0 ? (
            <motion.div
              key={`chart-${chartType}`}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
            >
              <ChartRenderer
                type={chartType === "Donut" ? "donut" : chartType}
                data={chartType === "Scatter"
                  ? (queryResult?.scatter_data?.length > 0
                    ? queryResult.scatter_data
                    : chartData.map((d: any, i: number) => ({ ...d, x: i + 1, y: d.value })))
                  : chartData}
                height={320}
                colors={CHART_COLORS}
                dark={true}
              />
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-72 gap-3"
            >
              <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
                <Activity className="w-7 h-7 text-slate-600" />
              </div>
              <p className="text-sm text-slate-500">No data for selected combination</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
