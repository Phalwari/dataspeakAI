import { useState, useEffect } from "react";
import { Link } from "react-router";
import { toast } from "sonner";
import { API_BASE_URL } from "../../config/api";
import {
  TrendingUp,
  Database,
  Activity,
  CreditCard,
  ArrowUpRight,
  ArrowDownRight,
  FileText,
  MessageSquare,
  PlusCircle,
  Upload,
  RefreshCw,
  Clock,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface OverviewData {
  total_queries: number;
  connected_databases: number;
  uploaded_documents: number;
  api_calls_today: number;
  subscription_plan: string;
  query_data: Array<{ name: string; date: string; queries: number }>;
  database_activity: Array<{ name: string; db_type?: string; queries: number }>;
  recent_queries: Array<{
    id: number;
    question: string;
    database: string;
    status: string;
    time: string;
    created_at: string;
  }>;
}

export function DashboardOverview() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(`${API_BASE_URL}/api/overview`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        throw new Error(`Failed to load overview: ${res.statusText}`);
      }

      const json = await res.json();
      setData(json);
    } catch (err: any) {
      console.error("Dashboard overview fetch error:", err);
      setError(err.message || "Failed to load dashboard overview");
      toast.error("Could not load live dashboard analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <div className="h-8 w-64 bg-gray-200 rounded animate-pulse mb-2" />
          <div className="h-4 w-96 bg-gray-100 rounded animate-pulse" />
        </div>

        {/* Skeleton Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-gray-200" />
                  <div className="h-4 w-12 bg-gray-200 rounded" />
                </div>
                <div className="h-7 w-20 bg-gray-200 rounded mb-2" />
                <div className="h-4 w-28 bg-gray-100 rounded" />
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Skeleton Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="animate-pulse">
            <CardHeader>
              <div className="h-6 w-36 bg-gray-200 rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-[300px] bg-gray-100 rounded" />
            </CardContent>
          </Card>
          <Card className="animate-pulse">
            <CardHeader>
              <div className="h-6 w-36 bg-gray-200 rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-[300px] bg-gray-100 rounded" />
            </CardContent>
          </Card>
        </div>

        {/* Skeleton Recent Queries */}
        <Card className="animate-pulse">
          <CardHeader>
            <div className="h-6 w-36 bg-gray-200 rounded" />
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-100 rounded-lg" />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-8 text-center bg-red-50 rounded-xl border border-red-200 space-y-4">
        <div className="text-red-600 font-semibold text-lg">{error}</div>
        <p className="text-gray-600 text-sm">
          Unable to connect to the analytics service. Please verify your connection or try again.
        </p>
        <Button onClick={fetchOverview} variant="outline" className="gap-2">
          <RefreshCw className="w-4 h-4" /> Try Again
        </Button>
      </div>
    );
  }

  const statCards = [
    {
      title: "Total Queries",
      value: (data?.total_queries ?? 0).toLocaleString(),
      change: data?.total_queries ? "Live" : "0",
      trend: "up",
      icon: TrendingUp,
    },
    {
      title: "Connected Databases",
      value: (data?.connected_databases ?? 0).toString(),
      change: data?.connected_databases ? "Active" : "None",
      trend: "neutral",
      icon: Database,
    },
    {
      title: "Uploaded Documents",
      value: (data?.uploaded_documents ?? 0).toString(),
      change: data?.uploaded_documents ? "Indexed" : "None",
      trend: "neutral",
      icon: FileText,
    },
    {
      title: "API Calls Today",
      value: (data?.api_calls_today ?? 0).toLocaleString(),
      change: "Today (UTC)",
      trend: "neutral",
      icon: Activity,
    },
    {
      title: "Subscription Plan",
      value: data?.subscription_plan || "Starter",
      change: "Active Tier",
      trend: "neutral",
      icon: CreditCard,
    },
  ];

  const hasQueries = (data?.total_queries ?? 0) > 0;
  const hasDatabases = (data?.connected_databases ?? 0) > 0;
  const hasDocuments = (data?.uploaded_documents ?? 0) > 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold mb-1 text-gray-900">Dashboard Overview</h1>
          <p className="text-gray-600 text-sm">
            Real-time telemetry and conversational activity for your tenant
          </p>
        </div>
        <Button onClick={fetchOverview} variant="outline" size="sm" className="gap-2 self-start sm:self-auto">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
        {statCards.map((stat) => (
          <Card key={stat.title}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                  <stat.icon className="w-5 h-5 text-white" />
                </div>
                {stat.trend === "up" && (
                  <div className="flex items-center gap-1 text-green-600 text-sm">
                    <ArrowUpRight className="w-4 h-4" />
                    <span>{stat.change}</span>
                  </div>
                )}
                {stat.trend === "down" && (
                  <div className="flex items-center gap-1 text-red-600 text-sm">
                    <ArrowDownRight className="w-4 h-4" />
                    <span>{stat.change}</span>
                  </div>
                )}
                {stat.trend === "neutral" && (
                  <div className="text-gray-500 text-xs font-medium">{stat.change}</div>
                )}
              </div>
              <h3 className="text-2xl font-bold mb-1 text-gray-900">{stat.value}</h3>
              <p className="text-sm text-gray-600">{stat.title}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Onboarding Banner if Zero Activity */}
      {(!hasQueries || !hasDatabases) && (
        <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-semibold text-blue-900 mb-1">
                  Get Started with DataSpeakAI
                </h3>
                <p className="text-sm text-blue-700">
                  {!hasDatabases
                    ? "Connect your SQL or NoSQL database to start running natural language queries."
                    : "Your database is connected! Ask your first data question in Conversational Chat."}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {!hasDatabases && (
                  <Button asChild size="sm" className="gap-2 bg-blue-600 hover:bg-blue-700">
                    <Link to="/dashboard/databases">
                      <PlusCircle className="w-4 h-4" /> Connect Database
                    </Link>
                  </Button>
                )}
                {!hasDocuments && (
                  <Button asChild size="sm" variant="outline" className="gap-2 bg-white">
                    <Link to="/dashboard/upload">
                      <Upload className="w-4 h-4" /> Upload Document
                    </Link>
                  </Button>
                )}
                <Button asChild size="sm" variant="default" className="gap-2 bg-indigo-600 hover:bg-indigo-700">
                  <Link to="/dashboard/chat">
                    <MessageSquare className="w-4 h-4" /> Start Chat
                  </Link>
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Query Volume (7 Days)</CardTitle>
          </CardHeader>
          <CardContent>
            {hasQueries ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={data?.query_data || []}>
                  <defs>
                    <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" allowDecimals={false} />
                  <Tooltip
                    formatter={(val: any) => [`${val} queries`, "Volume"]}
                    labelFormatter={(label) => `Day: ${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="queries"
                    stroke="#3b82f6"
                    fillOpacity={1}
                    fill="url(#colorQueries)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex flex-col items-center justify-center text-center text-gray-500 p-6">
                <Clock className="w-10 h-10 text-gray-300 mb-2" />
                <p className="font-medium">No Query History Yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  Queries executed through the chat or API will appear here over time.
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Database Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {hasDatabases && hasQueries ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={data?.database_activity || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" allowDecimals={false} />
                  <Tooltip formatter={(val: any) => [`${val} queries`, "Activity"]} />
                  <Bar dataKey="queries" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex flex-col items-center justify-center text-center text-gray-500 p-6">
                <Database className="w-10 h-10 text-gray-300 mb-2" />
                <p className="font-medium">No Database Activity</p>
                <p className="text-xs text-gray-400 mt-1">
                  Connect a database and execute queries to visualize activity distribution.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Queries */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-semibold">Recent Queries</CardTitle>
          {data?.recent_queries && data.recent_queries.length > 0 && (
            <Button asChild variant="ghost" size="sm" className="text-xs text-blue-600">
              <Link to="/dashboard/logs">View All Logs &rarr;</Link>
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {data?.recent_queries && data.recent_queries.length > 0 ? (
            <div className="space-y-3">
              {data.recent_queries.map((query) => (
                <div
                  key={query.id}
                  className="flex items-center justify-between p-4 rounded-lg border border-gray-100 hover:bg-gray-50/80 transition-colors"
                >
                  <div className="flex-1 min-w-0 pr-4">
                    <p className="font-medium text-sm text-gray-900 truncate mb-1">{query.question}</p>
                    <p className="text-xs text-gray-500 flex items-center gap-2">
                      <span className="font-medium text-gray-700">{query.database}</span>
                      <span>&bull;</span>
                      <span>{query.time || "Recently"}</span>
                    </p>
                  </div>
                  <div>
                    {query.status === "success" ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                        <CheckCircle2 className="w-3 h-3" /> Success
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
                        <XCircle className="w-3 h-3" /> Failed
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 flex flex-col items-center justify-center text-center text-gray-500">
              <MessageSquare className="w-10 h-10 text-gray-300 mb-2" />
              <p className="font-medium">No Recent Queries</p>
              <p className="text-xs text-gray-400 mt-1 max-w-sm mb-4">
                You haven't run any natural language queries yet. Head over to Chat to ask questions against your connected databases.
              </p>
              <Button asChild size="sm" className="gap-2">
                <Link to="/dashboard/chat">
                  <MessageSquare className="w-4 h-4" /> Start First Chat
                </Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
