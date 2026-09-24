/**
 * DomainSetupBanner — Hero CTA shown when no KPIs exist yet.
 * Guides users to open the DomainMappingWizard.
 * Pure frontend — no backend files touched.
 */
import { motion } from "motion/react";
import { Zap, BarChart3, TrendingUp, PieChart } from "lucide-react";

interface DomainSetupBannerProps {
  onSetup: () => void;
}

const FLOAT_ICONS = [
  { icon: BarChart3, x: "10%", delay: 0, color: "text-blue-400" },
  { icon: TrendingUp, x: "70%", delay: 0.3, color: "text-violet-400" },
  { icon: PieChart, x: "85%", delay: 0.6, color: "text-emerald-400" },
];

export function DomainSetupBanner({ onSetup }: DomainSetupBannerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="relative rounded-2xl overflow-hidden border border-indigo-200 shadow-xl"
      style={{ background: "linear-gradient(135deg, #312e81 0%, #1e1b4b 40%, #0f0e2a 100%)" }}
    >
      {/* Floating decorative icons */}
      {FLOAT_ICONS.map(({ icon: Icon, x, delay, color }, i) => (
        <motion.div
          key={i}
          className={`absolute top-4 opacity-20 ${color}`}
          style={{ left: x }}
          animate={{ y: [0, -8, 0] }}
          transition={{ duration: 3, repeat: Infinity, delay, ease: "easeInOut" }}
        >
          <Icon className="w-12 h-12" />
        </motion.div>
      ))}

      {/* Content */}
      <div className="relative z-10 px-8 py-8 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex-1">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/20 mb-4">
            <Zap className="w-3.5 h-3.5 text-yellow-400" />
            <span className="text-[11px] font-semibold text-white/80 tracking-wide uppercase">
              Database Profiled — Ready to Configure
            </span>
          </div>
          <h2 className="text-2xl font-black text-white leading-tight mb-2">
            Set up your AI Business Dashboard
          </h2>
          <p className="text-sm text-indigo-200 max-w-lg">
            Choose your business domain (E-Commerce, SaaS, Healthcare, etc.) and we'll
            auto-generate KPI cards, smart charts, and filters directly from your schema —
            with zero manual SQL.
          </p>
        </div>
        <motion.button
          whileHover={{ scale: 1.04 }}
          whileTap={{ scale: 0.98 }}
          onClick={onSetup}
          className="inline-flex items-center gap-2.5 px-6 py-3 rounded-xl bg-white text-indigo-700 font-bold text-sm shadow-xl hover:bg-indigo-50 transition-colors whitespace-nowrap"
        >
          <Zap className="w-4 h-4 text-indigo-500" />
          Setup Domain Dashboard
        </motion.button>
      </div>
    </motion.div>
  );
}
