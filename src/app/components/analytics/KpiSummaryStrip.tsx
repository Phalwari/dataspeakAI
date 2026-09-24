/**
 * KpiSummaryStrip — Glassmorphic animated 4-KPI stat card row.
 * Reads from kpi_stats returned by POST /api/analytics/dashboard/{id}/query.
 * Uses AnimatedNumber for live counting animation.
 * Pure frontend — no backend files touched.
 */
import { motion } from "motion/react";
import { TrendingUp, Activity, BarChart3, Database, Loader2 } from "lucide-react";
import { AnimatedNumber } from "./AnimatedNumber";

interface KpiStats {
  total: number | null;
  average: number | null;
  max: number | null;
  min: number | null;
  count: number | null;
}

interface KpiSummaryStripProps {
  stats: KpiStats | null;
  loading?: boolean;
  selectedMeasure?: string;
  selectedTable?: string;
  selectedAgg?: string;
}

const CARDS = [
  {
    key: "total" as keyof KpiStats,
    label: "TOTAL SUM",
    icon: TrendingUp,
    color: "blue",
    border: "border-blue-500/50 hover:border-blue-400",
    glow: "shadow-[0_0_24px_rgba(59,130,246,0.18),inset_0_1px_0_rgba(255,255,255,0.08)]",
    iconBg: "bg-blue-500/15 border border-blue-500/35",
    iconColor: "text-blue-400",
    trend: "+12.4% ↑",
    trendColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  },
  {
    key: "average" as keyof KpiStats,
    label: "AVERAGE VALUE",
    icon: Activity,
    color: "emerald",
    border: "border-emerald-500/50 hover:border-emerald-400",
    glow: "shadow-[0_0_24px_rgba(16,185,129,0.18),inset_0_1px_0_rgba(255,255,255,0.08)]",
    iconBg: "bg-emerald-500/15 border border-emerald-500/35",
    iconColor: "text-emerald-400",
    trend: "+5.2% ↑",
    trendColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  },
  {
    key: "max" as keyof KpiStats,
    label: "PEAK MAXIMUM",
    icon: BarChart3,
    color: "violet",
    border: "border-purple-500/50 hover:border-purple-400",
    glow: "shadow-[0_0_24px_rgba(168,85,247,0.18),inset_0_1px_0_rgba(255,255,255,0.08)]",
    iconBg: "bg-purple-500/15 border border-purple-500/35",
    iconColor: "text-purple-400",
    trend: "-2.1% ↓",
    trendColor: "text-rose-400 bg-rose-500/10 border-rose-500/30",
  },
  {
    key: "count" as keyof KpiStats,
    label: "SAMPLE COUNT",
    icon: Database,
    color: "amber",
    border: "border-amber-500/50 hover:border-amber-400",
    glow: "shadow-[0_0_24px_rgba(245,158,11,0.18),inset_0_1px_0_rgba(255,255,255,0.08)]",
    iconBg: "bg-amber-500/15 border border-amber-500/35",
    iconColor: "text-amber-400",
    trend: "+8.7% ↑",
    trendColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
  },
];

function MiniSparkline({ color }: { color: string }) {
  const points = [4, 7, 5, 11, 8, 14, 10, 18, 13, 20];
  const max = Math.max(...points);
  const w = 70;
  const h = 24;
  const pts = points
    .map((v, i) => `${(i / (points.length - 1)) * w},${h - (v / max) * h}`)
    .join(" ");
  const colorMap: Record<string, string> = {
    blue: "#38bdf8",
    emerald: "#34d399",
    violet: "#c084fc",
    amber: "#fbbf24",
  };
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="overflow-visible">
      <polyline
        points={pts}
        fill="none"
        stroke={colorMap[color]}
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="drop-shadow(0 0 4px currentColor)"
      />
    </svg>
  );
}

const isCurrencyMeasure = (meas?: string) => {
  if (!meas) return false;
  const m = meas.toLowerCase();
  return m.includes("revenue") || m.includes("amount") || m.includes("cost") || m.includes("price") || m.includes("sales") || m.includes("profit");
};

export function KpiSummaryStrip({
  stats,
  loading,
  selectedMeasure,
  selectedTable,
}: KpiSummaryStripProps) {
  const isCurrency = isCurrencyMeasure(selectedMeasure);

  return (
    <motion.div
      className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.08 } },
      }}
    >
      {CARDS.map((card) => {
        const Icon = card.icon;
        const val = stats ? stats[card.key] : null;
        const showCurrencyPrefix = isCurrency && card.key !== "count";

        return (
          <motion.div
            key={card.key}
            variants={{
              hidden: { opacity: 0, y: 18 },
              visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
            }}
            whileHover={{ scale: 1.015, y: -2, transition: { duration: 0.15 } }}
            className={`relative rounded-2xl bg-[#0e1526]/90 backdrop-blur-xl border ${card.border} p-4 shadow-xl ${card.glow} cursor-default overflow-hidden flex flex-col justify-between transition-all`}
          >
            {/* Top row: Icon container + Sparkline */}
            <div className="flex items-center justify-between mb-3">
              <div className={`w-11 h-11 rounded-xl ${card.iconBg} flex items-center justify-center shadow-inner`}>
                <Icon className={`w-5 h-5 ${card.iconColor}`} />
              </div>
              <MiniSparkline color={card.color} />
            </div>

            {/* Middle: Label */}
            <div className="mb-1">
              <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                {card.label}
              </p>
            </div>

            {/* Bottom: Big number & trend badge */}
            <div className="flex items-baseline justify-between gap-2 mt-auto">
              {loading ? (
                <Loader2 className="w-6 h-6 animate-spin text-slate-400 my-1" />
              ) : (
                <p className="text-2xl xl:text-3xl font-black text-white tabular-nums tracking-tight leading-none">
                  {showCurrencyPrefix && <span className="text-lg font-bold text-slate-400 mr-1">Rs</span>}
                  <AnimatedNumber value={val != null ? val : "—"} />
                </p>
              )}

              <span className={`inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded-full border ${card.trendColor}`}>
                {card.trend}
              </span>
            </div>

            {/* Sub-label */}
            {selectedTable && selectedMeasure && (
              <p className="text-[10px] text-slate-500 mt-2 truncate font-mono">
                {selectedTable}.{selectedMeasure}
              </p>
            )}
          </motion.div>
        );
      })}
    </motion.div>
  );
}
