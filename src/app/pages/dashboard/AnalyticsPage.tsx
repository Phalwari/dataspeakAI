/**
 * AnalyticsPage — Orchestrator matching mockup layout & dark glass aesthetics.
 * 3-Column Middle Row: Explorer Canvas (left) | AI Synthesized (center) | AI Insights (right).
 * Bottom Row: Schema Health & Data Quality (full width).
 * Full immersive dark background (-m-6) replacing light dashboard container.
 * Zero backend changes.
 */
import { useState, useEffect, useRef } from "react";
import { AnimatePresence } from "motion/react";
import { API_BASE_URL } from "../../config/api";
import { toast } from "sonner";

// Analytics child components
import { AnalyticsHeader, type AnalyticsSourceItem } from "../../components/analytics/AnalyticsHeader";
import { ProfilingProgressBar } from "../../components/analytics/ProfilingProgressBar";
import { SourceArchetypeBanner } from "../../components/analytics/SourceArchetypeBanner";
import { DomainSetupBanner } from "../../components/analytics/DomainSetupBanner";
import { KpiSummaryStrip } from "../../components/analytics/KpiSummaryStrip";
import { LiveExplorerCanvas } from "../../components/analytics/LiveExplorerCanvas";
import { AISynthesizedGrid } from "../../components/analytics/AISynthesizedGrid";
import { AIInsightsSummaryCard } from "../../components/analytics/AIInsightsSummaryCard";
import { SchemaHealthPanel } from "../../components/analytics/SchemaHealthPanel";
import { DomainMappingWizard } from "../../components/analytics/DomainMappingWizard";

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────
const isIdCol = (name: string) => {
  if (!name) return false;
  const lname = name.toLowerCase().trim();
  return (
    lname === "id" ||
    lname === "pk" ||
    lname === "uuid" ||
    lname === "guid" ||
    lname.endsWith("_id") ||
    lname.startsWith("id_") ||
    /[a-zA-Z]id$/i.test(name) ||
    /[a-zA-Z]ID$/.test(name)
  );
};

const parseSource = (s: string) => {
  if (!s || s === "all") return null;
  if (s.startsWith("doc_")) return { type: "document" as const, id: parseInt(s.slice(4), 10) };
  if (s.startsWith("db_")) return { type: "database" as const, id: parseInt(s.slice(3), 10) };
  const num = parseInt(s, 10);
  return isNaN(num) ? null : { type: "database" as const, id: num };
};

// ─────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────
export function AnalyticsPage() {
  // ── Core state ─────────────────────────────────────────────
  const [dateRange, setDateRange] = useState("30days");
  const [databasesList, setDatabasesList] = useState<any[]>([]);
  const [sourcesList, setSourcesList] = useState<AnalyticsSourceItem[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>("all");
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [isProfiling, setIsProfiling] = useState(false);

  const selectedDbRef = useRef(selectedDb);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    selectedDbRef.current = selectedDb;
  }, [selectedDb]);

  // Interactive filter & canvas states
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [selectedMeasure, setSelectedMeasure] = useState<string>("");
  const [selectedDimension, setSelectedDimension] = useState<string>("");
  const [selectedAgg, setSelectedAgg] = useState<string>("SUM");
  const [chartType, setChartType] = useState<string>("Bar");
  const [queryResult, setQueryResult] = useState<any>(null);
  const [queryLoading, setQueryLoading] = useState(false);

  // Wizard state
  const [wizardOpen, setWizardOpen] = useState(false);

  // ── Data fetchers ──────────────────────────────────────────
  const fetchDatabases = async () => {
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token");
      const res = await fetch(`${API_BASE_URL}/api/databases`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDatabasesList(data);
        if (data.length > 0 && selectedDb === "all") {
          setSelectedDb(`db_${data[0].id}`);
        }
      }
    } catch {
      toast.error("Failed to load database connections");
    }
  };

  const fetchSources = async () => {
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token");
      const res = await fetch(`${API_BASE_URL}/api/analytics/sources`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data: AnalyticsSourceItem[] = await res.json();
        setSourcesList(data);

        const dbs = data
          .filter((s) => s.source_type === "database")
          .map((s) => ({ id: s.raw_id || parseInt(s.id.replace("db_", ""), 10), name: s.name, db_type: s.db_type }));
        setDatabasesList(dbs);

        if (data.length > 0 && selectedDb === "all") {
          setSelectedDb(data[0].id);
        }
      } else {
        fetchDatabases();
      }
    } catch {
      fetchDatabases();
    }
  };

  const fetchDashboardData = async (sourceKey: string, range: string) => {
    if (!sourceKey || sourceKey === "all") return;
    const parsed = parseSource(sourceKey);
    if (!parsed) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token");
      const endpoint = `${API_BASE_URL}/api/analytics/sources/${parsed.type}/${parsed.id}/dashboard?date_range=${range}`;
      const res = await fetch(endpoint, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal
      });
      if (res.ok) {
        const data = await res.json();
        if (sourceKey !== selectedDbRef.current) return;
        setDashboardData(data);

        // Auto-select top recommended chart if available
        if (data.recommendations && data.recommendations.length > 0) {
          const topRec = data.recommendations[0];
          if (["Bar", "Line", "Area", "Donut", "Scatter"].includes(topRec.chart_type)) {
            setChartType(topRec.chart_type);
          }
        }

        if (data.schema_summary && data.schema_summary.length > 0) {
          const tables = Array.from(new Set(data.schema_summary.map((s: any) => s.table_name))) as string[];
          const initTable = tables[0];
          setSelectedTable(initTable);

          const tMeasures = data.schema_summary.filter((s: any) => s.table_name === initTable && s.is_measure && !isIdCol(s.column_name));
          const initMeasure = tMeasures.length > 0
            ? tMeasures[0].column_name
            : (data.schema_summary.find((s: any) => s.table_name === initTable && s.is_measure)?.column_name || "Record Count (*)");
          setSelectedMeasure(initMeasure);

          // Auto-select first dimension so chart immediately renders rich distribution
          const tDims = data.schema_summary.filter((s: any) => s.table_name === initTable && s.is_dimension && !isIdCol(s.column_name));
          const fallbackDims = data.schema_summary.filter((s: any) => s.table_name === initTable && !s.is_measure && !isIdCol(s.column_name));
          const initDim = tDims.length > 0 ? tDims[0].column_name : (fallbackDims.length > 0 ? fallbackDims[0].column_name : "");
          setSelectedDimension(initDim);

          const qMeas = initMeasure === "Record Count (*)" ? "*" : initMeasure;
          const qAgg = tMeasures.length > 0 ? "SUM" : "COUNT";
          setSelectedAgg(qAgg);

          runInteractiveQuery(sourceKey, initTable, qMeas, initDim, qAgg);
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        toast.error("Failed to load live dashboard analytics");
      }
    } finally {
      if (sourceKey === selectedDbRef.current) {
        setLoading(false);
      }
    }
  };

  const runInteractiveQuery = async (sourceKey: string, tbl: string, meas: string, dim: string, agg: string) => {
    if (!sourceKey || sourceKey === "all" || !tbl) return;
    const parsed = parseSource(sourceKey);
    if (!parsed) return;

    setQueryLoading(true);
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token");
      const res = await fetch(`${API_BASE_URL}/api/analytics/sources/${parsed.type}/${parsed.id}/query`, {
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
        setQueryResult(await res.json());
      }
    } catch {
      // silent — user can retry via filter change
    } finally {
      setQueryLoading(false);
    }
  };

  const handleTriggerProfile = async () => {
    if (!selectedDb || selectedDb === "all") return;
    const parsed = parseSource(selectedDb);
    if (!parsed) return;

    setIsProfiling(true);
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token");
      if (parsed.type === "document") {
        const res = await fetch(`${API_BASE_URL}/api/analytics/sources/document/${parsed.id}/discover`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setIsProfiling(false);
        if (res.ok) {
          toast.success("Document Source Profile Refreshed!");
          fetchDashboardData(selectedDb, dateRange);
        } else {
          toast.error("Failed to discover document source");
        }
        return;
      }

      const res = await fetch(`${API_BASE_URL}/api/analytics/connections/${parsed.id}/profile`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        toast.info("AI Multi-Agent profiling in progress...");
        let attempts = 0;
        const pollInterval = setInterval(async () => {
          attempts++;
          try {
            const sRes = await fetch(`${API_BASE_URL}/api/analytics/connections/${parsed.id}/profile-status`, {
              headers: { Authorization: `Bearer ${token}` }
            });
            if (sRes.ok) {
              const sData = await sRes.json();
              if (sData.status === "completed" || attempts >= 25) {
                clearInterval(pollInterval);
                setIsProfiling(false);
                toast.success("AI Dashboard Synthesized Successfully!");
                fetchDashboardData(selectedDb, dateRange);
              } else if (sData.status === "failed") {
                clearInterval(pollInterval);
                setIsProfiling(false);
                toast.error(`Profiling failed: ${sData.error || "Unknown error"}`);
              }
            }
          } catch {
            // polling blip
          }
        }, 2000);
      } else {
        setIsProfiling(false);
        toast.error("Could not trigger schema profiling");
      }
    } catch {
      setIsProfiling(false);
      toast.error("Failed to profile source schema");
    }
  };

  const handleSelectReferral = (recChartType: string, recMetric?: string) => {
    if (["Bar", "Line", "Area", "Donut", "Scatter"].includes(recChartType)) {
      setChartType(recChartType);
    }
    if (recMetric && availableMeasures.includes(recMetric)) {
      handleMeasureChange(recMetric);
    }
    toast.info(`Switched to recommended ${recChartType} visualization`);
  };

  // ── Lifecycle ──────────────────────────────────────────────
  useEffect(() => { fetchSources(); }, []);

  useEffect(() => {
    if (selectedDb && selectedDb !== "all") {
      setDashboardData(null);
      setQueryResult(null);
      setSelectedTable("");
      setSelectedMeasure("");
      setSelectedDimension("");
      fetchDashboardData(selectedDb, dateRange);
    }
  }, [selectedDb, dateRange]);

  // ── Derived lists for dropdowns ─────────────────────────────
  const availableTables = dashboardData?.schema_summary
    ? (Array.from(new Set(dashboardData.schema_summary.map((s: any) => s.table_name))) as string[])
    : [];

  const rawMeasures = dashboardData?.schema_summary
    ? dashboardData.schema_summary.filter((s: any) => s.table_name === selectedTable && s.is_measure && !isIdCol(s.column_name))
    : [];
  const measureNames = Array.from(new Set(rawMeasures.map((m: any) => m.column_name))) as string[];
  const availableMeasures = measureNames.length > 0 ? measureNames : ["Record Count (*)"];

  const rawDimensions = dashboardData?.schema_summary
    ? dashboardData.schema_summary.filter((s: any) => s.table_name === selectedTable && s.is_dimension && !isIdCol(s.column_name))
    : [];
  const availableDimensions = Array.from(new Set(rawDimensions.map((d: any) => d.column_name))) as string[];

  // ── Event handlers ──────────────────────────────────────────
  const handleTableChange = (tbl: string) => {
    setSelectedTable(tbl);
    const tRawMeas = dashboardData?.schema_summary
      ? dashboardData.schema_summary.filter((s: any) => s.table_name === tbl && s.is_measure && !isIdCol(s.column_name))
      : [];
    const tMeasNames = Array.from(new Set(tRawMeas.map((m: any) => m.column_name))) as string[];
    const newMeas = tMeasNames.length > 0 ? tMeasNames[0] : "Record Count (*)";
    setSelectedMeasure(newMeas);

    const tRawDims = dashboardData?.schema_summary
      ? dashboardData.schema_summary.filter((s: any) => s.table_name === tbl && s.is_dimension && !isIdCol(s.column_name))
      : [];
    const fallbackDims = dashboardData?.schema_summary
      ? dashboardData.schema_summary.filter((s: any) => s.table_name === tbl && !s.is_measure && !isIdCol(s.column_name))
      : [];
    const tDimNames = Array.from(new Set(tRawDims.map((d: any) => d.column_name))) as string[];
    const fallbackDimNames = Array.from(new Set(fallbackDims.map((d: any) => d.column_name))) as string[];
    const newDim = tDimNames.length > 0 ? tDimNames[0] : (fallbackDimNames.length > 0 ? fallbackDimNames[0] : "");
    setSelectedDimension(newDim);

    const newAgg = tMeasNames.length > 0 ? selectedAgg : "COUNT";
    setSelectedAgg(newAgg);
    runInteractiveQuery(selectedDb, tbl, newMeas === "Record Count (*)" ? "*" : newMeas, newDim, newAgg);
  };

  const handleMeasureChange = (meas: string) => {
    setSelectedMeasure(meas);
    runInteractiveQuery(selectedDb, selectedTable, meas === "Record Count (*)" ? "*" : meas, selectedDimension, selectedAgg);
  };

  const handleDimensionChange = (dim: string) => {
    setSelectedDimension(dim);
    runInteractiveQuery(selectedDb, selectedTable, selectedMeasure === "Record Count (*)" ? "*" : selectedMeasure, dim, selectedAgg);
  };

  const handleAggChange = (agg: string) => {
    setSelectedAgg(agg);
    runInteractiveQuery(selectedDb, selectedTable, selectedMeasure === "Record Count (*)" ? "*" : selectedMeasure, selectedDimension, agg);
  };

  const handleWizardApplied = () => {
    fetchDashboardData(selectedDb, dateRange);
  };

  const noKpis = !dashboardData?.kpis || dashboardData.kpis.length === 0;

  // ── Render matching Mockup ─────────────────────────────────
  return (
    <div className="-m-6 p-6 min-h-[calc(100vh-4rem)] bg-[#090d16] text-slate-100 space-y-5">
      {/* ── 1. Top Header Bar ─────────────────────────────────── */}
      <AnalyticsHeader
        selectedDb={selectedDb}
        dateRange={dateRange}
        databasesList={databasesList}
        sourcesList={sourcesList}
        isProfiling={isProfiling}
        dashboardData={dashboardData}
        onDbChange={setSelectedDb}
        onDateRangeChange={setDateRange}
        onTriggerProfile={handleTriggerProfile}
        onOpenWizard={() => setWizardOpen(true)}
      />

      {/* ── 2. Profiling progress bar ─────────────────────────── */}
      <ProfilingProgressBar isProfiling={isProfiling} />

      {/* ── 2.5 Discovered Source Archetype Banner ───────────── */}
      {selectedDb && selectedDb !== "all" && dashboardData?.discovery && (
        <SourceArchetypeBanner
          discovery={dashboardData.discovery}
          recommendations={dashboardData.recommendations}
          onSelectReferral={handleSelectReferral}
        />
      )}

      {/* ── 3. Domain setup banner (when unmapped) ────────────── */}
      <AnimatePresence>
        {selectedDb && selectedDb !== "all" && dashboardData && noKpis && !loading && (
          <DomainSetupBanner onSetup={() => setWizardOpen(true)} />
        )}
      </AnimatePresence>

      {/* ── 4. Glowing KPI Summary 4-Card Strip ───────────────── */}
      {(queryResult?.kpi_stats || queryLoading) && (
        <KpiSummaryStrip
          stats={queryResult?.kpi_stats ?? null}
          loading={queryLoading && !queryResult}
          selectedMeasure={selectedMeasure}
          selectedTable={selectedTable}
          selectedAgg={selectedAgg}
        />
      )}

      {/* ── 5. Core 3-Column Studio Grid matching Mockup ─────── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-stretch">
        {/* Col 1: Live Explorer Canvas (5 columns) */}
        <div className="xl:col-span-5 flex flex-col">
          <LiveExplorerCanvas
            availableTables={availableTables}
            availableMeasures={availableMeasures}
            availableDimensions={availableDimensions}
            selectedTable={selectedTable}
            selectedMeasure={selectedMeasure}
            selectedDimension={selectedDimension}
            selectedAgg={selectedAgg}
            chartType={chartType}
            queryResult={queryResult}
            queryLoading={queryLoading}
            recommendedChartTypes={dashboardData?.recommendations?.map((r: any) => r.chart_type) || []}
            onTableChange={handleTableChange}
            onMeasureChange={handleMeasureChange}
            onDimensionChange={handleDimensionChange}
            onAggChange={handleAggChange}
            onChartTypeChange={setChartType}
          />
        </div>

        {/* Col 2: AI Synthesized Dashboard (4 columns) */}
        <div className="xl:col-span-4 flex flex-col">
          <AISynthesizedGrid
            dashboardData={dashboardData}
            loading={loading}
            onOpenWizard={() => setWizardOpen(true)}
          />
        </div>

        {/* Col 3: AI Business Insights Card (3 columns) */}
        <div className="xl:col-span-3 flex flex-col">
          <AIInsightsSummaryCard
            connectionId={selectedDb}
            businessDomain={dashboardData?.business_domain}
          />
        </div>
      </div>

      {/* ── 6. Bottom Row: Schema Health & Data Quality ────────── */}
      <SchemaHealthPanel schemaSummary={dashboardData?.schema_summary} />

      {/* ── 7. Guided Domain Mapping Wizard Drawer ────────────── */}
      <AnimatePresence>
        {wizardOpen && (
          <DomainMappingWizard
            open={wizardOpen}
            onClose={() => setWizardOpen(false)}
            connectionId={selectedDb}
            onApplied={handleWizardApplied}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
