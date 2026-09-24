/**
 * AnalyticsHeader — Premium dark header bar for the analytics page.
 * Shows DB selector, date range, profiling status badge,
 * Re-profile button, and the "Setup Domain ⚡" wizard trigger.
 * Pure frontend — zero backend changes.
 */
import { motion } from "motion/react";
import {
  BarChart3,
  RefreshCw,
  Zap,
  CheckCircle2,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { Button } from "../ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";

interface AnalyticsHeaderProps {
  selectedDb: string;
  dateRange: string;
  databasesList: Array<{ id: number; name: string; db_type: string }>;
  isProfiling: boolean;
  dashboardData: any;
  onDbChange: (id: string) => void;
  onDateRangeChange: (range: string) => void;
  onTriggerProfile: () => void;
  onOpenWizard: () => void;
}

export function AnalyticsHeader({
  selectedDb,
  dateRange,
  databasesList,
  isProfiling,
  dashboardData,
  onDbChange,
  onDateRangeChange,
  onTriggerProfile,
  onOpenWizard,
}: AnalyticsHeaderProps) {
  const kpiCount = dashboardData?.kpis?.length ?? 0;
  const businessDomain = dashboardData?.business_domain;
  const usedFallback = dashboardData?.used_fallback;

  return (
    <motion.div
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="rounded-2xl border border-slate-800/80 shadow-2xl px-5 py-4"
      style={{ background: "#0e1526" }}
    >
      <div className="flex flex-wrap items-center justify-between gap-4">
        {/* Left: Title & domain badges */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shrink-0 shadow-lg shadow-indigo-500/25">
            <BarChart3 className="w-5 h-5 text-white" />
          </div>
          <div className="min-w-0">
            <h1 className="text-xl font-black text-white tracking-tight leading-none">
              Analytics &amp; Visualization
            </h1>
            <p className="text-[11px] text-slate-400 mt-1">
              Live database intelligence &amp; synthesized metrics
            </p>
          </div>

          {/* Domain badge */}
          {businessDomain && (
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-violet-950/80 border border-violet-500/40 text-xs font-semibold text-violet-300 tracking-wide">
              {businessDomain}
            </span>
          )}

          {/* Fallback warning */}
          {usedFallback && (
            <span className="hidden md:inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-[10px] font-semibold text-amber-300">
              <AlertTriangle className="w-3 h-3" />
              Rule-Based Fallback
            </span>
          )}
        </div>

        {/* Right: Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* KPI live badge */}
          {selectedDb && selectedDb !== "all" && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/70 border border-emerald-500/40"
            >
              {isProfiling ? (
                <Loader2 className="w-3.5 h-3.5 text-amber-400 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              )}
              <span className="text-xs font-semibold text-emerald-300">
                {isProfiling ? "Profiling..." : `${kpiCount} KPIs Live`}
              </span>
            </motion.div>
          )}

          {/* DB Selector */}
          <Select value={selectedDb} onValueChange={onDbChange}>
            <SelectTrigger className="w-48 bg-slate-900/90 border-slate-700/80 text-white text-xs h-9 hover:border-slate-600 transition-colors">
              <SelectValue placeholder="Select Database" />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              <SelectItem value="all">All Connections</SelectItem>
              {databasesList.map((db) => (
                <SelectItem key={db.id} value={db.id.toString()}>
                  {db.name} ({db.db_type})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Date range */}
          <Select value={dateRange} onValueChange={onDateRangeChange}>
            <SelectTrigger className="w-36 bg-slate-900/90 border-slate-700/80 text-white text-xs h-9 hover:border-slate-600 transition-colors">
              <SelectValue placeholder="Date Range" />
            </SelectTrigger>
            <SelectContent className="bg-slate-900 border-slate-700 text-white">
              <SelectItem value="7days">Last 7 days</SelectItem>
              <SelectItem value="30days">Last 30 days</SelectItem>
              <SelectItem value="90days">Last 90 days</SelectItem>
              <SelectItem value="1year">Last year</SelectItem>
            </SelectContent>
          </Select>

          {/* Re-profile button */}
          {selectedDb && selectedDb !== "all" && (
            <Button
              variant="outline"
              size="sm"
              onClick={onTriggerProfile}
              disabled={isProfiling}
              className="gap-2 bg-slate-900/80 border-slate-700 text-slate-200 hover:bg-slate-800 hover:text-white text-xs h-9"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isProfiling ? "animate-spin" : ""}`} />
              {isProfiling ? "Profiling..." : "Re-profile Schema"}
            </Button>
          )}

          {/* Setup Domain wizard trigger */}
          {selectedDb && selectedDb !== "all" && (
            <Button
              size="sm"
              onClick={onOpenWizard}
              className="gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white text-xs h-9 shadow-lg shadow-indigo-600/30 transition-all duration-200 hover:scale-[1.02]"
            >
              <Zap className="w-3.5 h-3.5" />
              Setup Domain
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
