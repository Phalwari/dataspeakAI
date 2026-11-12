import { Link, useNavigate } from "react-router";
import { useEffect, useState, useMemo } from "react";
import { toast } from "sonner";
import { API_BASE_URL } from "../../config/api";
import {
  Users,
  Database,
  Activity,
  Server,
  AlertCircle,
  CheckCircle,
  TrendingUp,
  ArrowLeft,
  Search,
  MoreVertical,
  RefreshCw,
  Cpu,
  Layers,
  ShieldAlert,
  Lock,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import { Badge } from "../../components/ui/badge";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { canAccessPlatformAdmin, formatRoleName } from "../../utils/permissions";

interface AdminStatCard {
  title: string;
  value: string;
  change: string;
  trend: string;
  key: string;
}

interface PlatformActivityPoint {
  date: string;
  queries: number;
  name?: string;
}

interface AdminStatsResponse {
  total_tenants: number;
  total_users: number;
  total_queries: number;
  active_databases: number;
  document_count: number;
  platform_stats: AdminStatCard[];
  platform_activity?: PlatformActivityPoint[];
}

interface TenantItem {
  id: number;
  company: string;
  email: string;
  plan: string;
  queries: number;
  databases: number;
  users_count: number;
  status: string;
  joined: string;
  usage: number;
}

interface SystemHealthResponse {
  status: string;
  active_db_pools: number;
  cached_dashboards_count: number;
}

const systemMetrics = [
  { time: "00:00", cpu: 32, memory: 54, requests: 420 },
  { time: "04:00", cpu: 28, memory: 52, requests: 280 },
  { time: "08:00", cpu: 48, memory: 65, requests: 1240 },
  { time: "12:00", cpu: 62, memory: 72, requests: 2150 },
  { time: "16:00", cpu: 55, memory: 68, requests: 1890 },
  { time: "20:00", cpu: 42, memory: 58, requests: 940 },
];

export function AdminPanel() {
  const navigate = useNavigate();
  const [authChecking, setAuthChecking] = useState(true);
  const [authorized, setAuthorized] = useState(false);
  const [permissionError, setPermissionError] = useState<string | null>(null);

  const [stats, setStats] = useState<AdminStatsResponse | null>(null);
  const [tenants, setTenants] = useState<TenantItem[]>([]);
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [loadingData, setLoadingData] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  // 1. Role verification check with explicit platform authority check
  useEffect(() => {
    const checkAdminAccess = async () => {
      const token = localStorage.getItem("token");
      if (!token) {
        toast.error("Please sign in as Platform Administrator to access this area");
        navigate("/login");
        return;
      }
      try {
        const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) {
          setPermissionError("Session expired or invalid credentials. Please sign in again.");
          setAuthorized(false);
          return;
        }
        const user = await res.json();
        
        // Strict platform admin authority boundary check (Sprint NR-1.1-A-T01)
        if (!canAccessPlatformAdmin(user)) {
          setPermissionError(
            `Platform Administrator Privileges Required. Your account is authenticated with tenant role "${formatRoleName(user.role)}", which is restricted to organization resources and does not have platform-level governance authority.`
          );
          setAuthorized(false);
          return;
        }

        setAuthorized(true);
        setPermissionError(null);
      } catch (err) {
        setPermissionError("Network connection error while validating platform administrative authority.");
        setAuthorized(false);
      } finally {
        setAuthChecking(false);
      }
    };

    checkAdminAccess();
  }, [navigate]);

  // 2. Fetch live stats & tenant management data
  const fetchAdminData = async () => {
    if (!authorized) return;
    setLoadingData(true);
    try {
      const token = localStorage.getItem("token");
      const headers = { Authorization: `Bearer ${token}` };

      const [statsRes, tenantsRes, healthRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/admin/stats`, { headers }),
        fetch(`${API_BASE_URL}/api/admin/tenants`, { headers }),
        fetch(`${API_BASE_URL}/api/admin/system-health`, { headers }),
      ]);

      // Check for security policy boundary enforcement (HTTP 403 Forbidden)
      if (statsRes.status === 403 || tenantsRes.status === 403 || healthRes.status === 403) {
        setPermissionError(
          "Access denied by security gateway (HTTP 403 Forbidden): Platform Administrator credentials are required to inspect multi-tenant telemetry and diagnostics."
        );
        toast.error("Permission denied: Platform Administrator access required");
        return;
      }

      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
      if (tenantsRes.ok) {
        const tenantsData = await tenantsRes.json();
        setTenants(tenantsData);
      }
      if (healthRes.ok) {
        const healthData = await healthRes.json();
        setHealth(healthData);
      }
    } catch (err) {
      console.error("Error loading admin data:", err);
      toast.error("Failed to load admin telemetry");
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    if (authorized) {
      fetchAdminData();
    }
  }, [authorized]);

  const filteredTenants = useMemo(() => {
    if (!searchQuery.trim()) return tenants;
    const q = searchQuery.toLowerCase();
    return tenants.filter(
      (t) =>
        t.company.toLowerCase().includes(q) ||
        t.email.toLowerCase().includes(q) ||
        t.plan.toLowerCase().includes(q)
    );
  }, [tenants, searchQuery]);

  if (authChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 text-gray-600 font-medium">
        Checking admin authorization...
      </div>
    );
  }

  // Graceful Permission Error Banner (Sprint NR-1.1-A-T09)
  if (permissionError) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col justify-center items-center p-6">
        <Card className="max-w-lg w-full shadow-lg border-red-200">
          <CardHeader className="text-center pb-2">
            <div className="w-14 h-14 bg-red-100 border border-red-200 text-red-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-xs">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <CardTitle className="text-xl font-bold text-gray-900">
              Platform Permission Boundary
            </CardTitle>
            <div className="flex justify-center mt-1">
              <Badge variant="outline" className="text-xs bg-red-50 text-red-700 border-red-200 font-semibold gap-1">
                <Lock className="w-3 h-3" />
                HTTP 403 Forbidden
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-2 text-center">
            <p className="text-sm text-gray-600 leading-relaxed">
              {permissionError}
            </p>

            <div className="p-3 bg-gray-100 rounded-lg text-left text-xs text-gray-600 border border-gray-200 space-y-1">
              <div className="font-semibold text-gray-800">Security Policy Notice:</div>
              <p>
                Platform administrator control centers are strictly isolated from tenant operations. General organization administrators cannot access global cross-tenant telemetry.
              </p>
            </div>

            <div className="pt-2 flex flex-col sm:flex-row gap-2 justify-center">
              <Button
                onClick={() => navigate("/dashboard")}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Return to Dashboard
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  localStorage.removeItem("token");
                  navigate("/login");
                }}
              >
                Sign in as Operator
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!authorized) {
    return null;
  }

  const statIcons: Record<string, any> = {
    tenants: Users,
    queries: Activity,
    databases: Database,
    health: Server,
  };

  const statCards = stats?.platform_stats || [
    { title: "Total Tenants", value: "0", change: "+0%", trend: "neutral", key: "tenants" },
    { title: "Total Queries", value: "0", change: "+0%", trend: "neutral", key: "queries" },
    { title: "Active Databases", value: "0", change: "+0%", trend: "neutral", key: "databases" },
    { title: "System Health", value: "100%", change: "Healthy", trend: "neutral", key: "health" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Bar */}
      <header className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">Admin Control Center</h1>
              <p className="text-xs text-gray-500">Platform-wide multi-tenant observability</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Badge variant="outline" className="gap-2 bg-green-50 text-green-700 border-green-200">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              {health?.status === "healthy" ? "All Systems Operational" : "System Active"}
            </Badge>
            <Button
              onClick={fetchAdminData}
              variant="outline"
              size="sm"
              className="gap-2 text-xs"
              disabled={loadingData}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingData ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {statCards.map((stat) => {
            const Icon = statIcons[stat.key] || Activity;
            return (
              <Card key={stat.title}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <span className="text-xs text-green-600 font-medium">{stat.change}</span>
                  </div>
                  <h3 className="text-2xl font-bold mb-1 text-gray-900">{stat.value}</h3>
                  <p className="text-sm text-gray-600">{stat.title}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* System Metrics */}
        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Simulated Resource Telemetry</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={systemMetrics}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="time" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="cpu"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    name="CPU %"
                  />
                  <Line
                    type="monotone"
                    dataKey="memory"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    name="Memory %"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base font-semibold">Global Platform Activity Curve</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={stats?.platform_activity && stats.platform_activity.length > 0 ? stats.platform_activity : []}>
                  <defs>
                    <linearGradient id="colorRequestsAdmin" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ec4899" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ec4899" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        const pt = payload[0].payload as PlatformActivityPoint;
                        return (
                          <div className="bg-white p-2 border border-gray-200 rounded shadow-sm text-xs">
                            <p className="font-semibold text-gray-900">{pt.date} ({pt.name})</p>
                            <p className="text-pink-600 font-medium">{pt.queries} Queries</p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="queries"
                    stroke="#ec4899"
                    fillOpacity={1}
                    fill="url(#colorRequestsAdmin)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* System Health Indicators */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Service Health & Pool Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg border border-gray-100 bg-gray-50/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Server className="w-5 h-5 text-blue-600" />
                  <div>
                    <p className="font-medium text-sm text-gray-900">Database Engine Pools</p>
                    <p className="text-xs text-gray-500">Live active connection pool instances</p>
                  </div>
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  {health?.active_db_pools ?? 0} active
                </Badge>
              </div>

              <div className="p-4 rounded-lg border border-gray-100 bg-gray-50/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Layers className="w-5 h-5 text-purple-600" />
                  <div>
                    <p className="font-medium text-sm text-gray-900">Cached Dashboards</p>
                    <p className="text-xs text-gray-500">In-memory Redis/TTL cache slots</p>
                  </div>
                </div>
                <Badge variant="outline" className="font-mono text-xs">
                  {health?.cached_dashboards_count ?? 0} cached
                </Badge>
              </div>

              <div className="p-4 rounded-lg border border-gray-100 bg-gray-50/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-5 h-5 text-green-600" />
                  <div>
                    <p className="font-medium text-sm text-gray-900">API Gateway Status</p>
                    <p className="text-xs text-gray-500">FastAPI ASGI Core Engine</p>
                  </div>
                </div>
                <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                  Healthy
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tenant List */}
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <CardTitle className="text-base font-semibold">
                  Registered Tenants ({filteredTenants.length})
                </CardTitle>
                <p className="text-xs text-gray-500 mt-1">Live customer accounts registered in DataSpeakAI</p>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search tenants or admin emails..."
                  className="pl-10 w-full sm:w-[280px]"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loadingData ? (
              <div className="py-12 text-center text-gray-500 space-y-2">
                <RefreshCw className="w-6 h-6 animate-spin mx-auto text-blue-600" />
                <p className="text-sm font-medium">Loading tenants...</p>
              </div>
            ) : filteredTenants.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Company</TableHead>
                    <TableHead>Plan</TableHead>
                    <TableHead>Users</TableHead>
                    <TableHead>Queries</TableHead>
                    <TableHead>Databases</TableHead>
                    <TableHead>Usage Meter</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Joined</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredTenants.map((tenant) => (
                    <TableRow key={tenant.id} className="hover:bg-gray-50/80 transition-colors">
                      <TableCell>
                        <div>
                          <p className="font-medium text-sm text-gray-900">{tenant.company}</p>
                          <p className="text-xs text-gray-500">{tenant.email}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={tenant.plan === "Pro" ? "default" : "secondary"}
                          className="text-xs"
                        >
                          {tenant.plan}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-gray-700">
                        {tenant.users_count}
                      </TableCell>
                      <TableCell className="font-medium text-sm text-gray-900">
                        {tenant.queries.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-sm text-gray-700">
                        {tenant.databases}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-[80px]">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{ width: `${Math.min(100, tenant.usage)}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-600">{tenant.usage}%</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className="bg-green-100 text-green-700 hover:bg-green-100 text-xs">
                          {tenant.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-gray-500 whitespace-nowrap">
                        {tenant.joined}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="py-12 text-center text-gray-500">
                <Users className="w-10 h-10 text-gray-300 mx-auto mb-2" />
                <p className="font-medium text-base text-gray-800">No Tenants Found</p>
                <p className="text-xs text-gray-500 mt-1">
                  {searchQuery ? "No tenants matched your search criteria." : "No tenants registered yet."}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
