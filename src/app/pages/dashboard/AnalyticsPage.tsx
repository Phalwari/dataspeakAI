import { useState, useEffect } from "react";
import { API_BASE_URL } from "../../config/api";
import { toast } from "sonner";
import {
  BarChart3,
  TrendingUp,
  Database,
  Activity,
  Calendar,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { AnimatedNumber } from "../../components/analytics/AnimatedNumber";
import { ProfilingProgressBar } from "../../components/analytics/ProfilingProgressBar";

const queryTrendsData = [
  { name: "Jan", queries: 4000 },
  { name: "Feb", queries: 3000 },
  { name: "Mar", queries: 5000 },
  { name: "Apr", queries: 4500 },
  { name: "May", queries: 6000 },
  { name: "Jun", queries: 5500 },
  { name: "Jul", queries: 7000 },
];

const topTablesData = [
  { name: "Orders", count: 12450 },
  { name: "Customers", count: 8900 },
  { name: "Products", count: 6700 },
  { name: "Invoices", count: 5200 },
  { name: "Payments", count: 4100 },
];

const databaseDistribution = [
  { name: "PostgreSQL", value: 45 },
  { name: "MongoDB", value: 30 },
  { name: "MySQL", value: 15 },
  { name: "SQLite", value: 10 },
];

const dataGrowthData = [
  { name: "Week 1", records: 10000 },
  { name: "Week 2", records: 12500 },
  { name: "Week 3", records: 15200 },
  { name: "Week 4", records: 18900 },
  { name: "Week 5", records: 22400 },
  { name: "Week 6", records: 26100 },
];

const COLORS = ["#3b82f6", "#8b5cf6", "#06b6d4", "#10b981"];


export function AnalyticsPage() {
  const [dateRange, setDateRange] = useState("30days");
  const [databasesList, setDatabasesList] = useState<any[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>("all");
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isProfiling, setIsProfiling] = useState(false);

  // Interactive filter & canvas states
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [selectedMeasure, setSelectedMeasure] = useState<string>("");
  const [selectedDimension, setSelectedDimension] = useState<string>("");
  const [selectedAgg, setSelectedAgg] = useState<string>("SUM");
  const [chartType, setChartType] = useState<string>("Bar");
  const [queryResult, setQueryResult] = useState<any>(null);
  const [queryLoading, setQueryLoading] = useState(false);

  // Fetch list of user's registered database connections
  const fetchDatabases = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/databases`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDatabasesList(data);
        if (data.length > 0 && selectedDb === "all") {
          setSelectedDb(data[0].id.toString());
        }
      }
    } catch (err) {
      toast.error("Failed to load database connections");
    }
  };

  // Fetch live dashboard analytics data for selected DB
  const fetchDashboardData = async (dbId: string, range: string) => {
    if (!dbId || dbId === "all") return;
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/analytics/dashboard/${dbId}?date_range=${range}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDashboardData(data);
        
        // Auto-select initial table, measure, dimension from schema
        if (data.schema_summary && data.schema_summary.length > 0) {
          const tables = Array.from(new Set(data.schema_summary.map((s: any) => s.table_name))) as string[];
          const initTable = tables[0];
          setSelectedTable(initTable);

          const tMeasures = data.schema_summary.filter((s: any) => s.table_name === initTable && s.is_measure && !s.column_name.toLowerCase().endsWith("id") && s.column_name.toLowerCase() !== "id");
          const initMeasure = tMeasures.length > 0 ? tMeasures[0].column_name : (data.schema_summary.find((s: any) => s.table_name === initTable && s.is_measure)?.column_name || "Record Count (*)");
          setSelectedMeasure(initMeasure);

          const tDims = data.schema_summary.filter((s: any) => s.table_name === initTable && s.is_dimension);
          const initDim = tDims.length > 0 ? tDims[0].column_name : "";
          setSelectedDimension(initDim);

          const qMeas = initMeasure === "Record Count (*)" ? "*" : initMeasure;
          const qAgg = tMeasures.length > 0 ? "SUM" : "COUNT";
          setSelectedAgg(qAgg);

          // Run initial interactive query
          runInteractiveQuery(dbId, initTable, qMeas, initDim, qAgg);
        }
      }
    } catch (err) {
      toast.error("Failed to load live dashboard analytics");
    } finally {
      setLoading(false);
    }
  };

  // Run dynamic interactive query against backend
  const runInteractiveQuery = async (
    dbId: string, 
    tbl: string, 
    meas: string, 
    dim: string, 
    agg: string
  ) => {
    if (!dbId || dbId === "all" || !tbl) return;
    setQueryLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/analytics/dashboard/${dbId}/query`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify({
          table_name: tbl,
          target_column: meas,
          dimension_column: dim || null,
          aggregation: agg,
          limit: 10
        })
      });
      if (res.ok) {
        const data = await res.json();
        setQueryResult(data);
      }
    } catch (err) {
      console.error("Interactive query error:", err);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleTriggerProfile = async () => {
    if (!selectedDb || selectedDb === "all") return;
    setIsProfiling(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/analytics/connections/${selectedDb}/profile`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        toast.success("Triggered schema profiling for selected database!");
        setTimeout(() => {
          setIsProfiling(false);
          fetchDashboardData(selectedDb, dateRange);
        }, 3600);
      } else {
        setIsProfiling(false);
      }
    } catch (err) {
      setIsProfiling(false);
      toast.error("Failed to profile database schema");
    }
  };

  useEffect(() => {
    fetchDatabases();
  }, []);

  useEffect(() => {
    if (selectedDb && selectedDb !== "all") {
      fetchDashboardData(selectedDb, dateRange);
    }
  }, [selectedDb, dateRange]);

  // Derived lists for dropdowns
  const availableTables = dashboardData?.schema_summary 
    ? (Array.from(new Set(dashboardData.schema_summary.map((s: any) => s.table_name))) as string[])
    : [];

  const rawMeasures = dashboardData?.schema_summary
    ? dashboardData.schema_summary.filter((s: any) => s.table_name === selectedTable && s.is_measure && !s.column_name.toLowerCase().endsWith("id") && s.column_name.toLowerCase() !== "id")
    : [];

  const measureNames = Array.from(new Set(rawMeasures.map((m: any) => m.column_name))) as string[];
  const availableMeasures = measureNames.length > 0 
    ? measureNames 
    : ["Record Count (*)"];

  const rawDimensions = dashboardData?.schema_summary
    ? dashboardData.schema_summary.filter((s: any) => s.table_name === selectedTable && s.is_dimension)
    : [];

  const availableDimensions = Array.from(new Set(rawDimensions.map((d: any) => d.column_name))) as string[];

  const handleTableChange = (tbl: string) => {
    setSelectedTable(tbl);
    const tRawMeas = dashboardData?.schema_summary 
      ? dashboardData.schema_summary.filter((s: any) => s.table_name === tbl && s.is_measure && !s.column_name.toLowerCase().endsWith("id") && s.column_name.toLowerCase() !== "id")
      : [];
    const tMeasNames = Array.from(new Set(tRawMeas.map((m: any) => m.column_name))) as string[];

    const newMeas = tMeasNames.length > 0 ? tMeasNames[0] : "Record Count (*)";
    setSelectedMeasure(newMeas);

    const tRawDims = dashboardData?.schema_summary
      ? dashboardData.schema_summary.filter((s: any) => s.table_name === tbl && s.is_dimension)
      : [];
    const tDimNames = Array.from(new Set(tRawDims.map((d: any) => d.column_name))) as string[];
    const newDim = tDimNames.length > 0 ? tDimNames[0] : "";
    setSelectedDimension(newDim);

    const newAgg = tMeasNames.length > 0 ? selectedAgg : "COUNT";
    setSelectedAgg(newAgg);

    const queryMeas = newMeas === "Record Count (*)" ? "*" : newMeas;
    runInteractiveQuery(selectedDb, tbl, queryMeas, newDim, newAgg);
  };

  const handleMeasureChange = (meas: string) => {
    setSelectedMeasure(meas);
    const queryMeas = meas === "Record Count (*)" ? "*" : meas;
    runInteractiveQuery(selectedDb, selectedTable, queryMeas, selectedDimension, selectedAgg);
  };

  const handleDimensionChange = (dim: string) => {
    setSelectedDimension(dim);
    const queryMeas = selectedMeasure === "Record Count (*)" ? "*" : selectedMeasure;
    runInteractiveQuery(selectedDb, selectedTable, queryMeas, dim, selectedAgg);
  };

  const handleAggChange = (agg: string) => {
    setSelectedAgg(agg);
    const queryMeas = selectedMeasure === "Record Count (*)" ? "*" : selectedMeasure;
    runInteractiveQuery(selectedDb, selectedTable, queryMeas, selectedDimension, agg);
  };


  const stats = queryResult?.kpi_stats || { total: 0, average: 0, max: 0, count: 0 };

  return (
    <div className="space-y-6">
      {/* Top Title & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Analytics & Visualization</h1>
          <p className="text-gray-600 mt-1">
            Monitor your live data trends, schema profiles, and query patterns
          </p>
        </div>
        <div className="flex items-center gap-3">
          {selectedDb !== "all" && (
            <Button variant="outline" size="sm" onClick={handleTriggerProfile} disabled={isProfiling} className="gap-2">
              <RefreshCw className={`w-4 h-4 ${isProfiling ? "animate-spin" : ""}`} />
              {isProfiling ? "Profiling..." : "Re-profile Schema"}
            </Button>
          )}
          <Select value={selectedDb} onValueChange={setSelectedDb}>
            <SelectTrigger className="w-48 font-medium">
              <SelectValue placeholder="Select Database" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Connections</SelectItem>
              {databasesList.map((db) => (
                <SelectItem key={db.id} value={db.id.toString()}>
                  {db.name} ({db.db_type})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={dateRange} onValueChange={setDateRange}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Date Range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7days">Last 7 days</SelectItem>
              <SelectItem value="30days">Last 30 days</SelectItem>
              <SelectItem value="90days">Last 90 days</SelectItem>
              <SelectItem value="1year">Last year</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Multi-step Profiling Progress Bar */}
      <ProfilingProgressBar isProfiling={isProfiling} />

      {/* Dynamic Filter Controls Bar */}
      {selectedDb !== "all" && availableTables.length > 0 && (
        <Card className="bg-gradient-to-r from-slate-900 to-slate-800 text-white border-none shadow-md">
          <CardContent className="p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Table</label>
                <Select value={selectedTable} onValueChange={handleTableChange}>
                  <SelectTrigger className="w-40 bg-slate-800 border-slate-700 text-white h-9">
                    <SelectValue placeholder="Select Table" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableTables.map((t) => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Target Metric</label>
                <Select value={selectedMeasure} onValueChange={handleMeasureChange}>
                  <SelectTrigger className="w-44 bg-slate-800 border-slate-700 text-white h-9">
                    <SelectValue placeholder="Select Metric" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableMeasures.map((m: string) => (
                      <SelectItem key={m} value={m}>{m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Group By Dimension</label>
                <Select value={selectedDimension} onValueChange={handleDimensionChange}>
                  <SelectTrigger className="w-44 bg-slate-800 border-slate-700 text-white h-9">
                    <SelectValue placeholder="Select Dimension" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableDimensions.map((d: string) => (
                      <SelectItem key={d} value={d}>{d}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Aggregation</label>
                <Select value={selectedAgg} onValueChange={handleAggChange}>
                  <SelectTrigger className="w-28 bg-slate-800 border-slate-700 text-white h-9">
                    <SelectValue placeholder="Agg" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="SUM">SUM</SelectItem>
                    <SelectItem value="AVG">AVG</SelectItem>
                    <SelectItem value="COUNT">COUNT</SelectItem>
                    <SelectItem value="MAX">MAX</SelectItem>
                    <SelectItem value="MIN">MIN</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Chart View</label>
              <div className="flex items-center bg-slate-800 p-1 rounded-md border border-slate-700 gap-1">
                <Button variant={chartType === "Bar" ? "secondary" : "ghost"} size="sm" onClick={() => setChartType("Bar")} className="h-7 px-2 text-xs">Bar</Button>
                <Button variant={chartType === "Line" ? "secondary" : "ghost"} size="sm" onClick={() => setChartType("Line")} className="h-7 px-2 text-xs">Line</Button>
                <Button variant={chartType === "Area" ? "secondary" : "ghost"} size="sm" onClick={() => setChartType("Area")} className="h-7 px-2 text-xs">Area</Button>
                <Button variant={chartType === "Donut" ? "secondary" : "ghost"} size="sm" onClick={() => setChartType("Donut")} className="h-7 px-2 text-xs">Donut</Button>
                <Button variant={chartType === "Scatter" ? "secondary" : "ghost"} size="sm" onClick={() => setChartType("Scatter")} className="h-7 px-2 text-xs">Scatter</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Live Calculated KPI Cards for Selected Filter */}
      <div className="grid md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Total {selectedMeasure || "Sum"}</p>
                <p className="text-2xl font-bold mt-1 text-slate-900">
                  <AnimatedNumber value={stats.total ? stats.total : 0} />
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">Sum of {selectedTable}.{selectedMeasure}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Average Value</p>
                <p className="text-2xl font-bold mt-1 text-slate-900">
                  <AnimatedNumber value={stats.average ? stats.average : 0} />
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                <Activity className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">Mean per record</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Peak Maximum</p>
                <p className="text-2xl font-bold mt-1 text-slate-900">
                  <AnimatedNumber value={stats.max ? stats.max : 0} />
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">Highest single record</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Total Records</p>
                <p className="text-2xl font-bold mt-1 text-slate-900">
                  <AnimatedNumber value={stats.count ? stats.count : 0} />
                </p>
              </div>
              <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center">
                <Database className="w-5 h-5 text-amber-600" />
              </div>
            </div>
            <p className="text-xs text-gray-500 mt-2">Rows in {selectedTable || "table"}</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Interactive Explorer Canvas */}
      {queryResult && (
        <Card className="border shadow-sm">
          <CardHeader className="border-b bg-gray-50/50 py-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-600" />
                Live Explorer: {selectedAgg}({selectedMeasure}) by {selectedDimension || "Row"} in {selectedTable}
              </CardTitle>
              <div className="text-xs px-2.5 py-1 bg-slate-100 text-slate-700 font-mono rounded border">
                SQL: SELECT {selectedDimension ? `"${selectedDimension}", ` : ""}{selectedAgg}("{selectedMeasure}") FROM "{selectedTable}"
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            {queryLoading ? (
              <div className="flex justify-center p-12">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={360}>
                {chartType === "Line" ? (
                  <LineChart data={queryResult.chart_data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                    <Legend />
                    <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={{ fill: "#3b82f6", r: 5 }} />
                  </LineChart>
                ) : chartType === "Area" ? (
                  <AreaChart data={queryResult.chart_data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                    <Area type="monotone" dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
                  </AreaChart>
                ) : chartType === "Donut" ? (
                  <PieChart>
                    <Pie data={queryResult.chart_data || []} cx="50%" cy="50%" innerRadius={60} outerRadius={110} fill="#8884d8" dataKey="value" label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}>
                      {(queryResult.chart_data || []).map((entry: any, i: number) => (
                        <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                  </PieChart>
                ) : chartType === "Scatter" ? (
                  <ScatterChart>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis type="number" dataKey="x" name="Measure X" stroke="#6b7280" />
                    <YAxis type="number" dataKey="y" name="Measure Y" stroke="#6b7280" />
                    <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                    <Scatter name="Measure Correlation" data={queryResult.scatter_data && queryResult.scatter_data.length > 0 ? queryResult.scatter_data : (queryResult.chart_data || []).map((d: any, i: number) => ({ x: i + 1, y: d.value, name: d.name }))} fill="#ec4899" />
                  </ScatterChart>
                ) : (
                  <BarChart data={queryResult.chart_data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                    <Bar dataKey="value" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      )}


      {/* Dynamic Table-Specific Breakdown Charts */}
      <div>
        <h2 className="text-xl font-bold mb-3 flex items-center justify-between">
          <span className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-600" />
            {selectedTable ? `${selectedTable} Table Analytics Overview` : "Auto-Generated Schema Overview Charts"}
          </span>
          <span className="text-xs font-normal text-slate-500">
            Dynamically filtered for <strong className="text-slate-900">{selectedTable || "All Tables"}</strong>
          </span>
        </h2>

        {loading ? (
          <div className="flex justify-center p-12">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        ) : queryResult ? (
          <div className="grid md:grid-cols-2 gap-6">
            {/* 1. Bar Chart Breakdown */}
            <Card>
              <CardHeader className="py-4">
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span>{selectedTable}: {selectedAgg}({selectedMeasure || "Records"}) by {selectedDimension || "Row"}</span>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-blue-50 text-blue-600 border border-blue-100">
                    Bar View
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={queryResult.chart_data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                    <Bar dataKey="value" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* 2. Donut Proportional Breakdown */}
            <Card>
              <CardHeader className="py-4">
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span>{selectedTable}: Distribution Share by {selectedDimension || "Category"}</span>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-purple-50 text-purple-600 border border-purple-100">
                    Donut View
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie data={queryResult.chart_data || []} cx="50%" cy="50%" innerRadius={45} outerRadius={80} fill="#8884d8" dataKey="value" label={({ name, percent }) => `${name.substring(0, 8)}: ${(percent * 100).toFixed(0)}%`}>
                      {(queryResult.chart_data || []).map((entry: any, i: number) => (
                        <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* 3. Line Sequential Trend */}
            <Card>
              <CardHeader className="py-4">
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span>{selectedTable}: Sequential Metric Trend</span>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-green-50 text-green-600 border border-green-100">
                    Line Trend
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={queryResult.chart_data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                    <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} dot={{ fill: "#3b82f6", r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* 4. Area Cumulative Density */}
            <Card>
              <CardHeader className="py-4">
                <CardTitle className="text-sm font-semibold flex items-center justify-between">
                  <span>{selectedTable}: Cumulative Metric Volume</span>
                  <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-100">
                    Area Density
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4">
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={queryResult.chart_data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip contentStyle={{ backgroundColor: "white", borderRadius: "8px" }} />
                    <Area type="monotone" dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.3} />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        ) : null}
      </div>

    </div>
  );
}



