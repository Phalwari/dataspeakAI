/**
 * SourceArchetypeBanner — Discovered Source Archetype Banner.
 * Displays discovered database/document identity, detected structure (tables, measures,
 * time axes), and interactive recommended visualization referral pills.
 */
import { motion } from "motion/react";
import {
  Database,
  FileSpreadsheet,
  BookOpen,
  Sparkles,
  TrendingUp,
  Clock,
  Layers,
  ArrowRight,
} from "lucide-react";

export interface SourceArchetypeBannerProps {
  discovery?: {
    source_name?: string;
    source_type?: "database" | "document";
    source_archetype?: string;
    archetype_display_name?: string;
    archetype_description?: string;
    detected_entities?: string[];
    detected_measures?: string[];
    detected_dimensions?: string[];
    detected_time_axes?: string[];
    stats?: Record<string, any>;
    recommended_chart_families?: string[];
  } | null;
  recommendations?: Array<{
    id: string;
    title: string;
    chart_type: string;
    description: string;
    archetype_fit_reason: string;
    target_metric: string;
  }>;
  onSelectReferral?: (chartType: string, targetMetric?: string) => void;
}

export function SourceArchetypeBanner({
  discovery,
  recommendations,
  onSelectReferral,
}: SourceArchetypeBannerProps) {
  if (!discovery) return null;

  const isDoc = discovery.source_type === "document";
  const archetype = discovery.source_archetype || "relational_timeseries";

  const getArchetypeIcon = () => {
    switch (archetype) {
      case "relational_timeseries":
        return <TrendingUp className="w-5 h-5 text-indigo-400" />;
      case "relational_categorical":
        return <Database className="w-5 h-5 text-cyan-400" />;
      case "tabular_spreadsheet":
        return <FileSpreadsheet className="w-5 h-5 text-emerald-400" />;
      case "document_knowledge":
        return <BookOpen className="w-5 h-5 text-amber-400" />;
      default:
        return <Database className="w-5 h-5 text-blue-400" />;
    }
  };

  const getArchetypeGradient = () => {
    switch (archetype) {
      case "relational_timeseries":
        return "from-indigo-900/40 via-purple-900/20 to-slate-900/40 border-indigo-500/30";
      case "relational_categorical":
        return "from-cyan-900/40 via-blue-900/20 to-slate-900/40 border-cyan-500/30";
      case "tabular_spreadsheet":
        return "from-emerald-900/40 via-teal-900/20 to-slate-900/40 border-emerald-500/30";
      case "document_knowledge":
        return "from-amber-900/40 via-orange-900/20 to-slate-900/40 border-amber-500/30";
      default:
        return "from-blue-900/40 via-indigo-900/20 to-slate-900/40 border-blue-500/30";
    }
  };

  const entityCount = discovery.detected_entities?.length ?? 0;
  const measureCount = discovery.detected_measures?.length ?? 0;
  const dimensionCount = discovery.detected_dimensions?.length ?? 0;
  const timeAxis = discovery.detected_time_axes?.[0] || null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={`rounded-2xl border p-5 shadow-2xl backdrop-blur-xl bg-gradient-to-r ${getArchetypeGradient()}`}
    >
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        {/* Left: Discovered Source Identity & Archetype */}
        <div className="space-y-2 min-w-0 max-w-2xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900/90 border border-slate-700/80 text-xs font-bold text-white shadow-inner">
              {getArchetypeIcon()}
              <span>{discovery.archetype_display_name || "Discovered Source"}</span>
            </span>

            <span className="px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-400/20 text-[11px] font-semibold text-indigo-300">
              {isDoc ? "Document Intelligence" : "SQL Relational"}
            </span>

            <span className="text-xs text-slate-400 font-mono">
              Source: <span className="text-slate-200 font-medium">{discovery.source_name}</span>
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {discovery.archetype_description}
          </p>

          {/* Structural badges */}
          <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-slate-300">
            <div className="flex items-center gap-1 bg-slate-900/60 px-2.5 py-1 rounded-lg border border-slate-800">
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              <span>{entityCount} {isDoc ? "Sections / Tables" : "Tables"}</span>
            </div>

            <div className="flex items-center gap-1 bg-slate-900/60 px-2.5 py-1 rounded-lg border border-slate-800">
              <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
              <span>{measureCount} Measures</span>
            </div>

            <div className="flex items-center gap-1 bg-slate-900/60 px-2.5 py-1 rounded-lg border border-slate-800">
              <Database className="w-3.5 h-3.5 text-cyan-400" />
              <span>{dimensionCount} Dimensions</span>
            </div>

            {timeAxis && (
              <div className="flex items-center gap-1 bg-slate-900/60 px-2.5 py-1 rounded-lg border border-slate-800">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                <span>Time Axis: <span className="font-mono text-amber-300">{timeAxis.split(".").pop()}</span></span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Recommended Visualization Referral Pills */}
        {recommendations && recommendations.length > 0 && (
          <div className="flex flex-col gap-2 shrink-0 max-w-md bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                <span>Recommended Visualizations</span>
              </div>
              <span className="text-[10px] text-slate-400 font-mono">Archetype Fit</span>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {recommendations.slice(0, 4).map((rec) => (
                <button
                  key={rec.id}
                  onClick={() => onSelectReferral?.(rec.chart_type, rec.target_metric)}
                  className="group flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-indigo-600/20 border border-slate-700/60 hover:border-indigo-400/50 text-[11px] text-slate-200 hover:text-indigo-200 transition-all text-left"
                  title={rec.archetype_fit_reason}
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400 group-hover:scale-125 transition-transform" />
                  <span className="font-semibold">{rec.chart_type}</span>
                  <span className="text-slate-400 text-[10px] group-hover:text-slate-300">
                    ({rec.title.length > 18 ? rec.title.slice(0, 18) + "…" : rec.title})
                  </span>
                  <ArrowRight className="w-2.5 h-2.5 opacity-0 group-hover:opacity-100 transition-opacity ml-0.5" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
