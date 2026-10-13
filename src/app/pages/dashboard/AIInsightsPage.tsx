import React, { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router";
import { API_BASE_URL } from "../../config/api";
import { toast } from "sonner";
import {
  Sparkles,
  RefreshCw,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  TrendingUp,
  Target,
  Database,
  ArrowRight,
  Filter,
  Check,
  EyeOff,
  Eye,
  Loader2,
  Clock,
  Layers,
  ShieldAlert,
  Flame,
  FileText,
  Activity,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Skeleton } from "../../components/ui/skeleton";

interface Recommendation {
  id: number;
  insight_id: number;
  action_step: string;
  priority: "high" | "medium" | "low" | string;
  action_type?: string;
  action_url?: string;
  status: "pending" | "completed" | string;
}

interface GeneratedInsight {
  id: number;
  tenant_id: number;
  database_id?: number | null;
  database_name?: string | null;
  title: string;
  category: "Revenue" | "Performance" | "Customer Success" | "Operational" | string;
  severity: "critical" | "warning" | "alert" | "opportunity" | string;
  summary: string;
  impact_score: number;
  confidence_score: number;
  status: "active" | "dismissed" | "actioned" | string;
  created_at: string;
  recommendations: Recommendation[];
}

interface SummaryStats {
  total_insights: number;
  critical_count: number;
  opportunities_count: number;
  pending_actions_count: number;
}

export function AIInsightsPage() {
  const navigate = useNavigate();
  const [insights, setInsights] = useState<GeneratedInsight[]>([]);
  const [summary, setSummary] = useState<SummaryStats>({
    total_insights: 0,
    critical_count: 0,
    opportunities_count: 0,
    pending_actions_count: 0,
  });
  const [databasesList, setDatabasesList] = useState<any[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [showDismissed, setShowDismissed] = useState<boolean>(false);
  const [hasConnectedSources, setHasConnectedSources] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [mutatingRecId, setMutatingRecId] = useState<number | null>(null);

  const token = localStorage.getItem("token") || "";

  // 1. Fetch available databases for dropdown
  const fetchDatabases = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/databases`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDatabasesList(Array.isArray(data) ? data : []);
      }
    } catch {
      // Non-blocking fallback
    }
  }, [token]);

  // 2. Fetch live insights from GET /api/insights
  const fetchInsights = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedDb && selectedDb !== "all") {
        params.append("database_id", selectedDb);
      }
      if (selectedCategory && selectedCategory !== "All") {
        params.append("category", selectedCategory);
      }
      if (selectedSeverity && selectedSeverity !== "all") {
        params.append("severity", selectedSeverity);
      }
      params.append("status", showDismissed ? "all" : "active");

      const res = await fetch(`${API_BASE_URL}/api/insights?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setInsights(data.insights || []);
        if (data.summary) {
          setSummary(data.summary);
        }
        setHasConnectedSources(data.has_connected_sources ?? true);
      } else {
        toast.error("Failed to load live AI insights.");
      }
    } catch (err) {
      toast.error("Network error fetching AI insights.");
    } finally {
      setLoading(false);
    }
  }, [token, selectedDb, selectedCategory, selectedSeverity, showDismissed]);

  // 3. Trigger fresh synthesis POST /api/insights/refresh
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const params = new URLSearchParams();
      if (selectedDb && selectedDb !== "all") {
        params.append("database_id", selectedDb);
      }

      const res = await fetch(`${API_BASE_URL}/api/insights/refresh?${params.toString()}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(
          data.refreshed_count > 0
            ? `Synthesized ${data.refreshed_count} fresh business insights with Gemini 2.5 Flash!`
            : "Telemetry scanned. System is in healthy equilibrium."
        );
        await fetchInsights();
      } else {
        toast.error("Failed to refresh AI insights.");
      }
    } catch (err) {
      toast.error("Error connecting to insights synthesis service.");
    } finally {
      setRefreshing(false);
    }
  };

  // 4. Update insight status (Dismiss vs Active)
  const handleToggleInsightStatus = async (insightId: number, currentStatus: string) => {
    const newStatus = currentStatus === "dismissed" ? "active" : "dismissed";
    try {
      const res = await fetch(`${API_BASE_URL}/api/insights/${insightId}/status`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (res.ok) {
        toast.success(newStatus === "dismissed" ? "Insight dismissed." : "Insight restored to active view.");
        // Optimistic state update
        setInsights((prev) =>
          prev.map((i) => (i.id === insightId ? { ...i, status: newStatus } : i))
        );
        fetchInsights();
      } else {
        toast.error("Could not update insight status.");
      }
    } catch {
      toast.error("Network error updating insight status.");
    }
  };

  // 5. Toggle recommendation status (Pending vs Completed)
  const handleToggleRecommendation = async (recId: number, currentStatus: string) => {
    const newStatus = currentStatus === "completed" ? "pending" : "completed";
    setMutatingRecId(recId);
    try {
      const res = await fetch(`${API_BASE_URL}/api/insights/recommendations/${recId}/status`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (res.ok) {
        toast.success(newStatus === "completed" ? "Action step completed!" : "Action step marked pending.");
        // Optimistic state update
        setInsights((prev) =>
          prev.map((insight) => ({
            ...insight,
            recommendations: insight.recommendations.map((rec) =>
              rec.id === recId ? { ...rec, status: newStatus } : rec
            ),
          }))
        );
      } else {
        toast.error("Could not update recommendation status.");
      }
    } catch {
      toast.error("Error updating recommendation.");
    } finally {
      setMutatingRecId(null);
    }
  };

  useEffect(() => {
    fetchDatabases();
  }, [fetchDatabases]);

  useEffect(() => {
    fetchInsights();
  }, [fetchInsights]);

  // Color & Icon mapping helpers
  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return (
          <Badge className="bg-red-100 text-red-800 border-red-300 font-semibold gap-1 px-2.5 py-0.5">
            <Flame className="w-3.5 h-3.5 text-red-600 animate-pulse" />
            CRITICAL
          </Badge>
        );
      case "warning":
        return (
          <Badge className="bg-amber-100 text-amber-800 border-amber-300 font-semibold gap-1 px-2.5 py-0.5">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
            WARNING
          </Badge>
        );
      case "alert":
        return (
          <Badge className="bg-orange-100 text-orange-800 border-orange-300 font-semibold gap-1 px-2.5 py-0.5">
            <ShieldAlert className="w-3.5 h-3.5 text-orange-600" />
            ALERT
          </Badge>
        );
      case "opportunity":
      default:
        return (
          <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold gap-1 px-2.5 py-0.5">
            <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
            OPPORTUNITY
          </Badge>
        );
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "high":
        return <Badge className="bg-red-50 text-red-700 border-red-200 text-[10px] font-bold">HIGH PRIORITY</Badge>;
      case "low":
        return <Badge className="bg-slate-50 text-slate-600 border-slate-200 text-[10px]">LOW</Badge>;
      case "medium":
      default:
        return <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[10px]">MEDIUM</Badge>;
    }
  };

  const getCardBorder = (severity: string, isDismissed: boolean) => {
    if (isDismissed) return "border-slate-200 opacity-60 bg-slate-50/50";
    switch (severity.toLowerCase()) {
      case "critical":
        return "border-red-200 hover:border-red-400 bg-white shadow-sm border-l-4 border-l-red-500";
      case "warning":
        return "border-amber-200 hover:border-amber-400 bg-white shadow-sm border-l-4 border-l-amber-500";
      case "alert":
        return "border-orange-200 hover:border-orange-400 bg-white shadow-sm border-l-4 border-l-orange-500";
      case "opportunity":
      default:
        return "border-emerald-200 hover:border-emerald-400 bg-white shadow-sm border-l-4 border-l-emerald-500";
    }
  };

  const categories = ["All", "Revenue", "Performance", "Customer Success", "Operational"];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ── Top Header & Global Actions ───────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-xl">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                AI Insights & Recommendation Engine
              </h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Dynamic cross-source business intelligence, anomaly detection, and tactical action playbooks synthesized with Gemini
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Database Scope Dropdown */}
          <Select value={selectedDb} onValueChange={setSelectedDb}>
            <SelectTrigger className="w-52 h-9 font-medium text-xs bg-white">
              <SelectValue placeholder="Scope: All Databases" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">🌐 All Databases (Global)</SelectItem>
              {databasesList.map((db) => (
                <SelectItem key={db.id} value={db.id.toString()}>
                  🗄️ {db.name} ({db.db_type})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Refresh Insights Trigger */}
          <Button
            onClick={handleRefresh}
            disabled={refreshing || loading}
            size="sm"
            className="gap-2 bg-gradient-to-r from-indigo-600 to-blue-600 hover:from-indigo-700 hover:to-blue-700 text-white shadow-sm"
          >
            {refreshing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing Telemetry...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                ⚡ Refresh AI Insights
              </>
            )}
          </Button>
        </div>
      </div>

      {/* ── Executive KPI Summary Strip ────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border bg-white shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Active Insights</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{summary.total_insights}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Layers className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border bg-white shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Critical / Warnings</p>
              <p className="text-2xl font-bold text-red-600 mt-1">{summary.critical_count}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-red-50 text-red-600 flex items-center justify-center">
              <AlertCircle className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border bg-white shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Growth Opportunities</p>
              <p className="text-2xl font-bold text-emerald-600 mt-1">{summary.opportunities_count}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
              <TrendingUp className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border bg-white shadow-xs">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Pending Action Items</p>
              <p className="text-2xl font-bold text-amber-600 mt-1">{summary.pending_actions_count}</p>
            </div>
            <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Target className="w-5 h-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Category Tabs & Interactive Filter Bar ─────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        {/* Category Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {categories.map((cat) => {
            const active = selectedCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  active
                    ? "bg-slate-900 text-white shadow-xs"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {cat}
              </button>
            );
          })}
        </div>

        {/* Secondary Filters */}
        <div className="flex items-center gap-2">
          {/* Severity Selector */}
          <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
            <SelectTrigger className="w-36 h-8 text-xs font-medium bg-white">
              <SelectValue placeholder="All Severities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Severities</SelectItem>
              <SelectItem value="critical">Critical</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
              <SelectItem value="alert">Alert</SelectItem>
              <SelectItem value="opportunity">Opportunity</SelectItem>
            </SelectContent>
          </Select>

          {/* Show / Hide Dismissed Toggle */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowDismissed(!showDismissed)}
            className={`h-8 text-xs gap-1.5 ${showDismissed ? "bg-slate-100 border-slate-400" : ""}`}
          >
            {showDismissed ? (
              <>
                <Eye className="w-3.5 h-3.5" />
                Showing Dismissed
              </>
            ) : (
              <>
                <EyeOff className="w-3.5 h-3.5 text-slate-400" />
                Hide Dismissed
              </>
            )}
          </Button>
        </div>
      </div>

      {/* ── Main Content Area: Insights Cards ──────────────────────────────── */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6 space-y-4">
              <div className="flex justify-between items-center">
                <Skeleton className="h-6 w-1/3" />
                <Skeleton className="h-6 w-24" />
              </div>
              <Skeleton className="h-16 w-full" />
              <div className="grid md:grid-cols-2 gap-3 pt-2">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
              </div>
            </Card>
          ))}
        </div>
      ) : !hasConnectedSources ? (
        /* ── Cold Start / Onboarding State ── */
        <Card className="border-dashed border-2 bg-gradient-to-b from-slate-50 to-white p-12 text-center">
          <div className="mx-auto w-14 h-14 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mb-4">
            <Sparkles className="w-7 h-7 text-indigo-600" />
          </div>
          <h3 className="text-xl font-bold text-slate-900">No Data Sources Connected Yet</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mt-1.5 mb-6">
            DataSpeakAI's Dynamic Insights Engine monitors query patterns, table row volumes, and error anomalies across your connected databases.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Button onClick={() => navigate("/dashboard/databases")} className="gap-2 bg-slate-900">
              <Database className="w-4 h-4" />
              Connect SQL Database
            </Button>
            <Button onClick={() => navigate("/dashboard/knowledge-base")} variant="outline" className="gap-2">
              <FileText className="w-4 h-4" />
              Upload Documents
            </Button>
          </div>
        </Card>
      ) : insights.length === 0 ? (
        /* ── Zero Unresolved Anomalies Clean Slate ── */
        <Card className="border-dashed border-2 bg-slate-50/50 p-12 text-center">
          <div className="mx-auto w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center mb-3">
            <CheckCircle2 className="w-6 h-6 text-emerald-600" />
          </div>
          <h3 className="text-lg font-bold text-slate-800">Zero Unresolved Anomalies</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mt-1 mb-5">
            {showDismissed
              ? "No insights match the current category or severity filters."
              : "All system telemetry is operating smoothly, or active insights have been dismissed."}
          </p>
          <div className="flex justify-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSelectedCategory("All");
                setSelectedSeverity("all");
              }}
            >
              Reset Filters
            </Button>
            <Button size="sm" onClick={handleRefresh} disabled={refreshing} className="gap-2">
              <RefreshCw className="w-3.5 h-3.5" />
              Re-Scan Telemetry
            </Button>
          </div>
        </Card>
      ) : (
        /* ── Active Insights Grid ── */
        <div className="space-y-4">
          {insights.map((insight) => {
            const isDismissed = insight.status === "dismissed";
            return (
              <Card
                key={insight.id}
                className={`transition-all duration-200 ${getCardBorder(insight.severity, isDismissed)}`}
              >
                <CardHeader className="pb-3 pt-5 px-6">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {getSeverityBadge(insight.severity)}
                        <Badge variant="outline" className="text-xs bg-slate-50 border-slate-200 font-medium">
                          {insight.category}
                        </Badge>
                        {insight.database_name && (
                          <span className="text-xs text-slate-500 flex items-center gap-1 font-mono">
                            <Database className="w-3 h-3" />
                            {insight.database_name}
                          </span>
                        )}
                        {isDismissed && (
                          <Badge className="bg-slate-200 text-slate-700 text-[10px]">DISMISSED</Badge>
                        )}
                      </div>
                      <CardTitle className="text-lg font-bold text-slate-900 pt-1">
                        {insight.title}
                      </CardTitle>
                    </div>

                    {/* Impact & Confidence & Dismiss Trigger */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="text-right hidden sm:block">
                        <div className="text-xs font-bold text-slate-700">
                          Impact: {insight.impact_score.toFixed(1)}/10
                        </div>
                        <div className="text-[11px] text-slate-400">
                          {Math.round(insight.confidence_score * 100)}% Confidence
                        </div>
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleToggleInsightStatus(insight.id, insight.status)}
                        className="h-8 w-8 p-0 text-slate-400 hover:text-slate-600"
                        title={isDismissed ? "Restore insight" : "Dismiss insight"}
                      >
                        {isDismissed ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="px-6 pb-6 pt-0 space-y-4">
                  {/* Narrative Summary */}
                  <p className="text-sm text-slate-600 leading-relaxed bg-slate-50/70 p-3.5 rounded-lg border border-slate-100">
                    {insight.summary}
                  </p>

                  {/* Recommendations Sub-Cards */}
                  {insight.recommendations && insight.recommendations.length > 0 && (
                    <div className="space-y-2 pt-1">
                      <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
                        <Target className="w-3.5 h-3.5 text-indigo-600" />
                        Tactical Action Playbook ({insight.recommendations.length})
                      </div>

                      <div className="grid gap-2">
                        {insight.recommendations.map((rec) => {
                          const isCompleted = rec.status === "completed";
                          return (
                            <div
                              key={rec.id}
                              className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg border transition-all ${
                                isCompleted
                                  ? "bg-slate-50/80 border-slate-200 opacity-60"
                                  : "bg-white border-slate-200 hover:border-slate-300 shadow-2xs"
                              }`}
                            >
                              <div className="flex items-start gap-3 flex-1">
                                {/* Completion Checkbox */}
                                <button
                                  type="button"
                                  disabled={mutatingRecId === rec.id}
                                  onClick={() => handleToggleRecommendation(rec.id, rec.status)}
                                  className={`mt-0.5 w-5 h-5 rounded-md border flex items-center justify-center transition-colors flex-shrink-0 cursor-pointer ${
                                    isCompleted
                                      ? "bg-emerald-600 border-emerald-600 text-white"
                                      : "border-slate-300 hover:border-slate-400 bg-white"
                                  }`}
                                >
                                  {isCompleted && <Check className="w-3.5 h-3.5" />}
                                </button>

                                <div className="space-y-1">
                                  <div className="flex items-center gap-2">
                                    {getPriorityBadge(rec.priority)}
                                    <span
                                      className={`text-xs font-semibold ${
                                        isCompleted ? "line-through text-slate-400" : "text-slate-800"
                                      }`}
                                    >
                                      {rec.action_step}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              {/* Contextual Deep-Link Button */}
                              {rec.action_url && !isCompleted && (
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => navigate(rec.action_url!)}
                                  className="h-7 text-xs font-semibold text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 border-indigo-200 self-start sm:self-auto gap-1"
                                >
                                  Take Action
                                  <ArrowRight className="w-3 h-3" />
                                </Button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400 border-t border-slate-100">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Generated: {new Date(insight.created_at).toLocaleString()}
                    </span>
                    <span className="font-mono">Gemini 2.5 Flash Engine</span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
