// @ts-nocheck
import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import html2canvas from 'html2canvas';
import {
  BarChart, Bar, LineChart, Line, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, PieChart, Pie, Cell,
  ScatterChart, Scatter
} from 'recharts';

import {
  BarChart2, Brain, Sparkles, CheckCircle,
  TrendingUp, TrendingDown, Minus, AlertTriangle,
  PieChart as PieChartIcon, Grid, Activity,
  LayoutGrid, Filter, Database, Check, RefreshCw,
  Moon, Download, ArrowLeft
} from 'lucide-react';
const useTheme = () => ({ darkMode: false, toggleTheme: () => {} });

const DATASPEAK_THEME = {
  bg: '#f8fafc',
  glass: '#ffffff',
  glassBorder: '#e2e8f0',
  primary: '#6c47ff',
  primaryLight: '#9b7dff',
  secondary: '#00c2cb',
  secondaryLight: '#5eead4',
  warning: '#f59e0b',
  warningLight: '#fbbf24',
  danger: '#e24b4a',
  dangerLight: '#f87171',
  success: '#10b981',
  successLight: '#34d399',
  textPrimary: '#0f172a',
  textSecondary: '#64748b',
  textMuted: '#94a3b8',
  gridColor: '#e2e8f0',
  tooltipBg: '#ffffff',
  tooltipBorder: '#e2e8f0',
  borderRadius: '16px',
  chartRadius: 6
};

const CHART_COLORS = ['#6c47ff','#00c2cb','#f59e0b','#e24b4a','#10b981','#9b7dff','#5eead4','#fbbf24'];

const KPI_GLOW_COLORS = ['#6c47ff', '#00c2cb', '#6c47ff', '#f59e0b', '#e24b4a'];

export const DataSpeakDashboard: React.FC<any> = ({ 
  mlData, 
  usingSampleData,
  templateName = "Manufacturing QC Dashboard",
  onBack,
  onRefresh,
  data: passedData,
  showPreviewTable = true,
  isDatabase = false,
  backText = ''
}) => {
  const { darkMode } = useTheme();
  const [selectedFilters, setSelectedFilters] = useState({});
  const [showRowsCount, setShowRowsCount] = useState(10);
  const [activeDropdownCol, setActiveDropdownCol] = useState(null);

  // Detect template type from templateName
  const templateType = useMemo(() => {
    const nameLower = templateName.toLowerCase();
    if (nameLower.includes('manufacturing') || nameLower.includes('qc')) return 'manufacturing';
    if (nameLower.includes('ecommerce') || nameLower.includes('sales')) return 'ecommerce';
    if (nameLower.includes('hr') || nameLower.includes('workforce') || nameLower.includes('employee')) return 'hr';
    if (nameLower.includes('finance') || nameLower.includes('financial') || nameLower.includes('p&l')) return 'financial';
    if (nameLower.includes('marketing') || nameLower.includes('campaign')) return 'marketing';
    if (nameLower.includes('supply') || nameLower.includes('logistic')) return 'supply_chain';
    return 'general';
  }, [templateName]);

  // Retrieve raw data rows
  const rawRows = useMemo(() => {
    if (passedData && passedData.length > 0) return passedData;
    if (mlData?.df_stats?.sample_rows && mlData.df_stats.sample_rows.length > 0) return mlData.df_stats.sample_rows;
    return [];
  }, [mlData, passedData]);

  // Extract filterable columns
  const filterCols = useMemo(() => {
    // If backend provided recommended filters (Phase 2E), use all of them dynamically
    if (mlData?.filters && Array.isArray(mlData.filters) && mlData.filters.length > 0) {
      return mlData.filters.map(f => (typeof f === 'string' ? f : f.column || f.name)).filter(Boolean);
    }
    if (!usingSampleData && mlData?.df_stats?.columns) {
      return mlData.df_stats.columns.filter(col => {
        const stats = mlData.df_stats.column_stats?.[col];
        return stats?.type === 'categorical' && 
               stats?.unique_count <= 50 &&
               stats?.unique_count >= 2;
      });
    }
    // Default sample filters
    if (templateType === 'manufacturing') return ['Factory', 'Shift', 'Year', 'Machine'];
    if (templateType === 'ecommerce') return ['Month', 'City', 'Status'];
    if (templateType === 'hr') return ['Department', 'Gender'];
    if (templateType === 'financial') return ['Quarter', 'Region'];
    if (templateType === 'marketing') return ['Channel', 'Campaign'];
    return ['Month', 'Status'];
  }, [mlData, usingSampleData, templateType]);

  // Get unique options for filter column
  const getFilterOptions = (col) => {
    const matchedFilter = mlData?.filters?.find(f => typeof f === 'object' && (f.column === col || f.name === col));
    if (matchedFilter && Array.isArray(matchedFilter.options) && matchedFilter.options.length > 0) {
      return matchedFilter.options.map(opt => typeof opt === 'object' ? (opt.value ?? opt.label) : opt);
    }
    const vals = rawRows.map(r => r[col]).filter(v => v !== undefined && v !== null);
    return Array.from(new Set(vals)).slice(0, 30);
  };

  // Filtered rows
  const filteredRows = useMemo(() => {
    return rawRows.filter(row => {
      for (const [col, val] of Object.entries(selectedFilters)) {
        if (val && String(row[col]) !== String(val)) return false;
      }
      return true;
    });
  }, [rawRows, selectedFilters]);

  // KPIs calculation — completely dynamic, displays ALL KPIs computed from data
  const kpis = useMemo(() => {
    if (!usingSampleData) {
      if (mlData?.key_metrics && mlData.key_metrics.length > 0) {
        return mlData.key_metrics.map(m => {
          const hasActiveFilters = Object.keys(selectedFilters).length > 0;
          let displayValue;
          if (hasActiveFilters && filteredRows.length > 0 && m.column) {
            const computed = calculateMetric(filteredRows, m.column, m.aggregation, m.label);
            displayValue = (computed !== null && computed !== undefined && !isNaN(computed))
              ? formatVal(computed, m.prefix, m.suffix)
              : (m.value || '—');
          } else {
            displayValue = m.value || formatVal(m.raw_value, m.prefix, m.suffix) || '—';
          }
          const trendDir = m.trend_direction || (m.trend_pct != null ? (m.trend_pct >= 0 ? 'up' : 'down') : null);
          const trendText = m.trend_pct != null
            ? `${m.trend_pct > 0 ? '+' : ''}${m.trend_pct.toFixed(1)}%${m.trend_text ? ` ${m.trend_text}` : ''}`
            : (m.trend_text || null);
          return {
            label: m.label,
            value: displayValue,
            trend: trendDir,
            trendText: trendText,
            color: m.icon_type === 'danger' ? '#e24b4a' : m.icon_type === 'success' ? '#10b981' : m.icon_type === 'warning' ? '#f59e0b' : '#6c47ff'
          };
        });
      }
      return []; // Honest empty state — no hardcoded fake fallback
    }
    return getSampleKPIs(templateType, filteredRows);
  }, [mlData, usingSampleData, templateType, filteredRows, selectedFilters]);

  // Charts Config & Data
  const charts = useMemo(() => {
    if (!usingSampleData) {
      if (mlData?.charts && mlData.charts.length > 0) {
        return mlData.charts.map((c, i) => {
          const color = c.color || CHART_COLORS[i % CHART_COLORS.length];
          const sampleRow = filteredRows[0] || rawRows[0];

          if (c.type === 'scatter') {
            const xKey = findColKey(sampleRow, c.x_column);
            const yKey = findColKey(sampleRow, c.y_column);

            const pairs = filteredRows
              .filter(r => r[xKey] != null && r[yKey] != null)
              .map(r => ({ x: Number(r[xKey]), y: Number(r[yKey]) }))
              .filter(p => !isNaN(p.x) && !isNaN(p.y));

            let sampled = pairs;
            if (pairs.length > 150) {
              const step = pairs.length / 150;
              sampled = [];
              for (let k = 0; k < 150; k++) {
                sampled.push(pairs[Math.floor(k * step)]);
              }
            }

            return {
              ...c,
              data: sampled,
              subtitle: `${pairs.length.toLocaleString()} points (${filteredRows.length.toLocaleString()} rows)`,
              color
            };
          }

          if (c.type === 'gauge') {
            const yKey = findColKey(sampleRow, c.y_column || c.column);
            const vals = filteredRows.map(r => Number(r[yKey])).filter(v => !isNaN(v));
            const avg = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
            return {
              ...c,
              data: [{ value: Number(avg.toFixed(2)) }],
              subtitle: `Avg ${c.y_column || ''} (${filteredRows.length.toLocaleString()} rows)`,
              color
            };
          }

          if (c.type === 'heatmap') {
            const cols = c.columns || [];
            if (cols.length < 2 || filteredRows.length === 0) {
              return { ...c, color };
            }
            const realCols = cols.map(col => findColKey(sampleRow, col));
            const heatData = [];
            realCols.forEach((c1, idx1) => {
              realCols.forEach((c2, idx2) => {
                let val = 1.0;
                if (c1 !== c2) {
                  const v1 = filteredRows.map(r => Number(r[c1]) || 0);
                  const v2 = filteredRows.map(r => Number(r[c2]) || 0);
                  const m1 = v1.reduce((a, b) => a + b, 0) / (v1.length || 1);
                  const m2 = v2.reduce((a, b) => a + b, 0) / (v2.length || 1);
                  const num = v1.reduce((s, a, idx) => s + (a - m1) * (v2[idx] - m2), 0);
                  const d1 = Math.sqrt(v1.reduce((s, a) => s + Math.pow(a - m1, 2), 0));
                  const d2 = Math.sqrt(v2.reduce((s, a) => s + Math.pow(a - m2, 2), 0));
                  val = (d1 && d2) ? num / (d1 * d2) : 0;
                }
                heatData.push({ x: cols[idx1] || c1, y: cols[idx2] || c2, value: Number(val.toFixed(2)) });
              });
            });
            return {
              ...c,
              data: heatData,
              subtitle: `Correlation (${filteredRows.length.toLocaleString()} rows)`,
              color
            };
          }

          // bar/line/area/donut
          const hasActiveFilters = Object.keys(selectedFilters).length > 0;
          let finalData;
          if (!hasActiveFilters && c.data && Array.isArray(c.data) && c.data.length > 0) {
            finalData = c.data;
          } else {
            finalData = computeChartData(filteredRows, c.x_column, c.y_column, c.aggregation, c.type);
          }
          return {
            ...c,
            data: finalData,
            subtitle: c.subtitle || `${c.aggregation || 'sum'} of ${c.y_column || ''} by ${c.x_column || ''}`,
            color
          };
        });
      }
      return []; // Honest empty state
    }
    return getSampleCharts(templateType, filteredRows);
  }, [mlData, usingSampleData, templateType, filteredRows, rawRows, selectedFilters]);

  // AI Insights
  const insights = useMemo(() => {
    if (!usingSampleData) {
      if (mlData?.ml_insights?.key_findings && mlData.ml_insights.key_findings.length > 0) {
        return mlData.ml_insights.key_findings;
      }
      if (mlData?.insights && Array.isArray(mlData.insights) && mlData.insights.length > 0) {
        return mlData.insights.map(item => typeof item === 'string' ? item : `${item.title ? item.title + ': ' : ''}${item.description || item.finding || ''}`);
      }
      if (mlData?.executive_summary?.strategic_insights && Array.isArray(mlData.executive_summary.strategic_insights)) {
        return mlData.executive_summary.strategic_insights.map(s => `${s.title}: ${s.finding}`);
      }
      return []; // Honest empty state
    }
    return getSampleInsights(templateType);
  }, [mlData, usingSampleData, templateType]);

  const handleFilterClick = (col, val) => {
    setSelectedFilters(prev => {
      const next = { ...prev };
      if (val === null) {
        delete next[col];
      } else {
        next[col] = val;
      }
      return next;
    });
    setActiveDropdownCol(null);
  };

  const handleResetFilters = () => {
    setSelectedFilters({});
    setActiveDropdownCol(null);
  };

  const handleDownloadChart = (chartIndex, chartTitle) => {
    const chartCard = document.getElementById(`chart-card-${chartIndex}`);
    if (!chartCard) return;

    const svgElement = chartCard.querySelector('svg');
    if (!svgElement) {
      alert("Chart graphic element not found for download.");
      return;
    }

    try {
      const svgString = new XMLSerializer().serializeToString(svgElement);
      const bounds = svgElement.getBoundingClientRect();
      const width = bounds.width || 400;
      const height = bounds.height || 250;

      const canvas = document.createElement('canvas');
      const scale = 2; // High-resolution export
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext('2d');

      // Background matches current theme
      ctx.fillStyle = darkMode ? '#0b0d19' : '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const img = new Image();
      const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);

      img.onload = () => {
        ctx.scale(scale, scale);
        ctx.drawImage(img, 0, 0, width, height);
        URL.revokeObjectURL(url);

        const pngUrl = canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.href = pngUrl;
        link.download = `${(chartTitle || 'chart').toLowerCase().replace(/[^a-z0-9]/g, '_')}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      };

      img.src = url;
    } catch (err) {
      console.error("Download chart error:", err);
    }
  };

  const handleDownloadDashboardPNG = async () => {
    const container = document.getElementById('full-dashboard-container');
    if (!container) return;

    try {
      // Hide buttons temporarily for clean capture
      const actionBtns = container.querySelectorAll('.status-pills button, .download-chart-btn, .filter-btn, .back-btn');
      actionBtns.forEach(btn => { btn.style.opacity = '0'; });

      const canvas = await html2canvas(container, {
        backgroundColor: darkMode ? '#06070f' : '#ffffff',
        scale: 2, // Crisp High-DPI export
        useCORS: true,
        logging: false,
        allowTaint: true
      });

      // Restore buttons
      actionBtns.forEach(btn => { btn.style.opacity = '1'; });

      const image = canvas.toDataURL('image/png');
      const link = document.createElement('a');
      link.href = image;
      link.download = `${(templateName || 'dashboard').toLowerCase().replace(/[^a-z0-9]/g, '_')}_screenshot.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err) {
      console.error("Dashboard screenshot error:", err);
      // Fallback to print
      window.print();
    }
  };

  // eslint-disable-next-line no-unused-vars
  const handleExportAllChartsZip = () => {
    charts.forEach((c, idx) => {
      setTimeout(() => {
        handleDownloadChart(idx, c.title);
      }, idx * 300);
    });
  };

  return (
    <div id="full-dashboard-container" style={{ background: 'var(--bg)', color: 'var(--text-primary)', minHeight: '100vh', fontFamily: "'Inter', 'Segoe UI', sans-serif", padding: '20px', transition: 'background-color 0.3s ease, color 0.3s ease' }}>
      {/* Dynamic CSS Styling Inject matching dashboard-scaled.html */}
      <style dangerouslySetInnerHTML={{ __html: `
        .glass {
          background: var(--card);
          border: 1px solid var(--border);
          backdrop-filter: blur(20px);
          border-radius: 16px;
          box-shadow: var(--shadow-card);
          transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .back-btn {
          background: var(--card);
          color: var(--text-secondary);
          border: 1px solid var(--border);
          border-radius: 10px;
          padding: 8px 14px;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          gap: 6px;
          box-shadow: var(--shadow-card);
          transition: all 0.2s ease;
          font-family: inherit;
        }
        .back-btn:hover {
          background: var(--hover-bg);
          color: var(--primary);
          border-color: var(--primary);
          transform: translateX(-2px);
        }
        .logo-badge {
          width: 42px; height: 42px; border-radius: 12px;
          background: linear-gradient(135deg,#6c47ff,#00c2cb);
          display: flex; align-items: center; justify-content: center;
          box-shadow: 0 8px 24px -6px rgba(108,71,255,0.5);
        }
        .h-title { font-size: 17px; font-weight: 700; margin: 0; color: var(--text-primary); }
        .h-sub { font-size: 12px; color: var(--text-secondary); margin: 2px 0 0; }
        .status-pills { display: flex; gap: 8px; flex-wrap: wrap; }
        .pill {
          font-size: 11px; font-weight: 600; padding: 6px 14px; border-radius: 999px;
          display: flex; align-items: center; gap: 6px;
        }
        .pill.success { background: rgba(16,185,129,0.12); color: #10B981; border: 1px solid rgba(16,185,129,0.25); }
        .pill.accent { background: rgba(108,71,255,0.12); color: var(--primary); border: 1px solid rgba(108,71,255,0.25); }
        
        .filters { display: flex; gap: 8px; align-items: center; margin-bottom: 24px; flex-wrap: wrap; }
        .filters-label { font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 6px; margin-right: 4px; }
        .filter-btn {
          font-size: 12px; padding: 7px 16px; border-radius: 10px; cursor: pointer;
          background: var(--card); color: var(--text-secondary); border: 1px solid var(--border);
          font-family: inherit; transition: all 0.15s;
          box-shadow: var(--shadow-card);
        }
        .filter-btn:hover {
          background: var(--hover-bg);
          border-color: var(--primary);
          color: var(--text-primary);
        }
        .filter-btn.active {
          background: rgba(108,71,255,0.12);
          color: var(--primary); border: 1px solid var(--primary);
          font-weight: 600;
        }
        .filter-dd-item {
          padding: 8px 12px; font-size: 12px; color: var(--text-primary); cursor: pointer;
          display: flex; justify-content: space-between; align-items: center; transition: background 0.15s;
        }
        .filter-dd-item:hover {
          background: var(--hover-bg);
        }

        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-bottom: 20px; }
        .kpi-card { padding: 20px; position: relative; overflow: hidden; }
        .kpi-glow {
          position: absolute; top: -30%; right: -20%; width: 140px; height: 140px; border-radius: 50%;
          filter: blur(40px); opacity: 0.18; pointer-events: none;
        }
        .kpi-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
        .kpi-icon {
          width: 34px; height: 34px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #fff;
        }
        .kpi-label { font-size: 11px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 600; }
        .kpi-value { font-size: 30px; font-weight: 700; letter-spacing: -0.01em; color: var(--text-primary); }
        .kpi-unit { font-size: 14px; color: var(--text-secondary); font-weight: 500; }
        .kpi-trend { font-size: 12px; margin-top: 8px; display: flex; align-items: center; gap: 4px; font-weight: 600; }

        .dynamic-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; margin-bottom: 14px; }
        .chart-card { padding: 20px; }
        .chart-card.span-2 { grid-column: span 2; }

        .gauge-wrap { display: flex; align-items: center; justify-content: center; padding: 10px 0 4px; }
        .gauge-value { font-size: 26px; font-weight: 700; }
        .gauge-caption { font-size: 11px; color: var(--text-secondary); text-align: center; margin-top: 4px; }

        .tree-grid { display: flex; flex-wrap: wrap; gap: 3px; height: 170px; }
        .tree-cell { border-radius: 8px; padding: 8px 10px; display: flex; flex-direction: column; justify-content: flex-end; min-width: 60px; overflow: hidden; }
        .tree-name { font-size: 10px; color: rgba(255,255,255,0.9); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; }
        .tree-pct { font-size: 13px; font-weight: 700; color: #fff; }

        .heat-table { width: 100%; border-collapse: separate; border-spacing: 3px; font-size: 10px; }
        .heat-table th { padding: 4px 6px; color: var(--text-secondary); font-weight: 600; text-align: center; text-transform: none; letter-spacing: 0; }
        .heat-table th:first-child { text-align: left; }
        .heat-cell { padding: 8px; text-align: center; border-radius: 6px; font-size: 10px; font-weight: 600; }
        .heat-row-label { padding: 4px 6px; color: var(--text-secondary); font-weight: 600; white-space: nowrap; }

        .chart-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
        .chart-icon-badge {
          width: 26px; height: 26px; border-radius: 8px; display: flex; align-items: center; justify-content: center; flex-shrink: 0;
        }
        .chart-title { font-size: 13px; font-weight: 700; color: var(--text-primary); }
        .chart-sub { font-size: 11px; color: var(--text-secondary); margin: 2px 0 12px 34px; }
        .legend-chip { font-size: 10px; color: var(--text-secondary); display: flex; align-items: center; gap: 5px; font-weight: 500; }
        .legend-dot { width: 8px; height: 8px; border-radius: 3px; display: inline-block; }

        .insight-card { padding: 20px; margin-bottom: 14px; }
        .insight-row { display: flex; gap: 12px; align-items: flex-start; padding: 10px 0; border-bottom: 1px solid var(--border); }
        .insight-row:last-child { border-bottom: none; padding-bottom: 0; }
        .insight-dot-wrap {
          width: 22px; height: 22px; border-radius: 7px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px;
        }
        .insight-text { font-size: 13px; color: var(--text-primary); line-height: 1.5; }

        .table-card { overflow: hidden; }
        .table-head { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
        .table-title { font-size: 13px; font-weight: 700; color: var(--text-primary); display: flex; align-items: center; gap: 8px; }
        .table-meta { font-size: 11px; color: var(--text-secondary); }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th { padding: 10px 20px; text-align: right; color: var(--text-secondary); font-weight: 600; font-size: 10px; text-transform: uppercase; letter-spacing: 0.04em; }
        th:first-child { text-align: left; }
        td { padding: 10px 20px; text-align: right; color: var(--text-primary); }
        td:first-child { text-align: left; font-weight: 700; color: var(--primary); }
        tbody tr { border-bottom: 1px solid var(--border); }
        tbody tr:hover { background: var(--hover-bg); }
        .total-row td { font-weight: 700; color: var(--text-primary); border-top: 2px solid var(--border); }
        .total-row td:first-child { color: var(--text-primary); }
        @media (max-width: 960px) {
          .chart-card.span-2 { grid-column: span 1; }
          .dynamic-grid { grid-template-columns: 1fr; }
          .kpi-grid { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
        }

        @media print {
          body { background: var(--bg) !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
          .status-pills button, .filters, .download-chart-btn, .filter-btn, .back-btn, nav, [class*="sidebar"], [id*="sidebar"] { display: none !important; }
          #full-dashboard-container { position: absolute !important; left: 0 !important; top: 0 !important; width: 100% !important; z-index: 99999 !important; background: var(--bg) !important; }
          .header, .glass, .chart-card, .table-card { break-inside: avoid; page-break-inside: avoid; }
        }
      ` }} />

      <div style={{ maxWidth: '1440px', margin: '0 auto', width: '100%' }}>
        
        {/* SECTION 1: HEADER */}
        <div className="header">
          <div className="header-left">
            {onBack && (
              <button
                onClick={onBack}
                className="back-btn"
                title={backText || (isDatabase ? "Back to Databases" : "Back to Datasets")}
              >
                <ArrowLeft size={14} /> {backText || (isDatabase ? "Back to Databases" : "Back to Datasets")}
              </button>
            )}
            <div className="logo-badge"><BarChart2 size={20} color="#fff" /></div>
            <div>
              <p className="h-title">DataSpeakAI</p>
              <p className="h-sub">{templateName}</p>
            </div>
          </div>
          <div className="status-pills">
            <span className="pill success"><CheckCircle size={12} /> {(mlData?.df_stats?.total_rows || filteredRows.length).toLocaleString()} {isDatabase ? "records analyzed" : "rows loaded"}</span>
            {isDatabase ? (
              <span className="pill accent"><Database size={12} /> Deterministic Pipeline (Phase 2C)</span>
            ) : mlData?.automl_results?.best_model?.model ? (() => {
              const best = mlData.automl_results.best_model;
              const metricName = best.metric || (mlData.automl_results.problem_type === 'regression' ? 'R² Score' : mlData.automl_results.problem_type === 'clustering' ? 'Silhouette' : 'Accuracy');
              let scoreText = 'N/A';
              if (typeof best.score === 'number') {
                if (metricName === 'R² Score' || best.r2_score !== undefined) {
                  scoreText = `R²: ${best.score.toFixed(2)}`;
                } else if (metricName === 'Silhouette' || best.silhouette_score !== undefined) {
                  scoreText = `Silhouette: ${best.score.toFixed(2)}`;
                } else {
                  scoreText = `${(best.score * 100).toFixed(1)}%`;
                }
              }
              const tooltipTitle = best.f1_score !== undefined
                ? `Holdout Test Accuracy: ${(best.score * 100).toFixed(1)}% | Weighted F1: ${(best.f1_score * 100).toFixed(1)}%`
                : best.mae !== undefined
                ? `Holdout Test R²: ${best.score?.toFixed(2)} | MAE: ${best.mae}`
                : undefined;
              return (
                <span className="pill accent" title={tooltipTitle}>
                  <Brain size={12} /> {best.model} · {scoreText}
                  {best.f1_score !== undefined && (
                    <span style={{ opacity: 0.85, marginLeft: '4px' }}>
                      (F1: {(best.f1_score * 100).toFixed(1)}%)
                    </span>
                  )}
                </span>
              );
            })() : null}
            {mlData?.automl_results?.class_imbalance_detected && (
              <span
                className="pill warning"
                style={{ background: 'rgba(239,68,68,0.15)', color: '#f87171', border: '1px solid rgba(239,68,68,0.3)' }}
                title={mlData.automl_results.class_imbalance_warning || `Severe class imbalance detected (>85% majority). Baseline: ${mlData.automl_results.majority_baseline ? (mlData.automl_results.majority_baseline * 100).toFixed(1) + '%' : 'N/A'}`}
              >
                <AlertTriangle size={12} /> Class Imbalance ({mlData.automl_results.majority_baseline ? `Baseline ${(mlData.automl_results.majority_baseline * 100).toFixed(0)}%` : 'Warning'})
              </span>
            )}
            {mlData?.automl_results?.insufficient_data && (
              <span
                className="pill"
                style={{ background: 'rgba(148,163,184,0.15)', color: '#94a3b8', border: '1px solid rgba(148,163,184,0.3)' }}
                title="Dataset has fewer than 20 rows. Model training omitted to prevent false confidence."
              >
                <AlertTriangle size={12} /> Small Dataset (&lt;20 rows)
              </span>
            )}
            <span className="pill" style={{ background: 'rgba(245,158,11,0.12)', color: '#FBBF24', border: '1px solid rgba(245,158,11,0.3)' }}><Sparkles size={12} /> AI selected {charts.length} charts</span>
            {onRefresh && (
              <button
                onClick={onRefresh}
                title="Re-run AI analysis with fresh data"
                style={{ background: 'rgba(108,71,255,0.12)', color: '#9b7dff', border: '1px solid rgba(108,71,255,0.3)', borderRadius: '999px', padding: '6px 14px', fontSize: '11px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '5px', fontFamily: 'inherit' }}
              >
                <RefreshCw size={11} /> Re-run Analysis
              </button>
            )}
            <button
              onClick={handleDownloadDashboardPNG}
              title="Download full dashboard screenshot as PNG image"
              style={{
                background: 'linear-gradient(135deg, #6c47ff, #00c2cb)',
                color: '#fff',
                border: 'none',
                borderRadius: '999px',
                padding: '6px 14px',
                fontSize: '11px',
                fontWeight: 700,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                fontFamily: 'inherit',
                boxShadow: '0 4px 12px rgba(108,71,255,0.3)',
                transition: 'all 0.2s ease'
              }}
            >
              <Download size={12} /> Download Dashboard
            </button>
          </div>
        </div>

        {/* SECTION 2: FILTER BAR */}
        {filterCols.length > 0 && (
          <div className="filters">
            <span className="filters-label"><Filter size={12} /> Filters</span>
            {filterCols.map(col => {
              const selectedVal = selectedFilters[col];
              const isOpen = activeDropdownCol === col;
              return (
                <div key={col} style={{ position: 'relative' }}>
                  <button
                    onClick={() => setActiveDropdownCol(isOpen ? null : col)}
                    className={`filter-btn ${selectedVal ? 'active' : ''}`}
                  >
                    {col} · {selectedVal || 'All'}
                  </button>
                  <AnimatePresence>
                    {isOpen && (
                      <motion.div
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 4 }}
                        style={{
                          position: 'absolute', top: '100%', left: 0, marginTop: '6px',
                          background: 'var(--card-elevated, var(--card))', border: '1px solid var(--border)',
                          borderRadius: '10px', boxShadow: 'var(--shadow-lg)',
                          zIndex: 999, width: '180px', maxHeight: '200px', overflowY: 'auto', padding: '6px 0'
                        }}
                      >
                        <div
                          onClick={() => handleFilterClick(col, null)}
                          className="filter-dd-item"
                        >
                          All
                          {!selectedVal && <Check size={12} color="#00c2cb" />}
                        </div>
                        {getFilterOptions(col).map(val => (
                          <div
                            key={val}
                            onClick={() => handleFilterClick(col, val)}
                            className="filter-dd-item"
                          >
                            {val}
                            {String(selectedVal) === String(val) && <Check size={12} color="#00c2cb" />}
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
            <div style={{ marginLeft: 'auto' }}>
              <button className="filter-btn" onClick={handleResetFilters}>
                <RefreshCw size={11} style={{ marginRight: '4px', verticalAlign: 'middle' }} /> Reset
              </button>
            </div>
          </div>
        )}

        {/* SECTION 3: KPI CARDS */}
        {kpis.length > 0 ? (
          <div className="kpi-grid">
            {kpis.map((k, idx) => {
              const glowColor = KPI_GLOW_COLORS[idx % KPI_GLOW_COLORS.length];
              const isUp = k.trend === 'up' || k.trend === 'positive';
              const isDown = k.trend === 'down' || k.trend === 'negative';
              const splitVal = String(k.value).split(/(?=[a-zA-Z%]+)/);
              const valueNumber = splitVal[0] || '';
              const valueUnit = splitVal.slice(1).join('') || '';

              return (
                <div className="glass kpi-card" key={idx}>
                  <div className="kpi-glow" style={{ background: glowColor }} />
                  <div className="kpi-top">
                    <span className="kpi-label">{k.label}</span>
                    <div className="kpi-icon" style={{ background: `linear-gradient(135deg, ${glowColor}, ${glowColor}cc)` }}>
                      <Activity size={16} />
                    </div>
                  </div>
                  <div className="kpi-value">
                    {valueNumber}
                    {valueUnit && <span className="kpi-unit">{valueUnit}</span>}
                  </div>
                  {k.trendText ? (
                    <div
                      className="kpi-trend"
                      style={{ color: isUp ? '#10b981' : isDown ? '#ef4444' : '#f59e0b' }}
                    >
                      {isUp ? <TrendingUp size={12} /> : isDown ? <TrendingDown size={12} /> : <Minus size={12} />}
                      {k.trendText}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="glass" style={{ padding: '20px', textAlign: 'center', color: '#64748B', fontSize: '13px', marginBottom: '14px', borderRadius: '16px' }}>
            Not enough numeric data found to generate KPI metrics.
          </div>
        )}

        {/* SECTION 4: CHARTS GRID */}
        {charts.length > 0 && charts.length <= 2 && (
          <div style={{ fontSize: '12px', color: '#64748B', marginBottom: '10px', padding: '0 4px' }}>
            Showing all available charts generated for this dataset structure.
          </div>
        )}
        {charts.length > 0 ? (
          <div className="dynamic-grid">
            {charts.map((c, i) => {
              const color = c.color || CHART_COLORS[i % CHART_COLORS.length];
              const Icon = getChartIcon(c.type);
              const isSpan2 = c.type === 'heatmap';

              return (
                <div key={i} id={`chart-card-${i}`} className={`glass chart-card ${isSpan2 ? 'span-2' : ''}`}>
                  <div className="chart-head">
                    <div className="chart-icon-badge" style={{ background: `linear-gradient(135deg, ${color}, ${color}cc)` }}>
                      <Icon size={13} color="#fff" />
                    </div>
                    <span className="chart-title">{c.title}</span>
                  </div>
                  <div className="chart-sub">{c.subtitle || `${c.y_column} by ${c.x_column}`}</div>
                  <div style={{ position: 'relative', height: isSpan2 ? '280px' : '240px' }}>
                    {renderRecharts(c, color, filteredRows)}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="glass" style={{ padding: '24px', textAlign: 'center', color: '#64748B', fontSize: '13px', marginBottom: '14px', borderRadius: '16px' }}>
            No visual charts planned for this dataset layout.
          </div>
        )}

        {/* SECTION 5: AI INSIGHTS */}
        <div className="glass insight-card">
          <div className="chart-head" style={{ marginBottom: '8px' }}>
            <div className="chart-icon-badge" style={{ background: 'linear-gradient(135deg, #6c47ff, #00c2cb)' }}>
              <Sparkles size={13} color="#fff" />
            </div>
            <span className="chart-title">AI insights</span>
          </div>

          {insights.length > 0 ? (
            insights.map((ins, idx) => {
              const rowColor = CHART_COLORS[idx % CHART_COLORS.length];
              const RotateIcon = [AlertTriangle, Moon, TrendingUp][idx % 3];

              return (
                <div className="insight-row" key={idx}>
                  <div className="insight-dot-wrap" style={{ background: `${rowColor}26` }}>
                    <RotateIcon size={11} color={rowColor} />
                  </div>
                  <div className="insight-text">{ins}</div>
                </div>
              );
            })
          ) : (
            <div style={{ color: '#64748B', fontSize: '13px', padding: '12px 0' }}>
              No specific AI insights generated for this dataset yet.
            </div>
          )}
        </div>

        {/* SECTION 6: DATA PREVIEW TABLE (Hidden when showPreviewTable is false) */}
        {showPreviewTable && (
          <div className="glass table-card">
            <div className="table-head">
              <span className="table-title">
                <Database size={14} color="#64748B" style={{ verticalAlign: 'middle', marginRight: '6px' }} />
                {templateType === 'manufacturing' ? 'Machine × defect type cross-tab' : 'Data Preview'}
              </span>
              <span className="table-meta">
                {filteredRows.length.toLocaleString()} total rows · {Object.keys(rawRows[0] || {}).length} columns
              </span>
            </div>
            {rawRows.length > 0 ? (
              <>
                <div style={{ overflowX: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(rawRows[0] || {}).map((col, idx) => (
                          <th key={col} style={{ textAlign: idx === 0 ? 'left' : 'right' }}>{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredRows.slice(0, showRowsCount).map((row, idx) => (
                        <tr key={idx}>
                          {Object.keys(row).map((col, cIdx) => (
                            <td key={col} style={{ textAlign: cIdx === 0 ? 'left' : 'right' }}>
                              {typeof row[col] === 'number' ? row[col].toLocaleString() : String(row[col])}
                            </td>
                          ))}
                        </tr>
                      ))}
                      {/* Dynamic Totals Row for Cross-Tab or Data representation */}
                      <tr className="total-row">
                        <td>Total</td>
                        {Object.keys(rawRows[0] || {}).slice(1).map(col => {
                          const totalSum = filteredRows.reduce((acc, r) => acc + (parseFloat(r[col]) || 0), 0);
                          return <td key={col}>{totalSum.toLocaleString()}</td>;
                        })}
                      </tr>
                    </tbody>
                  </table>
                </div>

                {filteredRows.length > showRowsCount && (
                  <div style={{ textAlign: 'center', padding: '14px 20px' }}>
                    <button
                      className="filter-btn"
                      onClick={() => setShowRowsCount(prev => prev + 15)}
                    >
                      Show More Rows
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div style={{ padding: '24px', textAlign: 'center', color: '#64748B', fontSize: '13px' }}>
                No preview data available for this dataset.
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
};

const getChartIcon = (type) => {
  switch (type) {
    case 'bar':
    case 'horizontal_bar':
      return BarChart2;
    case 'line':
    case 'area':
      return TrendingUp;
    case 'donut':
    case 'pie':
      return PieChartIcon;
    case 'scatter':
      return Activity;
    case 'treemap':
      return LayoutGrid;
    case 'heatmap':
      return Grid;
    default:
      return Activity;
  }
};

const renderRecharts = (c, color, filteredRows = []) => {
  const data = c.data || [];

  if (data.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748B', fontSize: '11px' }}>
        No data matches the selected filters
      </div>
    );
  }

  const xColName = (c.x_column || c.x_field || (c.type === 'line' || c.type === 'area' ? 'Timeline / Period' : 'Dimension')).replace(/_/g, ' ');
  const yColName = (c.y_column || c.y_field || c.metric_col || 'Metric Value').replace(/_/g, ' ');

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: 'var(--tooltip-bg, var(--card))',
          border: '1px solid var(--border)',
          borderRadius: '10px', padding: '10px 14px',
          boxShadow: 'var(--shadow-md)',
          minWidth: '150px'
        }}>
          <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '11px', fontWeight: 600 }}>
            {xColName}: <span style={{ color: 'var(--text-primary)', fontWeight: 700 }}>{label}</span>
          </p>
          {payload.map((p, idx) => (
            <p key={idx} style={{ color: p.color || color, margin: '4px 0 0 0', fontSize: '12px', fontWeight: 700 }}>
              {yColName}: {typeof p.value === 'number' ? (p.value >= 1000 ? p.value.toLocaleString() : p.value.toFixed(2)) : p.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  switch (c.type) {
    case 'line':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 15, right: 20, left: 15, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, var(--border))" opacity={0.6} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10.5, fill: 'var(--chart-text, #64748B)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              label={{ value: xColName, position: 'insideBottom', offset: -16, fill: 'var(--text-secondary)', fontSize: 10.5, fontWeight: 700 }}
            />
            <YAxis
              tickFormatter={v => formatVal(v)}
              width={52}
              tick={{ fontSize: 10.5, fill: 'var(--chart-text, #64748B)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              label={{ value: yColName, angle: -90, position: 'insideLeft', offset: -4, fill: 'var(--text-secondary)', fontSize: 10.5, fontWeight: 700, style: { textAnchor: 'middle' } }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} dot={{ r: 3, fill: color }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      );

    case 'area':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 15, right: 20, left: 15, bottom: 25 }}>
            <defs>
              <linearGradient id={`grad-${c.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, var(--border))" opacity={0.6} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10.5, fill: 'var(--chart-text, #64748B)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              label={{ value: xColName, position: 'insideBottom', offset: -16, fill: 'var(--text-secondary)', fontSize: 10.5, fontWeight: 700 }}
            />
            <YAxis
              tickFormatter={v => formatVal(v)}
              width={52}
              tick={{ fontSize: 10.5, fill: 'var(--chart-text, #64748B)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              label={{ value: yColName, angle: -90, position: 'insideLeft', offset: -4, fill: 'var(--text-secondary)', fontSize: 10.5, fontWeight: 700, style: { textAnchor: 'middle' } }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="value" stroke={color} strokeWidth={2.5} fillOpacity={1} fill={`url(#grad-${c.id})`} dot={{ r: 3, fill: color }} activeDot={{ r: 6 }} />
          </AreaChart>
        </ResponsiveContainer>
      );

    case 'horizontal_bar':
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 15, right: 20, left: 15, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, var(--border))" opacity={0.6} />
            <XAxis
              type="number"
              tickFormatter={v => formatVal(v)}
              tick={{ fontSize: 10.5, fill: 'var(--chart-text, #64748B)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              label={{ value: yColName, position: 'insideBottom', offset: -16, fill: 'var(--text-secondary)', fontSize: 10.5, fontWeight: 700 }}
            />
            <YAxis
              dataKey="name"
              type="category"
              tick={{ fontSize: 10.5, fill: 'var(--chart-text, #64748B)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              width={85}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" fill={color} radius={[0, 6, 6, 0]} barSize={14} />
          </BarChart>
        </ResponsiveContainer>
      );

    case 'donut':
    case 'pie':
      return (
        <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ height: '120px', width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius="70%"
                  outerRadius="90%"
                  paddingAngle={3}
                  dataKey="value"
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div style={{
            display: 'flex', flexWrap: 'wrap', gap: '6px 12px', justifyContent: 'center',
            marginTop: '8px', maxHeight: '45px', overflowY: 'auto'
          }}>
            {data.slice(0, 4).map((entry, index) => {
              const total = data.reduce((sum, d) => sum + (d.value || 0), 0);
              const pct = total > 0 ? ((entry.value / total) * 100).toFixed(1) : '0';
              return (
                <span className="legend-chip" key={index}>
                  <span className="legend-dot" style={{ background: CHART_COLORS[index % CHART_COLORS.length] }}></span>
                  {entry.name} {pct}%
                </span>
              );
            })}
          </div>
        </div>
      );

    case 'scatter': {
      const formattedScatterData = data.map(d => ({
        x: d.x !== undefined ? d.x : (typeof d.name === 'number' ? d.name : parseFloat(d.name) || 0),
        y: d.y !== undefined ? d.y : (typeof d.value === 'number' ? d.value : parseFloat(d.value) || 0),
        label: d.name || `${c.x_column || 'X'}: ${d.x}, ${c.y_column || 'Y'}: ${d.y}`
      }));

      const ScatterTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
          const pt = payload[0].payload;
          return (
            <div style={{
              backgroundColor: 'var(--tooltip-bg, var(--card))',
              border: '1px solid var(--border)',
              borderRadius: '10px', padding: '8px 12px',
              boxShadow: 'var(--shadow-md)'
            }}>
              <p style={{ color: 'var(--text-primary)', margin: 0, fontWeight: 700, fontSize: '11px' }}>
                {pt.label || `${c.x_column || 'X'}: ${pt.x}, ${c.y_column || 'Y'}: ${pt.y}`}
              </p>
              <p style={{ color: 'var(--text-secondary)', margin: '3px 0 0 0', fontSize: '11px', fontWeight: 600 }}>
                {c.x_column || 'X'}: {typeof pt.x === 'number' ? pt.x.toLocaleString() : pt.x}
              </p>
              <p style={{ color: color, margin: '3px 0 0 0', fontSize: '11px', fontWeight: 600 }}>
                {c.y_column || 'Y'}: {typeof pt.y === 'number' ? pt.y.toLocaleString() : pt.y}
              </p>
            </div>
          );
        }
        return null;
      };

      return (
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart key={`scatter-${formattedScatterData.length}-${data.length}`} margin={{ top: 10, right: 15, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, var(--border))" />
            <XAxis type="number" dataKey="x" name={c.x_column || "X"} tick={{ fontSize: 10, fill: 'var(--chart-text, #64748B)' }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
            <YAxis type="number" dataKey="y" name={c.y_column || "Y"} tick={{ fontSize: 10, fill: 'var(--chart-text, #64748B)' }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
            <Tooltip content={<ScatterTooltip />} />
            <Scatter data={formattedScatterData} fill={color} shape="circle" opacity={0.75} />
          </ScatterChart>
        </ResponsiveContainer>
      );
    }

    case 'gauge': {
      const val = data[0]?.value || 0;
      const target = 100;
      const pct = Math.min(Math.max((val / target) * 100, 0), 100);

      return (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <div className="gauge-wrap">
            <svg width="180" height="100" viewBox="0 0 180 100">
              <path d="M 20 90 A 70 70 0 0 1 160 90" fill="none" stroke="var(--border)" strokeWidth="14" strokeLinecap="round"/>
              <path
                d="M 20 90 A 70 70 0 0 1 160 90"
                fill="none"
                stroke={color}
                strokeWidth="14"
                strokeLinecap="round"
                strokeDasharray="220"
                strokeDashoffset={220 - (220 * pct * 0.5) / 100}
                style={{ transition: 'stroke-dashoffset 0.6s ease' }}
              />
            </svg>
          </div>
          <div className="gauge-value" style={{ textAlign: 'center', color: '#00c2cb', marginTop: '-35px' }}>{val.toFixed(1)}%</div>
          <div className="gauge-caption" style={{ color: 'var(--text-secondary)' }}>Target: 80% · Industry avg: 68%</div>
        </div>
      );
    }

    case 'treemap': {
      const total = data.reduce((sum, d) => sum + (d.value || 0), 0);
      return (
        <div className="tree-grid">
          {data.slice(0, 5).map((item, idx) => {
            const widthPct = total > 0 ? Math.max((item.value / total) * 100, 10) : 20;
            return (
              <div
                key={idx}
                className="tree-cell"
                style={{
                  background: CHART_COLORS[idx % CHART_COLORS.length],
                  width: `${widthPct - 2}%`
                }}
              >
                <div className="tree-name">{item.name}</div>
                <div className="tree-pct">{((item.value / (total || 1)) * 100).toFixed(0)}%</div>
              </div>
            );
          })}
        </div>
      );
    }

    case 'heatmap': {
      let columns = c.columns || [];
      let heatData = c.data || [];

      // If columns or heatData is missing but filteredRows exist, compute correlation dynamically
      if ((columns.length === 0 || heatData.length === 0) && filteredRows && filteredRows.length > 0) {
        const sampleRow = filteredRows[0];
        const numericCols = Object.keys(sampleRow).filter(k => typeof sampleRow[k] === 'number' && !isNaN(sampleRow[k])).slice(0, 6);
        if (numericCols.length >= 2) {
          columns = numericCols;
          heatData = [];
          numericCols.forEach(c1 => {
            numericCols.forEach(c2 => {
              let val = 1.0;
              if (c1 !== c2) {
                const vals1 = filteredRows.map(r => Number(r[c1]) || 0);
                const vals2 = filteredRows.map(r => Number(r[c2]) || 0);
                const mean1 = vals1.reduce((a, b) => a + b, 0) / (vals1.length || 1);
                const mean2 = vals2.reduce((a, b) => a + b, 0) / (vals2.length || 1);
                const num = vals1.reduce((sum, v1, idx) => sum + (v1 - mean1) * (vals2[idx] - mean2), 0);
                const den1 = Math.sqrt(vals1.reduce((sum, v1) => sum + Math.pow(v1 - mean1, 2), 0));
                const den2 = Math.sqrt(vals2.reduce((sum, v2) => sum + Math.pow(v2 - mean2, 2), 0));
                val = (den1 && den2) ? num / (den1 * den2) : 0;
              }
              heatData.push({ x: c1, y: c2, value: Number(val.toFixed(2)) });
            });
          });
        }
      }

      if (columns.length === 0 || heatData.length === 0) {
        return (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)', fontSize: '11px' }}>
            No correlation data available
          </div>
        );
      }

      // Build a lookup: value at (row, col)
      const valueMap = {};
      heatData.forEach(d => {
        valueMap[`${d.x}|${d.y}`] = d.value;
      });

      return (
        <table className="heat-table" style={{ width: '100%', height: '100%' }}>
          <thead>
            <tr>
              <th></th>
              {columns.map(h => <th key={h}>{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {columns.map((rowCol, idx) => (
              <tr key={idx}>
                <td className="heat-row-label">{rowCol}</td>
                {columns.map((colCol, vIdx) => {
                  const v = valueMap[`${rowCol}|${colCol}`] ?? 0;
                  const alpha = Math.abs(v) * 0.85;
                  const bg = `rgba(108,71,255,${alpha})`;
                  const textColor = alpha > 0.45 ? '#fff' : 'var(--text-secondary)';
                  return (
                    <td key={vIdx} className="heat-cell" style={{ background: bg, color: textColor }}>
                      {typeof v === 'number' ? v.toFixed(2) : v}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    case 'bar':
    default:
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 15, right: 20, left: 15, bottom: 25 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, var(--border))" opacity={0.6} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10.5, fill: 'var(--chart-text, #64748B)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              label={{ value: xColName, position: 'insideBottom', offset: -16, fill: 'var(--text-secondary)', fontSize: 10.5, fontWeight: 700 }}
            />
            <YAxis
              tickFormatter={v => formatVal(v)}
              width={52}
              tick={{ fontSize: 10.5, fill: 'var(--chart-text, #64748B)' }}
              axisLine={{ stroke: 'var(--border)' }}
              tickLine={false}
              label={{ value: yColName, angle: -90, position: 'insideLeft', offset: -4, fill: 'var(--text-secondary)', fontSize: 10.5, fontWeight: 700, style: { textAnchor: 'middle' } }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="value" fill={color} radius={[6, 6, 0, 0]} barSize={16} />
          </BarChart>
        </ResponsiveContainer>
      );
  }
};

const findColKey = (row, targetCol) => {
  if (!row || !targetCol) return targetCol;
  if (targetCol in row) return targetCol;
  const norm = targetCol.toLowerCase().replace(/[^a-z0-9]/g, '');
  const found = Object.keys(row).find(k => k.toLowerCase().replace(/[^a-z0-9]/g, '') === norm);
  return found || targetCol;
};

const calculateMetric = (rows, column, aggregation, label = '') => {
  if (!rows || rows.length === 0 || !column) return 0;
  const colKey = findColKey(rows[0], column);
  const values = rows.map(r => parseFloat(r[colKey])).filter(v => !isNaN(v));
  if (values.length === 0) return 0;

  let agg = aggregation?.toLowerCase();
  const colLower = String(column).toLowerCase();
  const labelLower = String(label).toLowerCase();
  
  if (!agg || agg === 'sum') {
    if (['age', 'rating', 'score', 'tenure', 'temp', 'prob', 'ratio', 'rate', 'pct', 'percent', 'satisfaction'].some(kw => colLower.includes(kw)) ||
        ['avg', 'average', 'mean', 'rate', 'ratio', 'score', 'rating'].some(kw => labelLower.includes(kw))) {
      agg = 'avg';
    }
  }

  switch (agg) {
    case 'sum':
      return values.reduce((sum, v) => sum + v, 0);
    case 'avg':
    case 'average':
    case 'mean':
      return values.reduce((sum, v) => sum + v, 0) / values.length;
    case 'count':
      return rows.length;
    case 'min':
      return Math.min(...values);
    case 'max':
      return Math.max(...values);
    default:
      return values.reduce((sum, v) => sum + v, 0);
  }
};

const formatVal = (val, prefix = '', suffix = '') => {
  if (typeof val !== 'number' || isNaN(val)) return String(val || '—');
  const abs = Math.abs(val);
  if (abs >= 1e9) return `${prefix}${(val / 1e9).toFixed(1)}B${suffix}`;
  if (abs >= 1e6) return `${prefix}${(val / 1e6).toFixed(1)}M${suffix}`;
  if (abs >= 1e3 && (prefix || abs >= 10000)) return `${prefix}${(val / 1e3).toFixed(1)}K${suffix}`;
  return Number.isInteger(val) ? `${prefix}${val}${suffix}` : `${prefix}${val.toFixed(1)}${suffix}`;
};

const computeChartData = (rows, xCol, yCol, agg, type) => {
  if (!rows || rows.length === 0 || !xCol) return [];

  const realXCol = findColKey(rows[0], xCol);
  const groups = {};
  rows.forEach(r => {
    const key = String(r[realXCol] || 'Unknown');
    if (!groups[key]) groups[key] = [];
    groups[key].push(r);
  });

  const chartData = Object.entries(groups).map(([name, groupRows]) => {
    const val = calculateMetric(groupRows, yCol, agg);
    return { name, value: val };
  });

  return chartData.slice(0, 10);
};

// ─── SAMPLE DATA GENERATOR FUNCTIONS ─────────────────────────────────────────

// eslint-disable-next-line no-unused-vars
const getSampleDataRows = (type) => {
  if (type === 'manufacturing') {
    return [
      { Machine: 'M-101', Assembly: 3391, Dimensional: 3280, Material: 3528, Surface: 3332, Total: 13531 },
      { Machine: 'M-102', Assembly: 4196, Dimensional: 4481, Material: 5127, Surface: 4808, Total: 18612 },
      { Machine: 'M-103', Assembly: 12740, Dimensional: 12218, Material: 11027, Surface: 11264, Total: 47249 },
      { Machine: 'M-104', Assembly: 3571, Dimensional: 3905, Material: 3783, Surface: 4377, Total: 15636 },
      { Machine: 'M-105', Assembly: 2299, Dimensional: 2795, Material: 2575, Surface: 2284, Total: 9953 }
    ];
  }
  return [
    { Month: 'Jan', Assembly: 1200, Dimensional: 3280, Material: 1528, Surface: 2332, Total: 8340 },
    { Month: 'Feb', Assembly: 1500, Dimensional: 4481, Material: 1827, Surface: 2808, Total: 10616 },
    { Month: 'Mar', Assembly: 1800, Dimensional: 12218, Material: 2102, Surface: 3264, Total: 19384 }
  ];
};

const getSampleKPIs = (type, rows) => {
  if (rows && rows.length > 0) {
    const sampleRow = rows[0];
    const numericCols = Object.keys(sampleRow).filter(
      k => typeof sampleRow[k] === 'number' && !isNaN(sampleRow[k])
    );
    if (numericCols.length > 0) {
      return numericCols.slice(0, 5).map((col, idx) => {
        const sum = rows.reduce((acc, r) => acc + (Number(r[col]) || 0), 0);
        return {
          label: col.replace(/_/g, ' ').toUpperCase(),
          value: formatVal(sum),
          trend: 'flat',
          trendText: 'Dataset total',
          color: CHART_COLORS[idx % CHART_COLORS.length]
        };
      });
    }
  }

  if (type === 'manufacturing') {
    return [
      { label: 'Defect rate', value: '7.82%', trend: 'up', trendText: '0.3% vs last month', color: '#6c47ff' },
      { label: 'Efficiency', value: '82.96%', trend: 'up', trendText: '2.1% vs last month', color: '#00c2cb' },
      { label: 'Total units', value: '1.0M', trend: 'up', trendText: '12K vs last month', color: '#6c47ff' },
      { label: 'Downtime', value: '167K min', trend: 'neutral', trendText: 'No change', color: '#f59e0b' },
      { label: 'Scrap cost', value: '52.5M', trend: 'up', trendText: '1.2M vs last month', color: '#e24b4a' }
    ];
  }

  return [];
};

const getSampleCharts = (type, rows) => {
  if (rows && rows.length > 0 && type !== 'manufacturing') {
    return [
      {
        id: 'c1', title: 'Defect rate by machine', type: 'bar',
        x_column: 'Machine', y_column: 'Total', aggregation: 'sum',
        subtitle: 'M-103 is the clear outlier at 17.2K',
        color: '#6c47ff',
        data: [
          { name: 'M-103', value: 17200 },
          { name: 'M-102', value: 7100 },
          { name: 'M-104', value: 5800 },
          { name: 'M-101', value: 5000 },
          { name: 'M-105', value: 3700 }
        ]
      },
      {
        id: 'c2', title: 'Defect type breakdown', type: 'donut',
        x_column: 'Type', y_column: 'Defects', aggregation: 'sum',
        subtitle: '4 near-equal segments',
        color: '#00c2cb',
        data: [
          { name: 'Dimensional', value: 26679 },
          { name: 'Assembly', value: 26197 },
          { name: 'Surface', value: 26065 },
          { name: 'Material', value: 26040 }
        ]
      },
      {
        id: 'c3', title: 'Monthly production trend', type: 'area',
        x_column: 'Month', y_column: 'Production', aggregation: 'sum',
        subtitle: 'Seasonal peak in June, dip in April',
        color: '#f59e0b',
        data: [
          { name: 'Jan', value: 52000 },
          { name: 'Feb', value: 48000 },
          { name: 'Mar', value: 55000 },
          { name: 'Apr', value: 43000 },
          { name: 'May', value: 58000 },
          { name: 'Jun', value: 61000 },
          { name: 'Jul', value: 57000 },
          { name: 'Aug', value: 50000 },
          { name: 'Sep', value: 54000 },
          { name: 'Oct', value: 49000 },
          { name: 'Nov', value: 53000 },
          { name: 'Dec', value: 46000 }
        ]
      },
      {
        id: 'c4', title: 'Downtime by shift', type: 'bar',
        x_column: 'Shift', y_column: 'Downtime', aggregation: 'sum',
        subtitle: 'Night shift nearly 2× evening, 3× morning',
        color: '#e24b4a',
        data: [
          { name: 'Night', value: 91000 },
          { name: 'Evening', value: 48000 },
          { name: 'Morning', value: 28000 }
        ]
      },
      {
        id: 'c5', title: 'Temperature vs defect rate', type: 'scatter',
        x_column: 'Temp', y_column: 'Defects', aggregation: 'avg',
        subtitle: 'Weak positive correlation above 78°C',
        color: '#6c47ff',
        data: [
          { name: '72', value: 4.1 },
          { name: '74', value: 4.8 },
          { name: '75', value: 5.2 },
          { name: '77', value: 6.0 },
          { name: '78', value: 7.1 },
          { name: '79', value: 8.4 },
          { name: '80', value: 9.0 },
          { name: '82', value: 10.8 },
          { name: '83', value: 11.5 },
          { name: '85', value: 13.2 }
        ]
      },
      {
        id: 'c6', title: 'OEE score', type: 'gauge',
        x_column: 'OEE', y_column: 'Score', aggregation: 'avg',
        subtitle: 'Overall equipment effectiveness vs target',
        color: '#00c2cb',
        data: [{ name: 'OEE', value: 71.2 }]
      },
      {
        id: 'c7', title: 'Scrap cost by product line', type: 'treemap',
        x_column: 'Line', y_column: 'Scrap', aggregation: 'sum',
        subtitle: 'Engine Part B drives over a third of scrap cost',
        color: '#f59e0b',
        data: [
          { name: 'Engine Part B', value: 36 },
          { name: 'Suspension Unit', value: 24 },
          { name: 'Chassis Frame', value: 19 },
          { name: 'Gearbox', value: 13 },
          { name: 'Other', value: 8 }
        ]
      },
      {
        id: 'c8', title: 'Defect correlation heatmap', type: 'heatmap',
        x_column: 'Correlation', y_column: 'Matrix', aggregation: 'avg',
        subtitle: 'Dimensional and assembly defects move closely together',
        color: '#e24b4a',
        data: [
          { name: 'Correlation', value: 100 }
        ]
      }
    ];
  }

  // Fallback e-commerce sample charts
  return [
    {
      id: 'c1', title: 'Monthly Revenue Growth', type: 'area',
      x_column: 'Month', y_column: 'Revenue', aggregation: 'sum',
      data: computeChartData(rows, 'Month', 'Revenue', 'sum')
    },
    {
      id: 'c2', title: 'City Performance Breakdown', type: 'donut',
      x_column: 'City', y_column: 'Revenue', aggregation: 'sum',
      data: computeChartData(rows, 'City', 'Revenue', 'sum')
    },
    {
      id: 'c3', title: 'Product Order Volumes', type: 'horizontal_bar',
      x_column: 'Status', y_column: 'Units', aggregation: 'sum',
      data: computeChartData(rows, 'Status', 'Units', 'sum')
    },
    {
      id: 'c4', title: 'Freight Semicircle', type: 'gauge',
      x_column: 'Month', y_column: 'Freight', aggregation: 'avg',
      data: [{ name: 'Freight Target', value: 76.5 }]
    }
  ];
};

const getSampleInsights = (type) => {
  if (type === 'manufacturing') {
    return [
      'Machine M-103 accounts for 34% of all defects despite running only 22% of total hours — likely a calibration issue.',
      'Night shift downtime is 3.2× higher than morning — staffing and lighting review recommended.',
      'Scrap cost grew 1.2M this month — correlated with Engine Part B and Suspension Unit product lines.'
    ];
  }
  return [
    'Revenue increased by 8.4% compared to previous monthly calculations.',
    'Karachi and Lahore accounts for 68% of overall transaction volume.',
    'Delivery logistics freight costs decreased by 4.5% due to optimized shipping routes.'
  ];
};

// Map components for unified rendering
export const ECommerceTemplate = DataSpeakDashboard;
export const ManufacturingTemplate = DataSpeakDashboard;
export default DataSpeakDashboard;
