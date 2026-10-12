import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { API_BASE_URL } from "../../config/api";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
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
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { TrendingUp, Database, Zap, DollarSign, RefreshCw, AlertCircle } from "lucide-react";

interface UsageDataResponse {
  total_queries: number;
  tokens_used: number;
  token_limit: number;
  available_tokens: number;
  avg_tokens_per_query: number;
  databases_count: number;
  current_cost: string;
  plan?: string;
  usage_data: Array<{ date: string; queries: number; tokens: number }>;
  database_type_data: Array<{ name: string; value: number; color: string }>;
  hourly_data: Array<{ hour: string; queries: number }>;
}

export function UsagePage() {
  const [period, setPeriod] = useState<string>("7d");
  const [data, setData] = useState<UsageDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsage = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/usage?period=${period}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        throw new Error(`Failed to load usage: ${res.statusText}`);
      }

      const json = await res.json();
      setData(json);
    } catch (err: any) {
      console.error("Error fetching usage data:", err);
      setError(err.message || "Failed to load usage data");
      toast.error("Failed to load live usage metrics");
    } finally {
      setLoading(false);
    }
  }, [period]);

  useEffect(() => {
    fetchUsage();
  }, [fetchUsage]);

  const hasData = (data?.total_queries ?? 0) > 0;
  const tokenUsagePercent = data
    ? Math.min(100, Math.round((data.tokens_used / Math.max(1, data.token_limit)) * 100))
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold mb-1 text-gray-900">Usage & Metering</h1>
          <p className="text-gray-600 text-sm">
            Monitor API token consumption, query volume, and database distribution
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24 Hours</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
              <SelectItem value="90d">Last 90 Days</SelectItem>
            </SelectContent>
          </Select>

          <Button
            onClick={fetchUsage}
            variant="outline"
            size="sm"
            className="gap-2"
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-6 animate-pulse">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <Card key={i}>
                <CardContent className="p-6">
                  <div className="h-10 w-10 bg-gray-200 rounded-lg mb-4" />
                  <div className="h-4 w-24 bg-gray-100 rounded mb-2" />
                  <div className="h-8 w-20 bg-gray-200 rounded" />
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="h-[360px] bg-gray-100 rounded-xl" />
            <Card className="h-[360px] bg-gray-100 rounded-xl" />
          </div>
        </div>
      ) : error && !data ? (
        <div className="p-8 text-center bg-red-50 rounded-xl border border-red-200 space-y-4">
          <AlertCircle className="w-8 h-8 text-red-500 mx-auto" />
          <div className="text-red-700 font-semibold">{error}</div>
          <Button onClick={fetchUsage} variant="outline" size="sm">
            Try Again
          </Button>
        </div>
      ) : (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                    <TrendingUp className="w-5 h-5 text-blue-600" />
                  </div>
                  <span className="text-xs text-blue-600 font-medium">Period: {period}</span>
                </div>
                <p className="text-sm text-gray-600 mb-1">Total Queries</p>
                <p className="text-2xl font-bold text-gray-900">
                  {(data?.total_queries ?? 0).toLocaleString()}
                </p>
                <p className="text-xs text-gray-500 mt-1">Processed in selected timeframe</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                    <Zap className="w-5 h-5 text-purple-600" />
                  </div>
                  <span className="text-xs text-purple-600 font-medium">
                    {tokenUsagePercent}% Used
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-1">Tokens Used</p>
                <p className="text-2xl font-bold text-gray-900">
                  {((data?.tokens_used ?? 0) / 1000).toFixed(1)}K
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Out of {((data?.token_limit ?? 500000) / 1000).toFixed(0)}K monthly limit
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                    <Database className="w-5 h-5 text-green-600" />
                  </div>
                  <span className="text-xs text-green-600 font-medium">
                    {data?.databases_count ?? 0} active
                  </span>
                </div>
                <p className="text-sm text-gray-600 mb-1">Databases</p>
                <p className="text-2xl font-bold text-gray-900">
                  {data?.databases_count ?? 0}
                </p>
                <p className="text-xs text-gray-500 mt-1">Connected data sources</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
                    <DollarSign className="w-5 h-5 text-orange-600" />
                  </div>
                  <span className="text-xs text-orange-600 font-medium">{data?.plan || "Starter"}</span>
                </div>
                <p className="text-sm text-gray-600 mb-1">Estimated Cost</p>
                <p className="text-2xl font-bold text-gray-900">{data?.current_cost || "$29"}</p>
                <p className="text-xs text-gray-500 mt-1">Fixed monthly base tier</p>
              </CardContent>
            </Card>
          </div>

          {/* Charts Row */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Query Volume Over Time */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">Query Volume Over Time</CardTitle>
              </CardHeader>
              <CardContent>
                {hasData ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={data?.usage_data || []}>
                      <defs>
                        <linearGradient id="colorUsageQueries" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                      <XAxis dataKey="date" stroke="#9ca3af" />
                      <YAxis stroke="#9ca3af" allowDecimals={false} />
                      <Tooltip formatter={(val: any) => [`${val} queries`, "Volume"]} />
                      <Area
                        type="monotone"
                        dataKey="queries"
                        stroke="#3b82f6"
                        fillOpacity={1}
                        fill="url(#colorUsageQueries)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[300px] flex flex-col items-center justify-center text-center text-gray-500 p-6">
                    <TrendingUp className="w-10 h-10 text-gray-300 mb-2" />
                    <p className="font-medium">No Query Activity in Selected Period</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Execute queries to monitor timeline distributions.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Database Distribution */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base font-semibold">Queries by Database Type</CardTitle>
              </CardHeader>
              <CardContent>
                {hasData && (data?.database_type_data?.length ?? 0) > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={data?.database_type_data || []}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) =>
                          `${name} ${((percent || 0) * 100).toFixed(0)}%`
                        }
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {(data?.database_type_data || []).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(val: any) => [`${val} queries`, "Queries"]} />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[300px] flex flex-col items-center justify-center text-center text-gray-500 p-6">
                    <Database className="w-10 h-10 text-gray-300 mb-2" />
                    <p className="font-medium">No Database Distribution Data</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Queries will be categorized by database type once executed.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Token Usage */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Token Consumption</CardTitle>
            </CardHeader>
            <CardContent>
              {hasData ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={data?.usage_data || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" stroke="#9ca3af" />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip formatter={(val: any) => [`${val.toLocaleString()} tokens`, "Tokens"]} />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="tokens"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                      dot={{ fill: "#8b5cf6", r: 4 }}
                      activeDot={{ r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[300px] flex flex-col items-center justify-center text-center text-gray-500 p-6">
                  <Zap className="w-10 h-10 text-gray-300 mb-2" />
                  <p className="font-medium">No Token Consumption Recorded</p>
                  <p className="text-xs text-gray-400 mt-1">
                    AI generation tokens will be tracked chronologically here.
                  </p>
                </div>
              )}

              <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="bg-purple-50 rounded-lg p-4 border border-purple-100">
                  <p className="text-xs text-purple-700 font-medium mb-1">Total Tokens Used</p>
                  <p className="text-xl font-bold text-purple-950">
                    {(data?.tokens_used ?? 0).toLocaleString()}
                  </p>
                </div>
                <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
                  <p className="text-xs text-blue-700 font-medium mb-1">Available Tokens</p>
                  <p className="text-xl font-bold text-blue-950">
                    {(data?.available_tokens ?? 0).toLocaleString()}
                  </p>
                </div>
                <div className="bg-green-50 rounded-lg p-4 border border-green-100">
                  <p className="text-xs text-green-700 font-medium mb-1">Average per Query</p>
                  <p className="text-xl font-bold text-green-950">
                    {data?.avg_tokens_per_query ?? 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Hourly Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Hourly Activity Pattern</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={data?.hourly_data || []}>
                  <defs>
                    <linearGradient id="colorHourly" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ec4899" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ec4899" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="hour" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" allowDecimals={false} />
                  <Tooltip formatter={(val: any) => [`${val} queries`, "Hourly Pattern"]} />
                  <Area
                    type="monotone"
                    dataKey="queries"
                    stroke="#ec4899"
                    fillOpacity={1}
                    fill="url(#colorHourly)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
