import { useState, useEffect } from "react";
import { API_BASE_URL } from "../../config/api";
import { toast } from "sonner";
import {
  Lightbulb,
  TrendingUp,
  Target,
  Sparkles,
  Loader2,
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

export function AIInsightsPage() {
  const [insightsData, setInsightsData] = useState<any>(null);
  const [databasesList, setDatabasesList] = useState<any[]>([]);
  const [selectedDb, setSelectedDb] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  const fetchDatabases = async () => {
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/databases`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDatabasesList(data);
        if (data.length > 0 && !selectedDb) {
          setSelectedDb(data[0].id.toString());
        }
      }
    } catch (err) {
      toast.error("Failed to load database connections");
    }
  };

  const fetchInsightsForDb = async (dbId: string) => {
    if (!dbId) return;
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/analytics/connections/${dbId}/ai-insights`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setInsightsData(data);
      }
    } catch (err) {
      toast.error("Failed to load AI insights for database");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateNew = async () => {
    if (!selectedDb) return;
    setGenerating(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/analytics/connections/${selectedDb}/ai-insights/generate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setInsightsData(data);
        toast.success("Synthesized fresh AI business insights with Gemini 2.5 Flash!");
      } else {
        toast.error("Failed to generate AI insights for connection");
      }
    } catch (err) {
      toast.error("Error generating AI insights");
    } finally {
      setGenerating(false);
    }
  };

  useEffect(() => {
    fetchDatabases();
  }, []);

  useEffect(() => {
    if (selectedDb) {
      fetchInsightsForDb(selectedDb);
    }
  }, [selectedDb]);

  const hasInsights = insightsData && insightsData.status !== "not_generated" && insightsData.business_type;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">AI Business Recommendations</h1>
          <p className="text-gray-600 mt-1">
            Executive business insights synthesized from live stats with Gemini 2.5 Flash
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedDb} onValueChange={setSelectedDb}>
            <SelectTrigger className="w-48 font-medium">
              <SelectValue placeholder="Select Database" />
            </SelectTrigger>
            <SelectContent>
              {databasesList.map((db) => (
                <SelectItem key={db.id} value={db.id.toString()}>
                  {db.name} ({db.db_type})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={handleGenerateNew} disabled={generating} className="gap-2">
            {generating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Re-Synthesize Insights
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Empty State when insights not yet generated */}
      {!loading && insightsData && (!hasInsights) && (
        <Card className="border-dashed border-2 bg-slate-50/50 p-8 text-center">
          <div className="mx-auto w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center mb-3">
            <Lightbulb className="w-6 h-6 text-blue-600" />
          </div>
          <h3 className="text-lg font-semibold text-slate-800">No AI Insights Generated Yet</h3>
          <p className="text-sm text-slate-500 max-w-md mx-auto mt-1 mb-4">
            Deterministic metrics are ready. Click "Re-Synthesize Insights" above to synthesize an executive narrative and actionable recommendations using Gemini 2.5 Flash.
          </p>
          <Button onClick={handleGenerateNew} disabled={generating} className="gap-2">
            <Sparkles className="w-4 h-4" />
            Synthesize Insights Now
          </Button>
        </Card>
      )}

      {/* Business Domain Summary Banner */}
      {hasInsights && (
        <Card className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white border-none shadow-lg">
          <CardContent className="p-6 flex items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge className="bg-blue-500/30 text-blue-200 border-blue-400">Auto-Detected Domain</Badge>
                <span className="text-xs text-blue-300 font-mono">Gemini 2.5 Engine</span>
              </div>
              <h2 className="text-xl font-bold">{insightsData.business_type}</h2>
            </div>
            <div className="w-12 h-12 rounded-xl bg-white/10 flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-amber-400" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Key Metrics Cards */}
      {hasInsights && insightsData.key_metrics && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {insightsData.key_metrics.map((km: any, idx: number) => (
            <Card key={idx} className="border shadow-sm">
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 font-semibold uppercase">{km.title}</span>
                  <Badge variant="outline" className="text-[10px] text-blue-600 bg-blue-50 border-blue-200">
                    {km.impact || "Growth"}
                  </Badge>
                </div>
                <p className="text-2xl font-bold mt-2 text-slate-900">{km.value}</p>
                <p className="text-xs text-green-600 font-medium mt-1 flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" />
                  {km.trend}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Observations & Recommendations Split */}
      {loading ? (
        <div className="flex justify-center p-12">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : hasInsights ? (
        <div className="grid md:grid-cols-2 gap-6">
          {/* Observations */}
          <Card className="border shadow-sm">
            <CardHeader className="bg-slate-50 py-4 border-b">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Lightbulb className="w-5 h-5 text-amber-500" />
                Key Data Observations
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5 space-y-3">
              {(insightsData.observations || []).map((obs: string, idx: number) => (
                <div key={idx} className="flex items-start gap-3 text-sm text-slate-700 bg-amber-50/50 p-3 rounded-lg border border-amber-100">
                  <span className="w-5 h-5 rounded-full bg-amber-200 text-amber-800 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span>{obs}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Strategic Recommendations */}
          <Card className="border shadow-sm">
            <CardHeader className="bg-slate-50 py-4 border-b">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Target className="w-5 h-5 text-emerald-600" />
                Strategic Action Items
              </CardTitle>
            </CardHeader>
            <CardContent className="p-5 space-y-3">
              {(insightsData.recommendations || []).map((rec: string, idx: number) => (
                <div key={idx} className="flex items-start gap-3 text-sm text-slate-700 bg-emerald-50/50 p-3 rounded-lg border border-emerald-100">
                  <span className="w-5 h-5 rounded-full bg-emerald-200 text-emerald-800 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                    {idx + 1}
                  </span>
                  <span>{rec}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
