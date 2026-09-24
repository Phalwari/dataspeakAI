/**
 * ChartRenderer — Unified Recharts wrapper for all analytics chart types.
 * Supports: bar | line | area | donut | scatter | horizontal_bar
 * This component is the single source of chart rendering truth for analytics.
 * Backend contract is preserved — no backend files are touched.
 */
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export const CHART_COLORS = [
  "#6366f1", "#8b5cf6", "#06b6d4", "#10b981",
  "#f59e0b", "#ec4899", "#3b82f6", "#f97316",
];

interface ChartRendererProps {
  type: string;
  data: Array<{ name: string; value: number; x?: number; y?: number }>;
  height?: number;
  colors?: string[];
  dark?: boolean;
}

const formatCompact = (val: number) => {
  if (val == null || isNaN(val)) return "0";
  if (Math.abs(val) >= 1_000_000_000) return `${(val / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(val) >= 1_000_000) return `${(val / 1_000_000).toFixed(1)}M`;
  if (Math.abs(val) >= 1_000) return `${(val / 1_000).toFixed(1)}k`;
  return val.toLocaleString();
};

const tooltipStyle = (dark: boolean) => ({
  contentStyle: {
    backgroundColor: dark ? "#0e1526" : "#ffffff",
    border: dark ? "1px solid rgba(255,255,255,0.12)" : "1px solid #e2e8f0",
    borderRadius: "12px",
    color: dark ? "#f8fafc" : "#0f172a",
    boxShadow: "0 12px 36px rgba(0,0,0,0.5)",
    fontSize: "12px",
    padding: "8px 12px",
  },
  labelStyle: {
    fontWeight: 600,
    marginBottom: "4px",
    color: dark ? "#94a3b8" : "#64748b",
  },
});

export function ChartRenderer({
  type,
  data,
  height = 260,
  colors = CHART_COLORS,
  dark = true,
}: ChartRendererProps) {
  const axisColor = dark ? "#64748b" : "#94a3b8";
  const gridColor = dark ? "rgba(255,255,255,0.06)" : "#f1f5f9";

  const normalizedType = type?.toLowerCase().replace("_", "");

  // Common SVG Gradients & Glow defs
  const commonDefs = (
    <defs>
      {/* Primary bar neon gradient (purple/indigo) */}
      <linearGradient id="barNeonGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#818cf8" stopOpacity={1} />
        <stop offset="60%" stopColor="#6366f1" stopOpacity={0.9} />
        <stop offset="100%" stopColor="#4338ca" stopOpacity={0.7} />
      </linearGradient>

      {/* Secondary cyan/blue gradient */}
      <linearGradient id="barCyanGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#22d3ee" stopOpacity={1} />
        <stop offset="60%" stopColor="#06b6d4" stopOpacity={0.9} />
        <stop offset="100%" stopColor="#0891b2" stopOpacity={0.7} />
      </linearGradient>

      {/* Emerald gradient */}
      <linearGradient id="barEmeraldGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#34d399" stopOpacity={1} />
        <stop offset="100%" stopColor="#059669" stopOpacity={0.7} />
      </linearGradient>

      {/* Area chart glowing fill */}
      <linearGradient id="areaNeonGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.45} />
        <stop offset="50%" stopColor="#6366f1" stopOpacity={0.15} />
        <stop offset="100%" stopColor="#6366f1" stopOpacity={0.0} />
      </linearGradient>

      {/* Subtle Glow Filter */}
      <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur" />
        <feComposite in="SourceGraphic" in2="blur" operator="over" />
      </filter>
    </defs>
  );

  if (normalizedType === "donut" || normalizedType === "pie") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          {commonDefs}
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={normalizedType === "donut" ? 48 : 0}
            outerRadius={76}
            paddingAngle={normalizedType === "donut" ? 4 : 0}
            dataKey="value"
            stroke="#0b0f19"
            strokeWidth={3}
          >
            {data.map((_, i) => (
              <Cell key={`cell-${i}`} fill={colors[i % colors.length]} />
            ))}
          </Pie>
          <Tooltip {...tooltipStyle(dark)} formatter={(val: any) => [formatCompact(Number(val)), "Value"]} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (normalizedType === "scatter") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <ScatterChart margin={{ top: 10, right: 15, bottom: 10, left: 0 }}>
          {commonDefs}
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis type="number" dataKey="x" name="X" stroke={axisColor} tick={{ fontSize: 11, fill: axisColor }} />
          <YAxis type="number" dataKey="y" name="Y" stroke={axisColor} tickFormatter={formatCompact} tick={{ fontSize: 11, fill: axisColor }} />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} {...tooltipStyle(dark)} />
          <Scatter
            data={data.map((d, i) => ({ x: d.x ?? i + 1, y: d.y ?? d.value, name: d.name }))}
            fill="#818cf8"
          />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  if (normalizedType === "line") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 10, right: 15, bottom: 10, left: 0 }}>
          {commonDefs}
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="name" stroke={axisColor} tick={{ fontSize: 11, fill: axisColor }} />
          <YAxis stroke={axisColor} tickFormatter={formatCompact} tick={{ fontSize: 11, fill: axisColor }} />
          <Tooltip {...tooltipStyle(dark)} formatter={(val: any) => [formatCompact(Number(val)), "Value"]} />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#38bdf8"
            strokeWidth={3}
            dot={{ fill: "#38bdf8", r: 4, strokeWidth: 2, stroke: "#0f172a" }}
            activeDot={{ r: 6, fill: "#818cf8" }}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (normalizedType === "area" || normalizedType === "stackedarea") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 10, right: 15, bottom: 10, left: 0 }}>
          {commonDefs}
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis dataKey="name" stroke={axisColor} tick={{ fontSize: 11, fill: axisColor }} />
          <YAxis stroke={axisColor} tickFormatter={formatCompact} tick={{ fontSize: 11, fill: axisColor }} />
          <Tooltip {...tooltipStyle(dark)} formatter={(val: any) => [formatCompact(Number(val)), "Value"]} />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#38bdf8"
            strokeWidth={2.5}
            fill="url(#areaNeonGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  if (normalizedType === "horizontalbar") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} layout="vertical" margin={{ top: 10, right: 15, bottom: 10, left: 0 }}>
          {commonDefs}
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} horizontal={false} />
          <XAxis type="number" stroke={axisColor} tickFormatter={formatCompact} tick={{ fontSize: 11, fill: axisColor }} />
          <YAxis type="category" dataKey="name" stroke={axisColor} tick={{ fontSize: 11, fill: axisColor }} width={80} />
          <Tooltip {...tooltipStyle(dark)} formatter={(val: any) => [formatCompact(Number(val)), "Value"]} />
          <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={28}>
            {data.map((_, i) => (
              <Cell key={`hcell-${i}`} fill={colors[i % colors.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // Default: Bar Chart with glowing vertical gradient bars matching mockup
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 12, right: 15, bottom: 12, left: 0 }}>
        {commonDefs}
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis
          dataKey="name"
          stroke={axisColor}
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
          tickLine={{ stroke: "rgba(255,255,255,0.1)" }}
        />
        <YAxis
          stroke={axisColor}
          tickFormatter={formatCompact}
          tick={{ fontSize: 11, fill: "#94a3b8" }}
          axisLine={{ stroke: "rgba(255,255,255,0.1)" }}
          tickLine={{ stroke: "rgba(255,255,255,0.1)" }}
        />
        <Tooltip {...tooltipStyle(dark)} formatter={(val: any) => [formatCompact(Number(val)), "Value"]} />
        <Bar
          dataKey="value"
          radius={[8, 8, 0, 0]}
          maxBarSize={56}
          animationDuration={700}
        >
          {data.map((_, i) => (
            <Cell
              key={`bcell-${i}`}
              fill={i % 2 === 0 ? "url(#barNeonGrad)" : "url(#barCyanGrad)"}
              className="transition-opacity hover:opacity-85"
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
