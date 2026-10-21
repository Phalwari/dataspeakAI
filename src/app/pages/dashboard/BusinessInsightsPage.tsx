import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router';
import { toast } from 'sonner';
import html2canvas from 'html2canvas';
// local auth
// local theme
import {
  Sparkles, RefreshCw, Download, AlertTriangle, AlertCircle, CheckCircle2, Lightbulb,
  TrendingUp, TrendingDown, Minus, MessageSquare, X, Database, Clock, ArrowLeft,
  Table as TableIcon, Activity, Cpu, Compass, ShieldCheck, Check, Loader2,
  Server, Plus, Search, Layers, ChevronDown, ChevronUp, Zap, Trash2, Filter
} from 'lucide-react';
import {
  BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, Legend, CartesianGrid, ResponsiveContainer
} from 'recharts';
import { API_BASE_URL } from '../../config/api';
import { databaseConnectionsAPI } from '../../api/connections';
const API_URL = `${API_BASE_URL}/api`;

// Curated vibrant enterprise chart palette
const PALETTE = ['#6c47ff', '#00c2cb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6', '#ec4899'];
const KPI_ACCENTS = ['#6c47ff', '#00c2cb', '#10b981', '#f59e0b', '#8b5cf6', '#3b82f6'];
const KPI_REASON_LABELS: Record<string, string> = {
  missing_role: 'Required column missing',
  missing_table: 'Source table unavailable',
  query_failed: 'Database query failed',
  no_rows: 'No rows found',
  date_filter_unavailable: 'Date-filtered value unavailable',
  unsupported_with_filter: 'This metric cannot use the selected dates',
};
const IMPACT_COLORS = { High: '#dc2626', Medium: '#d97706', Low: '#059669' };
const PRESETS: [string, string, number | null][] = [
  ['all', 'All time', null],
  ['90d', 'Last 90 days', 90],
  ['30d', 'Last 30 days', 30],
  ['7d', 'Last 7 days', 7]
];

// The progress view explains the safeguards behind the insight report in
// business-friendly language.
const INSIGHT_RUN_STAGES = [
  { phase: 'A', icon: ShieldCheck, title: 'Secure analysis context', description: 'Scope the request to the selected connection and tenant cache.', detail: 'Access & cache safety' },
  { phase: 'B', icon: Database, title: 'Discover the data catalog', description: 'Review supported tables, columns and declared relationships.', detail: 'Schema discovery' },
  { phase: 'C', icon: Cpu, title: 'Classify data roles', description: 'Identify dates, identifiers, measures and excluded sensitive fields.', detail: 'Evidence-based roles' },
  { phase: 'D', icon: Compass, title: 'Plan safe metrics', description: 'Prepare date-aware, dialect-aware read-only calculations.', detail: 'Filters & query plan' },
  { phase: 'E', icon: Activity, title: 'Execute and validate', description: 'Run bounded aggregates and separate zero, unavailable and error states.', detail: 'Data quality checks' },
  { phase: 'F', icon: Sparkles, title: 'Prepare decision-ready insights', description: 'Assemble charts, quality notes and an AI or deterministic summary.', detail: 'Report & fallback' }
];

// Smooth count hook for KPI numbers
function useCount(value: any) {
  const [out, setOut] = useState(String(value ?? '—'));
  useEffect(() => {
    const str = String(value ?? '—');
    const m = str.match(/^([^\d-]*)(-?[\d,]*\.?\d+)(.*)$/);
    if (!m) { setOut(str); return undefined; }
    const [, pre, num, suf] = m;
    const end = parseFloat(num.replace(/,/g, ''));
    if (isNaN(end)) { setOut(str); return undefined; }
    const dec = (num.split('.')[1] || '').length;
    let raf: any;
    const t0 = performance.now();
    const tick = (t: number) => {
      const p = Math.min((t - t0) / 500, 1);
      setOut(p >= 1 ? str : `${pre}${(end * p).toLocaleString(undefined, { maximumFractionDigits: dec, minimumFractionDigits: dec })}${suf}`);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return out;
}
const AnimatedCount = ({ value }: { value: any }) => <>{useCount(value)}</>;

const CustomChartTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '10px',
        padding: '10px 14px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.08)',
        fontSize: '12px',
        color: '#0f172a'
      }}>
        <div style={{ color: '#64748b', fontWeight: 600, marginBottom: '4px' }}>
          {label}
        </div>
        {payload.map((p: any, i: number) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, color: p.color || '#6c47ff' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: p.color || '#6c47ff' }} />
            <span>{p.name || 'Value'}: {typeof p.value === 'number' ? (p.value >= 1000 ? p.value.toLocaleString() : p.value.toFixed(2)) : p.value}</span>
          </div>
        ))}
        <div style={{ marginTop: '6px', fontSize: '10.5px', color: '#94a3b8', borderTop: '1px solid #f1f5f9', paddingTop: '4px' }}>
          💡 Click point to inspect underlying records
        </div>
      </div>
    );
  }
  return null;
};

export function BusinessInsightsPage() {
  // Business Insights Dashboard (White / Light Mode active)
  const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
  const darkMode = false;
  const navigate = useNavigate();
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  // Connection & schema states
  const [connections, setConnections] = useState<any[]>([]);
  const [selectedConnection, setSelectedConnection] = useState<string>('');
  const [availableTables, setAvailableTables] = useState<any[]>([]);
  const [activeTable, setActiveTable] = useState<string>(''); // '' means all tables
  const [fetchingConnections, setFetchingConnections] = useState(true);
  const [retestingId, setRetestingId] = useState<string | number | null>(null);

  // Workflow & Pipeline states
  const [loading, setLoading] = useState(false);
  const [autoGenerateStep, setAutoGenerateStep] = useState<string | null>(null); // 'analyzing' | null
  const [agAnalysisStep, setAgAnalysisStep] = useState(0);
  const [pipelineData, setPipelineData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Calendar date presets ('all', '90d', '30d', '7d')
  const [preset, setPreset] = useState('all');
  const [selectedDimensionFilter, setSelectedDimensionFilter] = useState<{ column: string; label: string; value: string } | null>(null);

  // Interactive Features
  const [expandedKpi, setExpandedKpi] = useState<any>(null);
  const [activeTopPerformerCategory, setActiveTopPerformerCategory] = useState(0);
  const [drilldown, setDrilldown] = useState<any>(null);
  const [drillSearch, setDrillSearch] = useState('');
  const [exporting, setExporting] = useState(false);

  // Clean DB location formatter
  const formatDbLocation = (conn: any) => {
    if (!conn) return 'Instance';
    if (conn.db_type === 'sqlite') {
      const raw = conn.database || conn.host || '';
      const parts = raw.split(/[/\\]/);
      return `Local SQLite · ${parts[parts.length - 1] || 'chinook.db'}`;
    }
    if (conn.host) {
      return `${conn.host}${conn.port ? `:${conn.port}` : ''} · DB: ${conn.database || 'main'}`;
    }
    return conn.database || 'Cloud Database';
  };

  const getDbColor = (dbType: any) => {
    const t = String(dbType || '').toLowerCase();
    if (t.includes('sqlite')) return '#00c2cb';
    if (t.includes('postgres')) return '#8b5cf6';
    if (t.includes('mysql')) return '#3b82f6';
    if (t.includes('mongo')) return '#10b981';
    return '#6c47ff';
  };

  // Reusable connection fetcher
  const fetchConnectionsList = useCallback(async () => {
    setFetchingConnections(true);
    try {
      const j = await databaseConnectionsAPI.listConnections();
      const list = j.connections || [];
      setConnections(list);
      if (list.length > 0 && !selectedConnection) {
        setSelectedConnection(list[0].id);
      }
    } catch (e: any) {
      setError(e.message || 'Could not load connections.');
    } finally {
      setFetchingConnections(false);
    }
  }, [selectedConnection]);

  // Retest connection action
  const handleRetestConnection = async (e: React.MouseEvent, connId: string | number) => {
    e.stopPropagation();
    setRetestingId(connId);
    try {
      const res = await databaseConnectionsAPI.retestConnection(connId);
      if (res.success) {
        toast.success(res.message || 'Connection retested successfully!');
        fetchConnectionsList();
      } else {
        toast.error(res.message || 'Retest failed.');
      }
    } catch (err: any) {
      toast.error('Retest network failure.');
    } finally {
      setRetestingId(null);
    }
  };

  // Delete connection action
  const handleDeleteConnection = async (e: React.MouseEvent, connId: string | number, connName: string) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to remove database connection "${connName}"?`)) {
      return;
    }
    try {
      await databaseConnectionsAPI.deleteConnection(connId);
      toast.success(`Removed connection "${connName}"`);
      if (selectedConnection === connId) {
        setSelectedConnection('');
        setAvailableTables([]);
      }
      fetchConnectionsList();
    } catch (err: any) {
      toast.error('Failed to delete connection.');
    }
  };

  // Fetch connections on mount
  useEffect(() => {
    fetchConnectionsList();
  }, [fetchConnectionsList]);

  // Fetch tables when connection changes
  useEffect(() => {
    if (!selectedConnection) {
      setAvailableTables([]);
      return;
    }
    const conn = connections.find((c) => c.id === selectedConnection);
    if (conn?.tables_metadata) {
      try {
        const meta = typeof conn.tables_metadata === 'string' ? JSON.parse(conn.tables_metadata) : conn.tables_metadata;
        const tbls = Object.keys(meta || {});
        if (tbls.length > 0) {
          setAvailableTables(tbls);
          return;
        }
      } catch (e) {
        // ignore
      }
    }
    // Fallback tables fetch
    fetch(`${API_URL}/connections/${selectedConnection}/tables`, {
      method: 'POST',
      headers
    })
      .then((r) => r.ok && r.json())
      .then((tbls) => {
        if (Array.isArray(tbls)) setAvailableTables(tbls);
      })
      .catch(() => {});
  }, [selectedConnection, connections, headers]);

  // Insight-run progress animation (only on explicit Run or Refresh).
  const triggerAnalysisAnimation = useCallback((onFinish?: () => void) => {
    setAutoGenerateStep('analyzing');
    setAgAnalysisStep(0);
    const interval = setInterval(() => {
      setAgAnalysisStep((prev) => {
        if (prev >= INSIGHT_RUN_STAGES.length - 1) {
          clearInterval(interval);
          setTimeout(() => {
            if (onFinish) onFinish();
          }, 350);
          return 6;
        }
        return prev + 1;
      });
    }, 550);
    return interval;
  }, []);

  const dateRangeForPreset = (presetChoice: string) => {
    const days = PRESETS.find(([id]) => id === presetChoice)?.[2];
    if (!days) return null;
    const today = new Date();
    const start = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    start.setDate(start.getDate() - days + 1);
    const formatLocalDate = (value: Date) =>
      `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
    return { from: formatLocalDate(start), to: formatLocalDate(today) };
  };

  // The API computes every metric and chart for the same calendar window.
  const runDatabaseAnalysis = async (
    connId = selectedConnection, tableChoice = activeTable,
    forceRefresh = false, requestedPreset = preset,
  ) => {
    if (!connId) return;
    setLoading(true);
    setError(null);

    let animationDone = false;
    let pipelineDone = false;
    let fetchedData: any = null;

    const animInterval = triggerAnalysisAnimation(() => {
      animationDone = true;
      if (pipelineDone && fetchedData) {
        setPipelineData(fetchedData);
        setPreset(requestedPreset);
        setActiveTable(tableChoice);
        setAutoGenerateStep(null);
        setLoading(false);
      }
    });

    try {
      const q = new URLSearchParams();
      if (forceRefresh) q.set('refresh', 'true');
      if (tableChoice) q.set('table', tableChoice);
      const dateRange = dateRangeForPreset(requestedPreset);
      if (dateRange) {
        q.set('date_from', dateRange.from);
        q.set('date_to', dateRange.to);
      }

      const res = await fetch(`${API_URL}/insights/generate/${connId}${q.toString() ? `?${q}` : ''}`, { headers });
      if (!res.ok) throw new Error(`Could not generate insights (HTTP ${res.status})`);
      const data = await res.json();
      fetchedData = data;
      pipelineDone = true;

      if (animationDone) {
        setPipelineData(fetchedData);
        setPreset(requestedPreset);
        setActiveTable(tableChoice);
        setAutoGenerateStep(null);
        setLoading(false);
      }
    } catch (err: any) {
      clearInterval(animInterval);
      setAutoGenerateStep(null);
      setLoading(false);
      setError(err?.message || 'Failed to analyze database');
    }
  };

  // A table switch recomputes the server-side analysis for that scope.
  const handleSelectTableScope = (tbl: string) => {
    if (tbl !== activeTable && !loading) void runDatabaseAnalysis(selectedConnection, tbl);
  };

  const handleApplyPreset = (id: string) => {
    if (id !== preset && !loading) void runDatabaseAnalysis(selectedConnection, activeTable, false, id);
  };

  // Interactive Drilldown Drawer Opener
  const handleOpenDrilldown = async (chartOrMetric?: any, label?: any, tableOverride?: string) => {
    const targetTable = tableOverride || chartOrMetric?.table || activeTable || (availableTables[0] || 'Invoice');
    const field = chartOrMetric?.x_field || chartOrMetric?.xKey || chartOrMetric?.x_column || chartOrMetric?.column || 'id';

    setDrillSearch('');
    setDrilldown({
      title: chartOrMetric?.title || chartOrMetric?.label || 'Record Inspection',
      table: targetTable,
      filterKey: field,
      filterValue: String(label || 'All'),
      rows: [],
      loading: true,
      error: null
    });

    try {
      let filterBody: any = label != null && label !== 'All' ? { [field]: label } : {};
      if (selectedDimensionFilter && selectedDimensionFilter.column) {
        const dimCol = selectedDimensionFilter.column.split('.').pop();
        if (dimCol && dimCol !== field) {
          filterBody = { ...filterBody, [dimCol]: selectedDimensionFilter.value };
        }
      }
      const res = await fetch(`${API_URL}/connections/${selectedConnection}/preview`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          table_name: targetTable,
          limit: 30,
          filter: filterBody
        })
      });
      if (!res.ok) throw new Error('No matching records could be retrieved for this point.');
      const j = await res.json();
      setDrilldown((d: any) => d && { ...d, rows: j.rows || [], loading: false });
    } catch (e: any) {
      setDrilldown((d: any) => d && { ...d, loading: false, error: e?.message || 'Error loading records' });
    }
  };

  // Close drilldown on Escape key
  useEffect(() => {
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setDrilldown(null);
    };
    window.addEventListener('keydown', esc);
    return () => window.removeEventListener('keydown', esc);
  }, []);

  // Clean PNG Image Export: Downloads ONLY the dashboard itself in high resolution!
  const handleExportReport = async () => {
    const dashboardElem = document.getElementById('bi-dashboard-export-target');
    if (!dashboardElem) return;
    setExporting(true);
    try {
      // Temporarily hide action buttons during screenshot
      const hideElems = dashboardElem.querySelectorAll('.no-export');
      hideElems.forEach((el) => {
        (el as HTMLElement).style.visibility = 'hidden';
      });

      const canvas = await html2canvas(dashboardElem, {
        scale: 2,
        useCORS: true,
        logging: false,
        allowTaint: true,
        backgroundColor: darkMode ? '#050714' : '#F8FAFC',
        windowWidth: 1440
      });

      // Restore action buttons
      hideElems.forEach((el) => {
        (el as HTMLElement).style.visibility = 'visible';
      });

      const cleanName = (activeConnName || 'Dashboard').replace(/[^a-zA-Z0-9]/g, '_');
      const link = document.createElement('a');
      link.download = `DataSpeakAI_${cleanName}_Analytics_Report.png`;
      link.href = canvas.toDataURL('image/png');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error('Export error:', err);
    } finally {
      setExporting(false);
    }
  };

  const selectedConnObj = connections.find((c) => c.id === selectedConnection);
  const activeConnName = selectedConnObj ? selectedConnObj.db_name : (activeTable || 'Database Analytics');

  // Raw base data from pipeline
  const baseKpis = pipelineData?.key_metrics || pipelineData?.business_summary?.key_metrics || [];
  const rawCharts = pipelineData?.charts || pipelineData?.auto_charts || [];
  const insights = pipelineData?.insights || [];
  const anomalies = pipelineData?.anomalies || [];
  const aiExecutive = pipelineData?.executive_summary || pipelineData?.business_summary || {};

  // Check if any chart or dimension actually contains a time-series or date/time column!
  const hasTimeSeriesData = useMemo(() => {
    if (!rawCharts || rawCharts.length === 0) return false;
    return rawCharts.some((c: any) => {
      const type = (c.type || '').toLowerCase();
      if (type === 'line' || type === 'area') return true;
      const xCol = (c.x_column || c.x_field || c.xKey || '').toLowerCase();
      return (
        xCol.includes('date') ||
        xCol.includes('time') ||
        xCol.includes('period') ||
        xCol.includes('month') ||
        xCol.includes('year')
      );
    });
  }, [rawCharts]);

  // The backend already applies the requested calendar range to chart queries.
  const charts = useMemo(() => {
    let result = rawCharts;

    // Filter by table scope if specific table selected
    if (activeTable) {
      const tableMatches = result.filter((c: any) => c.table?.toLowerCase() === activeTable.toLowerCase());
      if (tableMatches.length > 0) result = tableMatches;
    }

    return result;
  }, [rawCharts, activeTable]);

  // KPI values come from the same server-side calendar range as the charts.
  const kpis = useMemo(() => {
    let result = baseKpis;

    // Filter by table scope if specific table selected
    if (activeTable) {
      const tableMatches = result.filter((k: any) => k.table?.toLowerCase() === activeTable.toLowerCase());
      if (tableMatches.length > 0) result = tableMatches;
    }

    if (selectedDimensionFilter) {
      result = result.map((k: any) => ({
        ...k,
        trend_text: `${k.trend_text || ''} · ${selectedDimensionFilter.label}: ${selectedDimensionFilter.value}`
      }));
    }

    return result;
  }, [baseKpis, activeTable, selectedDimensionFilter]);

  // Dynamically derive Period Comparison from Time-Series Chart data & KPIs
  const timeSeriesChart = charts.find((c: any) => c.type === 'line' || c.type === 'area') || charts[0];
  const periodComparisonData = useMemo(() => {
    if (pipelineData?.trends && pipelineData.trends.length >= 3) {
      return pipelineData.trends;
    }
    const rows: any[] = [];
    if (timeSeriesChart && Array.isArray(timeSeriesChart.data) && timeSeriesChart.data.length >= 2) {
      const d = timeSeriesChart.data;
      const cur = d[d.length - 1];
      const prev = d[d.length - 2];
      const cVal = Number(cur.value ?? cur.y ?? 0);
      const pVal = Number(prev.value ?? prev.y ?? 0);
      const diff = pVal !== 0 ? ((cVal - pVal) / Math.abs(pVal)) * 100 : 0;
      rows.push({
        metric: `${(timeSeriesChart.title || 'Gross Velocity').replace(/Trend|Over Time/i, '').trim()} (Latest Period)`,
        current: cVal,
        previous: pVal,
        change_pct: diff,
        table: timeSeriesChart.table || 'Relational Federation'
      });

      if (d.length >= 3) {
        const prev2 = d[d.length - 3];
        const p2Val = Number(prev2.value ?? prev2.y ?? 0);
        const diff2 = p2Val !== 0 ? ((pVal - p2Val) / Math.abs(p2Val)) * 100 : 0;
        rows.push({
          metric: `${(timeSeriesChart.title || 'Gross Velocity').replace(/Trend|Over Time/i, '').trim()} (Prior Period)`,
          current: pVal,
          previous: p2Val,
          change_pct: diff2,
          table: timeSeriesChart.table || 'Relational Federation'
        });
      }

      if (d.length >= 3) {
        const recent3 = d.slice(-3);
        const avg3 = recent3.reduce((acc: number, x: any) => acc + Number(x.value ?? x.y ?? 0), 0) / 3;
        const baselineDiff = avg3 !== 0 ? ((cVal - avg3) / avg3) * 100 : 0;
        rows.push({
          metric: '3-Period Baseline Average',
          current: cVal,
          previous: avg3,
          change_pct: baselineDiff,
          table: timeSeriesChart.table || 'Statistical Baseline'
        });
      }
    }

    // Complement with top KPIs to maintain balanced rows
    if (rows.length < 4 && kpis && kpis.length > 0) {
      kpis.forEach((k: any) => {
        if (rows.length < 4 && !rows.find((r: any) => r.metric.toLowerCase().includes(k.label.toLowerCase()))) {
          if (k.status === 'unavailable' || k.status === 'error' || k.value == null) return;
          const numVal = k.raw_value;
          const trendPct = k.trend_pct;
          if (typeof numVal !== 'number' || !Number.isFinite(numVal) ||
              typeof trendPct !== 'number' || !Number.isFinite(trendPct) || trendPct === -100) return;
          const prevVal = numVal / (1 + trendPct / 100);
          rows.push({
            metric: k.label,
            current: numVal,
            previous: prevVal,
            change_pct: trendPct,
            table: k.table || 'Federated'
          });
        }
      });
    }

    return rows.length > 0 ? rows : (pipelineData?.trends || []);
  }, [pipelineData, timeSeriesChart, kpis]);

  // Dynamically derive Top Performers from Categorical Charts
  const topPerformerCharts = useMemo(() => {
    return charts.filter((c: any) => c.type === 'bar' || c.type === 'donut' || c.type === 'pie');
  }, [charts]);

  const activeTopPerformer = topPerformerCharts[activeTopPerformerCategory] || topPerformerCharts[0];
  const topPerformerRows = useMemo(() => {
    if (!activeTopPerformer || !Array.isArray(activeTopPerformer.data)) return [];
    return activeTopPerformer.data.slice(0, 7);
  }, [activeTopPerformer]);

  const maxPerformerVal = useMemo(() => {
    if (!topPerformerRows.length) return 1;
    return Math.max(1, ...topPerformerRows.map((r: any) => Number(r.value || r.count || 0)));
  }, [topPerformerRows]);

  // Filtered rows inside drilldown drawer
  const filteredDrillRows = useMemo(() => {
    if (!drilldown?.rows) return [];
    if (!drillSearch.trim()) return drilldown.rows;
    const term = drillSearch.toLowerCase();
    return drilldown.rows.filter((row: any) =>
      Object.values(row).some((val) => String(val).toLowerCase().includes(term))
    );
  }, [drilldown, drillSearch]);

  const completedAnalysisStages = Math.min(agAnalysisStep, INSIGHT_RUN_STAGES.length);
  const activeAnalysisStage = INSIGHT_RUN_STAGES[
    Math.min(agAnalysisStep, INSIGHT_RUN_STAGES.length - 1)
  ];
  const analysisProgress = Math.round(
    (completedAnalysisStages / INSIGHT_RUN_STAGES.length) * 100
  );
  const analysisScopeLabel = activeTable ? `${activeTable} table` : 'All catalog tables';
  const analysisDateLabel = PRESETS.find(([id]) => id === preset)?.[1] || 'All dates';

  return (
    <div style={{ flex: 1, minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)', padding: '20px 28px 80px', transition: 'background-color 0.3s ease, color 0.3s ease' }}>
      
      {/* Dynamic CSS Styling matching Light Enterprise Theme */}
      <style dangerouslySetInnerHTML={{ __html: `
        .bi-hub {
          max-width: 1280px;
          margin: 0 auto;
          width: 100%;
          --bg: #f8fafc;
          --card: #ffffff;
          --card-elevated: #ffffff;
          --border: #e2e8f0;
          --border-subtle: #f1f5f9;
          --text-primary: #0f172a;
          --text-secondary: #64748b;
          --text-muted: #94a3b8;
          --hover-bg: #f1f5f9;
          --shadow-card: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
          --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.06);
          --primary: #6c47ff;
          --primary-light: #f5f3ff;
        }
        .glass-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 16px;
          padding: 22px;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
          transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
        }
        .glass-card:hover {
          box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
        }
        .btn-primary {
          background: linear-gradient(135deg, #6c47ff, #00c2cb);
          color: #ffffff;
          border: none;
          padding: 10px 18px;
          border-radius: 10px;
          font-weight: 700;
          font-size: 13px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 8px;
          box-shadow: 0 4px 18px rgba(108, 71, 255, 0.28);
          transition: all 0.2s ease;
          font-family: inherit;
        }
        .btn-primary:hover {
          transform: translateY(-1.5px);
          box-shadow: 0 6px 24px rgba(108, 71, 255, 0.38);
        }
        .btn-outline {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          color: #0f172a;
          padding: 8px 14px;
          border-radius: 10px;
          font-weight: 600;
          font-size: 12.5px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          transition: all 0.2s;
          font-family: inherit;
        }
        .btn-outline:hover {
          background: #f8fafc;
          border-color: #6c47ff;
          color: #6c47ff;
        }
        .chip {
          padding: 6px 14px;
          border-radius: 20px;
          border: 1px solid #e2e8f0;
          background: #ffffff;
          color: #64748b;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.15s ease;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .chip:hover {
          background: #f1f5f9;
          color: #0f172a;
        }
        .chip.active {
          background: rgba(108, 71, 255, 0.08);
          border-color: #6c47ff;
          color: #6c47ff;
          box-shadow: 0 0 10px rgba(108,71,255,0.12);
        }
        .kpi-interactive-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 16px;
          padding: 20px;
          position: relative;
          overflow: hidden;
          cursor: pointer;
          box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
          transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .kpi-interactive-card:hover {
          border-color: #6c47ff;
          transform: translateY(-2px);
          box-shadow: 0 8px 24px -10px rgba(108,71,255,0.22);
        }
        .kpi-interactive-card.expanded {
          border-color: #6c47ff;
          box-shadow: 0 10px 28px -6px rgba(108,71,255,0.25);
        }
        .drawer-overlay {
          position: fixed;
          inset: 0;
          background: rgba(15, 23, 42, 0.45);
          backdrop-filter: blur(4px);
          z-index: 9998;
        }
        .drilldown-drawer {
          position: fixed;
          right: 0;
          top: 0;
          bottom: 0;
          width: min(520px, 100vw);
          background: #ffffff;
          border-left: 1px solid #e2e8f0;
          z-index: 9999;
          display: flex;
          flex-direction: column;
          box-shadow: -10px 0 40px rgba(0,0,0,0.08);
        }
        @media print {
          .btn-primary, .btn-outline, .chip, .drawer-overlay, .drilldown-drawer, nav, [class*="sidebar"] {
            display: none !important;
          }
        }
      ` }} />

      {/* VIEW 1: CONNECTION SELECTION LAUNCHPAD (when no database is active) */}
      {!pipelineData && autoGenerateStep !== 'analyzing' && (
        <motion.div
          className="bi-hub"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          {/* Header Bar */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px', marginBottom: '22px' }}>
            <div>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '3px 9px', borderRadius: '20px', background: 'rgba(0,194,203,0.1)', border: '1px solid rgba(0,194,203,0.25)', color: '#00c2cb', fontSize: '11px', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '8px' }}>
                <Activity size={12} /> Enterprise SQL / Relational Pipeline
              </div>
              <h1 style={{ fontSize: '26px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Database size={28} color="var(--primary)" />
                Database AI Insights Hub
              </h1>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '4px 0 0', maxWidth: '750px', lineHeight: 1.5 }}>
                Connect and analyze live SQL databases. Computes 100% deterministic metric recipes, executes pushdown relational aggregations, and delivers interactive drill-down dashboards.
              </p>
            </div>
          </div>

          {error && (
            <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: '#ef4444', borderRadius: '12px', padding: '12px 16px', marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13px' }}>
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* Launchpad Card */}
          <div className="glass-card" style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <h2 style={{ fontSize: '16px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Database size={17} color="#00c2cb" />
                  Select Database Target ({connections.length})
                </h2>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Click a database card to select scope for AI analysis
                </span>
              </div>
            </div>

            {fetchingConnections ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '140px', color: 'var(--text-secondary)' }}>
                <Loader2 size={30} className="animate-spin" style={{ marginBottom: '10px', color: 'var(--primary)' }} />
                <p style={{ fontSize: '13px', margin: 0 }}>Discovering databases...</p>
              </div>
            ) : connections.length === 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '160px', color: 'var(--text-secondary)' }}>
                <Server size={38} style={{ marginBottom: '10px', opacity: 0.5, color: 'var(--primary)' }} />
                <p style={{ fontSize: '14px', fontWeight: 600, margin: '0 0 4px', color: 'var(--text-primary)' }}>No active database connections found.</p>
                <p style={{ fontSize: '12px', margin: '0 0 14px', color: 'var(--text-secondary)' }}>Connect a database in Databases page to run insights.</p>
                <button
                  type="button"
                  onClick={() => navigate('/dashboard/databases')}
                  className="btn-primary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Database size={14} /> Manage Databases
                </button>
              </div>
            ) : (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px', marginBottom: '18px' }}>
                  {connections.map((conn) => {
                    const isSelected = selectedConnection === conn.id;
                    const dbColor = getDbColor(conn.db_type);
                    const cleanLocation = formatDbLocation(conn);
                    const isRetesting = retestingId === conn.id;

                    return (
                      <div
                        key={conn.id}
                        onClick={() => setSelectedConnection(conn.id)}
                        style={{
                          background: isSelected ? 'rgba(108,71,255,0.08)' : 'var(--card-elevated, var(--card))',
                          border: `1.5px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`,
                          borderRadius: '14px',
                          padding: '16px 18px',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          boxShadow: isSelected ? '0 0 0 1px var(--primary), 0 8px 25px rgba(108,71,255,0.18)' : 'none',
                          transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', minWidth: 0, flex: 1 }}>
                          <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: `${dbColor}18`, border: `1px solid ${dbColor}33`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                            <Database size={20} color={dbColor} />
                          </div>
                          <div style={{ minWidth: 0, flex: 1 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              <p style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>
                                {conn.db_name || conn.name}
                              </p>
                              <span style={{ fontSize: '10px', fontWeight: 700, padding: '2px 7px', borderRadius: '6px', textTransform: 'uppercase', color: dbColor, background: `${dbColor}15`, border: `1px solid ${dbColor}40` }}>
                                {conn.db_type}
                              </span>
                              {conn.status && (
                                <span style={{
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  padding: '1px 6px',
                                  borderRadius: '5px',
                                  background: conn.status === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                                  color: conn.status === 'error' ? '#ef4444' : '#10b981',
                                }}>
                                  {conn.status}
                                </span>
                              )}
                            </div>
                            <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)', display: 'block', marginTop: '3px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {cleanLocation}
                            </span>
                          </div>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: '12px', flexShrink: 0 }}>
                          <button
                            type="button"
                            title="Retest connection"
                            disabled={isRetesting}
                            onClick={(e) => handleRetestConnection(e, conn.id)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: 'var(--text-secondary)',
                              cursor: 'pointer',
                              padding: '5px',
                              borderRadius: '6px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              opacity: 0.7,
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                            onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.7')}
                          >
                            <RefreshCw size={14} className={isRetesting ? 'animate-spin' : ''} />
                          </button>
                          <button
                            type="button"
                            title="Remove connection"
                            onClick={(e) => handleDeleteConnection(e, conn.id, conn.db_name || conn.name)}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: '#ef4444',
                              cursor: 'pointer',
                              padding: '5px',
                              borderRadius: '6px',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              opacity: 0.7,
                            }}
                            onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                            onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.7')}
                          >
                            <Trash2 size={14} />
                          </button>
                          <div style={{ width: '22px', height: '22px', borderRadius: '50%', border: `2px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`, background: isSelected ? 'var(--primary)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {isSelected && <Check size={14} color="#fff" />}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Control bar */}
                {selectedConnection && (
                  <div style={{ background: 'rgba(108, 71, 255, 0.05)', border: '1px solid rgba(108, 71, 255, 0.16)', borderRadius: '12px', padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '260px' }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}>
                        <TableIcon size={14} color="var(--primary)" /> Scope:
                      </label>
                      <select
                        value={activeTable}
                        onChange={(e) => setActiveTable(e.target.value)}
                        style={{ background: 'var(--card-elevated, var(--card))', border: '1px solid var(--border)', color: 'var(--text-primary)', borderRadius: '9px', padding: '8px 12px', fontSize: '13px', outline: 'none', cursor: 'pointer', fontFamily: 'inherit' }}
                      >
                        <option value="">All Tables (Multi-Table Relational Federation)</option>
                        {availableTables.map((tbl) => (
                          <option key={tbl} value={tbl}>{tbl} table</option>
                        ))}
                      </select>
                    </div>

                    <button
                      className="btn-primary"
                      onClick={() => runDatabaseAnalysis(selectedConnection, activeTable, true)}
                      disabled={loading}
                    >
                      <Sparkles size={16} />
                      Run AI Analytics
                    </button>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Capabilities Ribbon */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '24px', flexWrap: 'wrap', padding: '12px 18px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '12px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><ShieldCheck size={14} color="#10b981" /><span>Deterministic Metric Recipes</span></div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Activity size={14} color="#00c2cb" /><span>Sub-Second SQL Aggregations</span></div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><TrendingUp size={14} color="#f59e0b" /><span>Automated Relational Federation</span></div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}><Cpu size={14} color="var(--primary)" /><span>Interactive Point Drilldown</span></div>
          </div>
        </motion.div>
      )}

      {/* VIEW 2: TRUSTED INSIGHT RUN PROGRESS (Only shown on initial run or explicit Refresh) */}
      {autoGenerateStep === 'analyzing' && !pipelineData && (
        <div style={{ minHeight: '500px', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px 0' }}>
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.28 }}
            aria-live="polite"
            aria-label="Insight analysis progress"
            style={{ width: '100%', maxWidth: '780px', overflow: 'hidden', background: 'var(--card)', border: '1px solid rgba(108, 71, 255, 0.2)', borderRadius: '20px', boxShadow: '0 18px 44px rgba(15, 23, 42, 0.10)' }}
          >
            <div style={{ padding: '26px 28px 22px', background: 'linear-gradient(135deg, rgba(108, 71, 255, 0.10), rgba(0, 194, 203, 0.08))', borderBottom: '1px solid rgba(108, 71, 255, 0.14)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
                  <div style={{ width: '48px', height: '48px', background: 'linear-gradient(135deg,#6c47ff,#00c2cb)', borderRadius: '14px', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 22px rgba(108,71,255,0.30)', flexShrink: 0 }}>
                    <Layers size={24} color="#fff" />
                  </div>
                  <div>
                    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '4px 8px', borderRadius: '999px', background: 'rgba(108, 71, 255, 0.12)', color: '#6246EA', fontSize: '10px', fontWeight: 800, letterSpacing: '0.08em' }}>
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', boxShadow: '0 0 0 4px rgba(16,185,129,0.12)' }} />
                      PHASE A–F INSIGHT RUN
                    </div>
                    <h3 style={{ fontSize: '20px', lineHeight: 1.25, fontWeight: 800, color: 'var(--text-primary)', margin: '9px 0 5px', letterSpacing: '-0.02em' }}>
                      Building a trusted view of your data
                    </h3>
                    <p style={{ fontSize: '12.5px', color: 'var(--text-secondary)', margin: 0 }}>
                      {activeConnName} · {analysisScopeLabel} · {analysisDateLabel}
                    </p>
                  </div>
                </div>
                <div style={{ padding: '8px 10px', borderRadius: '10px', background: 'rgba(255,255,255,0.68)', border: '1px solid rgba(108, 71, 255, 0.16)', color: '#6246EA', fontSize: '11px', fontWeight: 800, whiteSpace: 'nowrap' }}>
                  Phase {activeAnalysisStage.phase} in progress
                </div>
              </div>

              <div style={{ marginTop: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', marginBottom: '8px', color: 'var(--text-secondary)', fontSize: '11px', fontWeight: 700 }}>
                  <span>{completedAnalysisStages} of {INSIGHT_RUN_STAGES.length} safeguards prepared</span>
                  <span>{analysisProgress}%</span>
                </div>
                <div style={{ height: '8px', overflow: 'hidden', borderRadius: '999px', background: 'rgba(108, 71, 255, 0.12)' }}>
                  <motion.div animate={{ width: `${analysisProgress}%` }} transition={{ duration: 0.35, ease: 'easeOut' }} style={{ height: '100%', borderRadius: 'inherit', background: 'linear-gradient(90deg, #6C47FF, #00C2CB)' }} />
                </div>
              </div>
            </div>

            <div style={{ padding: '18px 20px 14px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
              {INSIGHT_RUN_STAGES.map((s, idx) => {
              const isDone = agAnalysisStep > idx;
              const isActive = agAnalysisStep === idx;
              const Icon = s.icon;
              return (
                <div
                  key={s.phase}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '12px',
                    minHeight: '92px',
                    padding: '13px',
                    borderRadius: '12px',
                    background: isActive ? 'rgba(108,71,255,0.09)' : isDone ? 'rgba(16,185,129,0.075)' : 'var(--card-elevated, var(--card))',
                    border: `1px solid ${isActive ? 'rgba(108,71,255,0.34)' : isDone ? 'rgba(16,185,129,0.24)' : 'var(--border)'}`,
                    transition: 'all 0.3s ease'
                  }}
                >
                  <div style={{ width: '32px', height: '32px', borderRadius: '9px', background: isActive ? 'rgba(108,71,255,0.18)' : isDone ? 'rgba(16,185,129,0.15)' : 'var(--hover-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {isDone ? <Check size={16} color="#10B981" /> : isActive ? <Loader2 size={16} className="animate-spin" color="var(--primary)" /> : <Icon size={16} color="var(--text-secondary)" />}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '7px', flexWrap: 'wrap' }}>
                      <span style={{ color: isActive ? '#6246EA' : isDone ? '#059669' : 'var(--text-secondary)', fontSize: '10px', fontWeight: 800, letterSpacing: '0.06em' }}>PHASE {s.phase}</span>
                      <span style={{ color: isActive ? '#6246EA' : isDone ? '#059669' : 'var(--text-secondary)', fontSize: '10px', fontWeight: 700 }}>{isDone ? 'Complete' : isActive ? 'Working' : 'Queued'}</span>
                    </div>
                    <div style={{ color: isActive ? 'var(--primary)' : isDone ? '#047857' : 'var(--text-primary)', fontSize: '12.5px', fontWeight: 750, marginTop: '3px' }}>{s.title}</div>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '10.5px', lineHeight: 1.45, margin: '4px 0 0' }}>{s.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', padding: '0 20px 20px' }}>
              {['Read-only analysis', 'Tenant-scoped context', 'Quality-aware results'].map((item) => (
                <span key={item} style={{ padding: '5px 8px', borderRadius: '999px', background: 'var(--hover-bg)', color: 'var(--text-secondary)', fontSize: '10.5px', fontWeight: 700 }}>{item}</span>
              ))}
              <span style={{ marginLeft: 'auto', alignSelf: 'center', color: 'var(--text-secondary)', fontSize: '10.5px' }}>{activeAnalysisStage.detail}</span>
            </div>
          </motion.section>
        </div>
      )}

      {/* VIEW 3: FULL ENTERPRISE DASHBOARD WITH DRILLDOWN & SPARKLINES */}
      {pipelineData && (
        <motion.div
          id="bi-dashboard-export-target"
          className="bi-hub"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          style={{
            background: darkMode ? '#050714' : '#F8FAFC',
            color: darkMode ? '#F8FAFC' : '#0F172A',
            padding: '28px',
            borderRadius: '20px',
            border: `1px solid ${darkMode ? 'rgba(139, 92, 246, 0.25)' : '#E2E8F0'}`
          }}
        >
          {/* Dashboard Header Bar - Solid & High Contrast for Both Screen & Export */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '14px', marginBottom: '22px', borderBottom: `1px solid ${darkMode ? 'rgba(255,255,255,0.08)' : '#E2E8F0'}`, paddingBottom: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
              <button
                className="btn-outline no-export"
                onClick={() => setPipelineData(null)}
              >
                <ArrowLeft size={14} /> Back to Databases
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '42px', height: '42px', borderRadius: '12px', background: 'linear-gradient(135deg, #6C63FF, #00C2CB)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 4px 18px rgba(108,99,255,0.4)', flexShrink: 0 }}>
                  <Database size={22} color="#FFFFFF" />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <h1 style={{ fontSize: '24px', fontWeight: 800, margin: 0, color: darkMode ? '#FFFFFF' : '#0F172A', letterSpacing: '-0.02em' }}>
                      {activeConnName}
                    </h1>
                    <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 9px', borderRadius: '6px', background: 'rgba(108,71,255,0.18)', border: '1px solid rgba(108,71,255,0.35)', color: '#A855F7', textTransform: 'uppercase' }}>
                      {pipelineData.db_type || 'SQL'}
                    </span>
                    <span style={{ fontSize: '11px', fontWeight: 700, padding: '3px 9px', borderRadius: '6px', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)', color: '#10B981' }}>
                      ● Live Analysis
                    </span>
                  </div>
                  <p style={{ fontSize: '12.5px', color: darkMode ? '#94A3B8' : '#64748B', margin: '3px 0 0' }}>
                    Live Multi-Table Relational Intelligence · {kpis.length} Deterministic Metrics · {charts.length} Analytical Views
                  </p>
                  <p style={{ fontSize: '12px', color: '#64748B', margin: '3px 0 0' }}>
                    {pipelineData.applied_date_from || pipelineData.applied_date_to
                      ? `Applied dates: ${pipelineData.applied_date_from || 'earliest'} to ${pipelineData.applied_date_to || 'latest'}`
                      : 'All dates'}
                    {loading ? ' · Updating analysis…' : ''}
                  </p>
                </div>
              </div>
            </div>

            {/* Action buttons (hidden during PNG export with .no-export class) */}
            <div className="no-export" style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <button
                className="btn-outline"
                onClick={() => runDatabaseAnalysis(selectedConnection, activeTable, true)}
                disabled={loading}
              >
                <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
              </button>

              <button
                className="btn-outline"
                onClick={handleExportReport}
                disabled={exporting}
                title="Download high-resolution image of this dashboard"
              >
                {exporting ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                {exporting ? 'Generating PNG...' : 'Export Report'}
              </button>

              <button
                className="btn-primary"
                onClick={() => navigate(`/connections?connection_id=${selectedConnection}&view=query`)}
              >
                <MessageSquare size={14} /> Ask AI Analyst
              </button>
            </div>
          </div>

          {/* Quick Date Presets & Filter Strip (ONLY shown if time-series data or multi-tables exist!) */}
          {(hasTimeSeriesData || preset !== 'all' || availableTables.length > 1 || (pipelineData?.filters && pipelineData.filters.some((f: any) => f.options && f.options.length > 0))) && (
            <div className="glass-card no-export" style={{ padding: '14px 18px', marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                {/* Only show Date Horizon if date/timeline column actually exists in data! */}
                {(hasTimeSeriesData || preset !== 'all') ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginRight: '4px' }}>
                      <Clock size={13} style={{ verticalAlign: -2 }} /> Horizon:
                    </span>
                    {PRESETS.map(([id, label]) => (
                      <button
                        key={id}
                        className={`chip ${preset === id ? 'active' : ''}`}
                        onClick={() => handleApplyPreset(id)}
                        disabled={loading}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                ) : <div />}

                {/* Table Scope Selector with ZERO-TOKEN Client-side instant filter */}
                {availableTables.length > 1 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginLeft: hasTimeSeriesData ? 'auto' : 0 }}>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                      <TableIcon size={13} style={{ verticalAlign: -2 }} /> Scope:
                    </span>
                    <button
                      className={`chip ${!activeTable ? 'active' : ''}`}
                      onClick={() => handleSelectTableScope('')}
                      disabled={loading}
                    >
                      Federated (All)
                    </button>
                    {availableTables.slice(0, 6).map((tbl) => (
                      <button
                        key={tbl}
                        className={`chip ${activeTable === tbl ? 'active' : ''}`}
                        onClick={() => handleSelectTableScope(tbl)}
                        disabled={loading}
                      >
                        {tbl}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Dimensional Filters Row (Borough, Cuisine, etc.) */}
              {pipelineData?.filters && pipelineData.filters.filter((f: any) => f.options && f.options.length > 0 && (!activeTable || f.column.toLowerCase().startsWith(activeTable.toLowerCase()))).length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
                  <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <Filter size={13} style={{ verticalAlign: -1 }} /> Filter by:
                  </span>
                  {pipelineData.filters
                    .filter((f: any) => f.options && f.options.length > 0 && (!activeTable || f.column.toLowerCase().startsWith(activeTable.toLowerCase())))
                    .slice(0, 4)
                    .map((f: any) => {
                      const isActive = selectedDimensionFilter?.column === f.column;
                      return (
                        <div key={f.column} style={{ display: 'flex', alignItems: 'center' }}>
                          <select
                            value={isActive ? selectedDimensionFilter.value : ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              if (val) {
                                setSelectedDimensionFilter({ column: f.column, label: f.label, value: val });
                              } else {
                                setSelectedDimensionFilter(null);
                              }
                            }}
                            style={{
                              padding: '5px 12px',
                              borderRadius: '20px',
                              border: isActive ? '1px solid #6c47ff' : '1px solid var(--border)',
                              background: isActive ? 'rgba(108, 71, 255, 0.08)' : 'var(--card)',
                              color: isActive ? '#6c47ff' : 'var(--text-primary)',
                              fontSize: '12px',
                              fontWeight: 600,
                              cursor: 'pointer',
                              outline: 'none'
                            }}
                          >
                            <option value="">{f.label}: All</option>
                            {f.options.map((opt: string) => (
                              <option key={opt} value={opt}>{opt}</option>
                            ))}
                          </select>
                        </div>
                      );
                    })}

                  {selectedDimensionFilter && (
                    <button
                      className="chip"
                      onClick={() => setSelectedDimensionFilter(null)}
                      style={{ color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)', padding: '4px 10px', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    >
                      <X size={12} /> Clear ({selectedDimensionFilter.value})
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Strategic Executive Playbook Summary */}
          {aiExecutive?.executive_summary && (
            <div style={{
              background: darkMode ? 'rgba(13, 18, 36, 0.85)' : '#FFFFFF',
              border: `1px solid ${darkMode ? 'rgba(139, 92, 246, 0.3)' : '#E2E8F0'}`,
              borderRadius: '16px',
              padding: '20px 24px',
              marginBottom: '22px',
              boxShadow: darkMode ? '0 8px 32px rgba(0,0,0,0.5)' : '0 4px 16px rgba(0,0,0,0.06)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Sparkles size={16} color="#6C63FF" />
                <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#6C63FF', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  {aiExecutive.source === 'deterministic_fallback'
                    ? 'Auto-generated summary (AI unavailable)'
                    : aiExecutive.source === 'llm'
                      ? `Dual-Engine AI Executive Playbook (${aiExecutive.business_domain || 'Enterprise Business'})`
                      : 'Executive summary'}
                </span>
              </div>
              <p style={{ fontSize: '14px', color: darkMode ? '#F8FAFC' : '#1E293B', margin: 0, lineHeight: 1.6, fontWeight: 500 }}>
                {aiExecutive.executive_summary}
              </p>
            </div>
          )}

          {/* SECTION 1: EXPANDABLE KPI CARDS WITH SPARKLINES */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <h2 style={{ fontSize: '15px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={16} color="var(--primary)" />
                Deterministic Key Metrics ({kpis.length})
              </h2>
              <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                Click any card to expand sparkline & inspect records
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 230px), 1fr))', gap: '14px' }}>
              {kpis.map((kpi: any, idx: number) => {
                const isExpanded = expandedKpi === idx;
                const accentColor = KPI_ACCENTS[idx % KPI_ACCENTS.length];
                const isUp = kpi.trend_direction === 'up';
                const isDown = kpi.trend_direction === 'down';
                const unavailable = kpi.status === 'unavailable' || kpi.status === 'error' || kpi.value == null;
                const reasonLabel = KPI_REASON_LABELS[kpi.reason] || 'Metric unavailable';

                // Find matching sparkline dataset from charts
                const matchingChart = charts.find((c: any) => c.table === kpi.table && Array.isArray(c.data) && c.data.length > 2) || timeSeriesChart;
                const sparkData = matchingChart?.data ? matchingChart.data.slice(-8) : [];

                return (
                  <div
                    key={idx}
                    className={`kpi-interactive-card ${isExpanded ? 'expanded' : ''}`}
                    onClick={() => setExpandedKpi(isExpanded ? null : idx)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        {kpi.label}
                      </span>
                      <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: `${accentColor}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Activity size={14} color={accentColor} />
                      </div>
                    </div>

                    <div style={{ fontSize: '28px', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-primary)', marginBottom: '6px' }}>
                      <AnimatedCount value={unavailable ? '—' : kpi.value} />
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11.5px' }}>
                      <span style={{ color: unavailable ? '#b45309' : isUp ? '#10b981' : isDown ? '#ef4444' : 'var(--text-secondary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        {unavailable ? <AlertCircle size={13} /> : isUp ? <TrendingUp size={13} /> : isDown ? <TrendingDown size={13} /> : <Minus size={13} />}
                        {unavailable ? reasonLabel : kpi.trend_text || (kpi.trend_pct != null ? `${Math.abs(kpi.trend_pct)}% vs baseline` : 'All-time value')}
                      </span>
                      <span style={{ color: 'var(--text-secondary)', fontSize: '11px', fontWeight: 500 }}>
                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </span>
                    </div>

                    {/* Expandable Mini Sparkline & Drilldown Trigger */}
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border)' }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                            <span>Recent Trajectory:</span>
                            <span style={{ color: 'var(--primary)', fontWeight: 600 }}>{kpi.table || 'Relational'} Table</span>
                          </div>

                          {sparkData.length > 1 ? (
                            <div style={{ height: '90px', width: '100%', marginBottom: '10px' }}>
                              <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={sparkData}>
                                  <defs>
                                    <linearGradient id={`spark-${idx}`} x1="0" y1="0" x2="0" y2="1">
                                      <stop offset="5%" stopColor={accentColor} stopOpacity={0.4} />
                                      <stop offset="95%" stopColor={accentColor} stopOpacity={0} />
                                    </linearGradient>
                                  </defs>
                                  <Tooltip content={<CustomChartTooltip />} />
                                  <Area type="monotone" dataKey="value" stroke={accentColor} strokeWidth={2} fill={`url(#spark-${idx})`} />
                                </AreaChart>
                              </ResponsiveContainer>
                            </div>
                          ) : (
                            <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                              Formula: Deterministic recipe compiled across {kpi.table || 'target'} records.
                            </div>
                          )}

                          <button
                            className="btn-outline"
                            style={{ width: '100%', justifyContent: 'center', fontSize: '11.5px', padding: '6px' }}
                            onClick={() => handleOpenDrilldown({ title: kpi.label, table: kpi.table, column: kpi.column }, 'All', kpi.table)}
                          >
                            <Search size={12} /> Inspect {kpi.table || 'Table'} Records
                          </button>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })}
            </div>
          </div>

          {/* SECTION 2: PERIOD COMPARISON & TOP PERFORMERS DUAL GRID */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: '18px', marginBottom: '24px' }}>
            
            {/* Widget A: Period Comparison Table */}
            <div className="glass-card">
              <h3 style={{ fontSize: '14px', fontWeight: 700, margin: '0 0 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <TrendingUp size={16} color="var(--primary)" />
                Period Velocity & Growth Comparison
              </h3>

              {periodComparisonData.length > 0 ? (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                      <th style={{ padding: '8px 4px', fontWeight: 600 }}>Metric / Entity</th>
                      <th style={{ padding: '8px 4px', textAlign: 'right', fontWeight: 600 }}>Current</th>
                      <th style={{ padding: '8px 4px', textAlign: 'right', fontWeight: 600 }}>Previous</th>
                      <th style={{ padding: '8px 4px', textAlign: 'right', fontWeight: 600 }}>Change</th>
                    </tr>
                  </thead>
                  <tbody>
                    {periodComparisonData.map((t: any, i: number) => {
                      const isPositive = (t.change_pct ?? 0) >= 0;
                      return (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '10px 4px' }}>
                            <strong style={{ color: 'var(--text-primary)' }}>{t.metric || t.table}</strong>
                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{t.table || 'Federated SQL'}</div>
                          </td>
                          <td style={{ padding: '10px 4px', textAlign: 'right', fontWeight: 600, color: 'var(--text-primary)' }}>
                            {typeof t.current === 'number' ? (t.current >= 1000 ? t.current.toLocaleString() : t.current.toFixed(2)) : t.current}
                          </td>
                          <td style={{ padding: '10px 4px', textAlign: 'right', color: 'var(--text-secondary)' }}>
                            {typeof t.previous === 'number' ? (t.previous >= 1000 ? t.previous.toLocaleString() : t.previous.toFixed(2)) : t.previous}
                          </td>
                          <td style={{ padding: '10px 4px', textAlign: 'right', fontWeight: 700, color: isPositive ? '#10b981' : '#ef4444' }}>
                            {isPositive ? '+' : ''}{Number(t.change_pct || 0).toFixed(1)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <div style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', padding: '30px 0' }}>
                  No historical periods available for comparison.
                </div>
              )}
            </div>

            {/* Widget B: Top Performers Ranking with Progress Bars */}
            <div className="glass-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Sparkles size={16} color="#10b981" />
                  Top Performers Ranking
                </h3>

                {topPerformerCharts.length > 1 && (
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {topPerformerCharts.map((c: any, idx: number) => (
                      <button
                        key={idx}
                        className={`chip ${activeTopPerformerCategory === idx ? 'active' : ''}`}
                        style={{ padding: '4px 10px', fontSize: '11px' }}
                        onClick={() => setActiveTopPerformerCategory(idx)}
                      >
                        {c.x_column || c.title?.split(' ')[1] || `View ${idx + 1}`}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {topPerformerRows.length > 0 ? (
                <div>
                  {topPerformerRows.map((p: any, idx: number) => {
                    const pVal = Number(p.value || p.count || 0);
                    const pName = p.name || p.x || p.category || `Item ${idx + 1}`;
                    const pct = Math.min(100, Math.max(5, (pVal / maxPerformerVal) * 100));

                    return (
                      <div
                        key={idx}
                        style={{ marginBottom: '12px', cursor: 'pointer' }}
                        onClick={() => handleOpenDrilldown(activeTopPerformer, pName)}
                        title={`Click to inspect records for ${pName}`}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12.5px', marginBottom: '4px' }}>
                          <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                            <span style={{ color: 'var(--primary)', marginRight: '6px' }}>#{idx + 1}</span> {pName}
                          </span>
                          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                            {pVal >= 1000 ? pVal.toLocaleString() : pVal.toFixed(2)}
                          </span>
                        </div>
                        <div style={{ height: '7px', background: 'var(--hover-bg, #f1f5f9)', borderRadius: '10px', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', background: 'linear-gradient(90deg, #6c47ff, #00c2cb)', borderRadius: '10px', transition: 'width 0.4s ease' }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', padding: '30px 0' }}>
                  No ranking entities identified in dataset.
                </div>
              )}
            </div>

          </div>

          {/* SECTION 3: INTERACTIVE CHARTS GRID WITH CLICK-TO-DRILLDOWN */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <h2 style={{ fontSize: '15px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={16} color="var(--primary)" />
                Relational Dimensional Charts ({charts.length})
              </h2>
              <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                Click any bar or chart point to drill into underlying records
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 460px), 1fr))', gap: '18px' }}>
              {charts.map((c: any, idx: number) => {
                const chartType = (c.type || 'bar').toLowerCase();
                const chartData = c.data || [];
                const color = c.color || PALETTE[idx % PALETTE.length];

                return (
                  <div key={idx} className="glass-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '14px' }}>
                      <div>
                        <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
                          {c.title}
                        </h3>
                        <p style={{ fontSize: '11.5px', color: 'var(--text-secondary)', margin: '3px 0 0' }}>
                          {c.subtitle || `Grouped along ${c.x_column || 'dimension'}`}
                        </p>
                      </div>
                      <span style={{ fontSize: '10.5px', fontWeight: 700, padding: '2px 8px', borderRadius: '6px', background: 'var(--hover-bg, rgba(255,255,255,0.06))', border: '1px solid var(--border)', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                        {chartType}
                      </span>
                    </div>

                    <div style={{ height: '260px', width: '100%' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        {chartType === 'line' || chartType === 'area' ? (
                          <AreaChart
                            data={chartData}
                            onClick={(e: any) => {
                              if (e && e.activeLabel != null) {
                                handleOpenDrilldown(c, e.activeLabel);
                              }
                            }}
                          >
                            <defs>
                              <linearGradient id={`grad-${idx}`} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={color} stopOpacity={0.4} />
                                <stop offset="95%" stopColor={color} stopOpacity={0} />
                              </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} vertical={false} />
                            <XAxis dataKey={c.xKey || 'period'} stroke="var(--text-secondary)" fontSize={11} tickLine={false} axisLine={false} />
                            <YAxis stroke="var(--text-secondary)" fontSize={11} tickLine={false} axisLine={false} width={45} />
                            <Tooltip content={<CustomChartTooltip />} />
                            <Area type="monotone" dataKey={c.yKey || 'value'} stroke={color} strokeWidth={2.4} fill={`url(#grad-${idx})`} activeDot={{ r: 6, fill: color }} />
                          </AreaChart>
                        ) : chartType === 'donut' || chartType === 'pie' ? (
                          <PieChart>
                            <Tooltip content={<CustomChartTooltip />} />
                            <Legend verticalAlign="bottom" iconType="circle" wrapperStyle={{ fontSize: '11px', color: 'var(--text-secondary)' }} />
                            <Pie
                              data={chartData}
                              dataKey={c.yKey || 'value'}
                              nameKey={c.xKey || 'name'}
                              innerRadius={chartType === 'donut' ? 52 : 0}
                              outerRadius={84}
                              paddingAngle={2}
                              onClick={(entry: any) => handleOpenDrilldown(c, entry?.name || entry?.category)}
                              cursor="pointer"
                            >
                              {chartData.map((_: any, i: number) => (
                                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                              ))}
                            </Pie>
                          </PieChart>
                        ) : (
                          <BarChart
                            data={chartData}
                            onClick={(e: any) => {
                              if (e && e.activeLabel != null) {
                                handleOpenDrilldown(c, e.activeLabel);
                              }
                            }}
                          >
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.5} vertical={false} />
                            <XAxis dataKey={c.xKey || 'name'} stroke="var(--text-secondary)" fontSize={11} tickLine={false} axisLine={false} />
                            <YAxis stroke="var(--text-secondary)" fontSize={11} tickLine={false} axisLine={false} width={45} />
                            <Tooltip content={<CustomChartTooltip />} />
                            <Bar dataKey={c.yKey || 'value'} fill={color} radius={[6, 6, 0, 0]} maxBarSize={38} cursor="pointer" />
                          </BarChart>
                        )}
                      </ResponsiveContainer>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                      <span>Source: {c.table || 'Relational Federation'}</span>
                      <span style={{ color: 'var(--primary)', cursor: 'pointer', fontWeight: 600 }} onClick={() => handleOpenDrilldown(c, 'All')}>
                        Inspect All Records →
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* STATISTICAL OUTLIER & ANOMALY BANNER */}
          {anomalies && anomalies.length > 0 && (
            <div style={{
              background: darkMode ? 'rgba(217, 119, 6, 0.08)' : '#FFFBEB',
              border: `1px solid ${darkMode ? 'rgba(217, 119, 6, 0.3)' : '#FDE68A'}`,
              borderRadius: '14px',
              padding: '16px 20px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '14px',
              boxShadow: darkMode ? '0 4px 20px rgba(217, 119, 6, 0.1)' : '0 2px 8px rgba(217, 119, 6, 0.08)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: 1, minWidth: '280px' }}>
                <div style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '10px',
                  background: 'rgba(217, 119, 6, 0.16)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#D97706',
                  flexShrink: 0
                }}>
                  <AlertTriangle size={22} />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                    <span style={{ fontSize: '13.5px', fontWeight: 700, color: darkMode ? '#FDE68A' : '#92400E' }}>
                      Statistical Outlier & Anomaly Detected
                    </span>
                    <span style={{ fontSize: '10px', fontWeight: 800, padding: '2px 8px', borderRadius: '999px', background: 'rgba(217, 119, 6, 0.25)', color: '#D97706', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                      {anomalies.length} Flagged
                    </span>
                  </div>
                  <div style={{ fontSize: '12.5px', color: darkMode ? '#CBD5E1' : '#475569', lineHeight: 1.5 }}>
                    {anomalies.map((a: any, i: number) => (
                      <span key={i}>
                        <strong style={{ color: darkMode ? '#FCD34D' : '#B45309' }}>{a.table} · {a.field}:</strong> {a.deviation || `Peak transaction deviates sharply from expected baseline average.`}
                        {i < anomalies.length - 1 ? ' | ' : ''}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <button
                className="btn-outline"
                style={{
                  borderColor: darkMode ? 'rgba(217, 119, 6, 0.45)' : '#FCD34D',
                  color: '#D97706',
                  fontSize: '12px',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  background: darkMode ? 'rgba(217, 119, 6, 0.08)' : '#FEF3C7'
                }}
                onClick={() => handleOpenDrilldown({ title: anomalies[0]?.field, table: anomalies[0]?.table }, 'All')}
              >
                <Search size={13} /> Inspect Outlier Records →
              </button>
            </div>
          )}

          {/* SECTION 4: STRATEGIC TACTICAL RECOMMENDATIONS (FULL-WIDTH 3-COLUMN GRID) */}
          <div style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Lightbulb size={17} color="var(--primary)" />
                Strategic Tactical Recommendations ({insights.length})
              </h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {(!anomalies || anomalies.length === 0) && (
                  <span style={{ fontSize: '11.5px', color: '#10B981', display: 'inline-flex', alignItems: 'center', gap: '4px', background: 'rgba(16, 185, 129, 0.1)', padding: '3px 10px', borderRadius: '999px', fontWeight: 600 }}>
                    <CheckCircle2 size={13} /> Statistical Baselines Stable
                  </span>
                )}
                <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                  AI synthesized from multi-table metric recipes
                </span>
              </div>
            </div>

            {insights.length > 0 ? (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 330px), 1fr))',
                gap: '16px'
              }}>
                {insights.map((n: any, i: number) => {
                  const REC_COLORS = ['#6C63FF', '#00C2CB', '#10B981', '#F59E0B', '#EC4899'];
                  const accent = REC_COLORS[i % REC_COLORS.length];
                  const isHigh = (n.impact || '').toLowerCase() === 'high';
                  const isMed = (n.impact || '').toLowerCase() === 'medium';

                  return (
                    <div
                      key={i}
                      className="glass-card"
                      style={{
                        padding: '22px 20px',
                        display: 'flex',
                        flexDirection: 'column',
                        borderRadius: '16px',
                        borderTop: `3px solid ${accent}`,
                        transition: 'transform 0.2s ease, box-shadow 0.2s ease'
                      }}
                    >
                      {/* Top Meta Bar */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <span style={{
                          fontSize: '10.5px',
                          fontWeight: 800,
                          padding: '3px 8px',
                          borderRadius: '6px',
                          background: `${accent}18`,
                          color: accent,
                          letterSpacing: '0.06em',
                          textTransform: 'uppercase'
                        }}>
                          #{String(i + 1).padStart(2, '0')} Pillar
                        </span>

                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '5px',
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '3px 9px',
                          borderRadius: '999px',
                          background: darkMode
                            ? (isHigh ? 'rgba(239, 68, 68, 0.12)' : isMed ? 'rgba(245, 158, 11, 0.12)' : 'rgba(16, 185, 129, 0.12)')
                            : (isHigh ? '#FEF2F2' : isMed ? '#FFFBEB' : '#ECFDF5'),
                          color: darkMode
                            ? (isHigh ? '#F87171' : isMed ? '#FBBF24' : '#34D399')
                            : (isHigh ? '#DC2626' : isMed ? '#D97706' : '#059669'),
                          border: `1px solid ${darkMode
                            ? (isHigh ? 'rgba(239, 68, 68, 0.25)' : isMed ? 'rgba(245, 158, 11, 0.25)' : 'rgba(16, 185, 129, 0.25)')
                            : (isHigh ? '#FECACA' : isMed ? '#FDE68A' : '#A7F3D0')}`
                        }}>
                          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: isHigh ? '#EF4444' : isMed ? '#F59E0B' : '#10B981' }} />
                          {n.impact || 'Strategic'} Impact
                        </span>
                      </div>

                      {/* Title */}
                      <h4 style={{
                        fontSize: '15px',
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                        margin: '0 0 10px',
                        lineHeight: 1.35
                      }}>
                        {n.title}
                      </h4>

                      {/* Description */}
                      <p style={{
                        fontSize: '12.5px',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.6,
                        margin: '0 0 18px',
                        flex: 1
                      }}>
                        {n.description}
                      </p>

                      {/* Tactical Action Box */}
                      {n.suggested_action && (
                        <div style={{
                          marginTop: 'auto',
                          background: darkMode ? 'rgba(108, 99, 255, 0.07)' : '#F5F3FF',
                          border: `1px solid ${darkMode ? 'rgba(108, 99, 255, 0.2)' : '#EDE9FE'}`,
                          borderLeft: `4px solid ${accent}`,
                          borderRadius: '10px',
                          padding: '12px 14px'
                        }}>
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontSize: '10.5px',
                            fontWeight: 800,
                            color: accent,
                            textTransform: 'uppercase',
                            letterSpacing: '0.06em',
                            marginBottom: '4px'
                          }}>
                            <Zap size={12} /> Tactical Action
                          </div>
                          <div style={{
                            fontSize: '12px',
                            color: darkMode ? '#E2E8F0' : '#334155',
                            lineHeight: 1.55,
                            fontWeight: 500
                          }}>
                            {n.suggested_action}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="glass-card" style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', padding: '36px 0' }}>
                No tactical recommendations generated for current scope.
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* RIGHT SLIDING DRILL-DOWN RECORD DRAWER (Option B Feature) */}
      <AnimatePresence>
        {drilldown && (
          <>
            <motion.div
              className="drawer-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDrilldown(null)}
            />

            <motion.aside
              className="drilldown-drawer"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 220 }}
            >
              {/* Drawer Header */}
              <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    <Search size={12} /> Drill-Down Record Inspector
                  </div>
                  <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
                    {drilldown.title}
                  </h2>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
                    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'var(--hover-bg, rgba(255,255,255,0.06))', border: '1px solid var(--border)' }}>
                      Table: <strong>{drilldown.table}</strong>
                    </span>
                    <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '4px', background: 'rgba(108,71,255,0.1)', color: 'var(--primary)' }}>
                      Filter: <strong>{drilldown.filterValue}</strong>
                    </span>
                  </div>
                </div>

                <button
                  onClick={() => setDrilldown(null)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '6px', borderRadius: '8px' }}
                >
                  <X size={18} />
                </button>
              </div>

              {/* Drawer Search Filter */}
              <div style={{ padding: '12px 24px', borderBottom: '1px solid var(--border)', background: 'var(--card)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--hover-bg, rgba(255,255,255,0.05))', border: '1px solid var(--border)', borderRadius: '8px', padding: '6px 12px' }}>
                  <Search size={14} color="var(--text-secondary)" />
                  <input
                    type="text"
                    placeholder="Search inside retrieved records..."
                    value={drillSearch}
                    onChange={(e) => setDrillSearch(e.target.value)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-primary)', outline: 'none', fontSize: '12.5px', width: '100%', fontFamily: 'inherit' }}
                  />
                  {drillSearch && (
                    <X size={13} style={{ cursor: 'pointer', color: 'var(--text-secondary)' }} onClick={() => setDrillSearch('')} />
                  )}
                </div>
              </div>

              {/* Drawer Body / Records list */}
              <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
                {drilldown.loading ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '240px', color: 'var(--text-secondary)' }}>
                    <Loader2 size={32} className="animate-spin" color="var(--primary)" style={{ marginBottom: '12px' }} />
                    <span style={{ fontSize: '13px' }}>Querying live database records...</span>
                  </div>
                ) : drilldown.error ? (
                  <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.25)', color: '#ef4444', borderRadius: '10px', padding: '14px', fontSize: '13px' }}>
                    {drilldown.error}
                  </div>
                ) : filteredDrillRows.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)', fontSize: '13px' }}>
                    No matching records found for this slice.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gap: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                      Showing {filteredDrillRows.length} matching database rows:
                    </div>

                    {filteredDrillRows.map((row: any, rIdx: number) => (
                      <div
                        key={rIdx}
                        style={{
                          background: 'var(--card)',
                          border: '1px solid var(--border)',
                          borderRadius: '12px',
                          padding: '14px 16px',
                          boxShadow: 'var(--shadow-card)',
                          fontSize: '12.5px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', borderBottom: '1px solid var(--border)', paddingBottom: '6px' }}>
                          <span style={{ fontWeight: 700, color: 'var(--primary)' }}>
                            Record #{rIdx + 1}
                          </span>
                          <span style={{ fontSize: '10.5px', color: 'var(--text-secondary)' }}>
                            {drilldown.table}
                          </span>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                          {Object.entries(row).map(([k, v]) => (
                            <div key={k} style={{ minWidth: 0 }}>
                              <div style={{ fontSize: '10.5px', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                                {k.replace(/_/g, ' ')}
                              </div>
                              <div style={{ fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={String(v)}>
                                {v === null || v === undefined ? '—' : String(v)}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Drawer Footer */}
              <div style={{ padding: '14px 24px', borderTop: '1px solid var(--border)', background: 'var(--card)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {filteredDrillRows.length} records retrieved
                </span>
                <button
                  className="btn-outline"
                  onClick={() => setDrilldown(null)}
                  style={{ fontSize: '12px', padding: '6px 14px' }}
                >
                  Close Drawer
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default BusinessInsightsPage;
