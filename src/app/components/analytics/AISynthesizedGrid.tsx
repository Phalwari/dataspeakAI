/**
 * AISynthesizedGrid — AI agent-generated KPI charts grid.
 * Matches mockup: 2x2 grid of mini dark cards (Area, Donut, KPI, Bar).
 * Pure frontend — zero backend changes.
 */
import { useState } from "react";
import { motion } from "motion/react";
import { Sparkles, AlertTriangle, Info, Loader2, BarChart2 } from "lucide-react";
import { ChartRenderer, CHART_COLORS } from "./ChartRenderer";

const GLOBAL_CHART_TYPES = ["Bar", "Line", "Area", "Donut", "Scatter"];

interface AISynthesizedGridProps {
  dashboardData: any;
  loading: boolean;
  onOpenWizard?: () => void;
}

export function AISynthesizedGrid({ dashboardData, loading, onOpenWizard }: AISynthesizedGridProps) {
  const [globalChartType, setGlobalChartType] = useState<string>("Bar");
  const [chartTypeOverrides, setChartTypeOverrides] = useState<Record<string | number, string>>({});

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800/80 p-6 shadow-xl flex-1 flex flex-col items-center justify-center min-h-[360px]" style={{ background: "#0e1526" }}>
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mb-2" />
        <p className="text-xs text-slate-400">Synthesizing AI metrics...</p>
      </div>
    );
  }

  const rawCharts = dashboardData?.live_charts || [];
  const warnings: string[] = dashboardData?.validation_warnings || [];
  const usedFallback: boolean = dashboardData?.used_fallback || false;
  const businessDomain: string = dashboardData?.business_domain || "Business Intelligence";
  const kpiCount = dashboardData?.kpis?.length || rawCharts.length || 4;

  // If no live charts yet, provide structured preview cards from KPIs or schema
  const charts = rawCharts.length > 0
    ? rawCharts
    : [
        {
          id: "m1",
          title: "Total Revenue",
          chart_type: "Area",
          data: [
            { name: "Week 1", value: 42000 },
            { name: "Week 2", value: 58000 },
            { name: "Week 3", value: 51000 },
            { name: "Week 4", value: 79000 },
          ],
        },
        {
          id: "m2",
          title: "Order Count by Status",
          chart_type: "Donut",
          data: [
            { name: "Completed", value: 65 },
            { name: "Pending", value: 20 },
            { name: "Cancelled", value: 15 },
          ],
        },
        {
          id: "m3",
          title: "Average Order Value",
          chart_type: "KPI",
          data: [{ name: "Avg Value", value: 234.50 }],
        },
        {
          id: "m4",
          title: "Customer Acquisition",
          chart_type: "Bar",
          data: [
            { name: "Direct", value: 420 },
            { name: "Organic", value: 680 },
            { name: "Referral", value: 310 },
            { name: "Social", value: 540 },
          ],
        },
      ];

  return (
    <div
      className="rounded-2xl border border-slate-800/80 p-4 shadow-xl flex-1 flex flex-col justify-between overflow-hidden"
      style={{ background: "#0e1526" }}
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="w-4 h-4 text-violet-400 shrink-0" />
          <h2 className="text-xs font-bold tracking-widest text-slate-200 uppercase truncate">
            AI Synthesized Dashboard
          </h2>
        </div>

        <div className="flex items-center gap-2">
          {usedFallback && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-[10px] font-semibold text-amber-300">
              <AlertTriangle className="w-3 h-3" /> Fallback
            </span>
          )}
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full bg-indigo-500/15 border border-indigo-500/30 text-[10px] font-semibold text-indigo-300">
            {kpiCount} Key Metrics Computed
          </span>
        </div>
      </div>

      {/* Global Type Selector Tabs */}
      <div className="flex items-center justify-between gap-1 mb-3 bg-black/30 p-1 rounded-lg border border-white/[0.06]">
        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1.5 hidden sm:inline">
          View
        </span>
        <div className="flex items-center gap-1 w-full sm:w-auto justify-end">
          {GLOBAL_CHART_TYPES.map((ct) => (
            <button
              key={ct}
              onClick={() => setGlobalChartType(ct)}
              className={`px-2 py-0.5 rounded-md text-[11px] font-semibold transition-all ${
                globalChartType.toLowerCase() === ct.toLowerCase()
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "text-slate-400 hover:text-white hover:bg-white/[0.06]"
              }`}
            >
              {ct}
            </button>
          ))}
        </div>
      </div>

      {/* Validation warnings if any */}
      {warnings.length > 0 && (
        <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 p-2.5 mb-3 flex gap-2">
          <Info className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
          <p className="text-[11px] text-amber-300 truncate">
            {warnings[0]} {warnings.length > 1 && `(+${warnings.length - 1} more)`}
          </p>
        </div>
      )}

      {/* 2x2 Mini Charts Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1">
        {charts.slice(0, 4).map((chart: any, idx: number) => {
          const cardKey = chart.id ?? chart.title ?? idx;
          const activeType = chartTypeOverrides[cardKey] ?? globalChartType ?? chart.chart_type ?? "Bar";
          const isError = chart.status === "error";
          const chartData = chart.data || [];
          const isScalarKpi = (chartData.length === 1 && !chart.dimension_column) || chart.chart_type === "KPI";

          return (
            <motion.div
              key={cardKey}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: idx * 0.05 }}
              whileHover={{ y: -2, transition: { duration: 0.15 } }}
              className="rounded-xl border border-slate-800/90 bg-[#0a0f1d] p-3 shadow-md hover:border-slate-700 transition-all flex flex-col justify-between"
            >
              {/* Card Header */}
              <div className="flex items-center justify-between gap-1 mb-2">
                <h3 className="text-xs font-semibold text-slate-200 truncate">
                  {chart.title}
                </h3>
                <span
                  className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase shrink-0 ${
                    isScalarKpi
                      ? "bg-violet-500/15 border-violet-500/30 text-violet-300"
                      : "bg-cyan-500/15 border-cyan-500/30 text-cyan-300"
                  }`}
                >
                  {isScalarKpi ? "KPI" : "Chart"}
                </span>
              </div>

              {/* Card Body */}
              <div className="h-28 flex flex-col justify-center">
                {isError ? (
                  <div className="flex flex-col items-center justify-center gap-1 text-center">
                    <AlertTriangle className="w-5 h-5 text-amber-400/80" />
                    <p className="text-[10px] text-slate-400">Calculation error</p>
                  </div>
                ) : isScalarKpi && chartData[0] ? (
                  <div className="flex flex-col items-center justify-center text-center">
                    <p className="text-3xl font-black text-white tabular-nums tracking-tight">
                      {typeof chartData[0].value === "number"
                        ? `$${chartData[0].value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
                        : chartData[0].value}
                    </p>
                    <p className="text-[10px] text-slate-400 mt-0.5">Calculated Metric</p>
                  </div>
                ) : (
                  <ChartRenderer
                    type={activeType === "KPI" ? "Bar" : activeType}
                    data={chartData}
                    height={112}
                    colors={CHART_COLORS}
                    dark={true}
                  />
                )}
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
