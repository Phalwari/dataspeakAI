import { Link } from "react-router";
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

const platformStats = [
  {
    title: "Total Tenants",
    value: "1,247",
    change: "+12.5%",
    trend: "up",
    icon: Users,
  },
  {
    title: "Total Queries",
    value: "2.4M",
    change: "+18.2%",
    trend: "up",
    icon: Activity,
  },
  {
    title: "Active Databases",
    value: "3,891",
    change: "+7.1%",
    trend: "up",
    icon: Database,
  },
  {
    title: "System Health",
    value: "99.8%",
    change: "Healthy",
    trend: "neutral",
    icon: Server,
  },
];

const tenants = [
  {
    id: 1,
    company: "Acme Corporation",
    email: "admin@acme.com",
    plan: "Pro",
    queries: 45234,
    databases: 8,
    status: "active",
    joined: "Jan 15, 2026",
    usage: 85,
  },
  {
    id: 2,
    company: "TechStart Inc.",
    email: "contact@techstart.io",
    plan: "Starter",
    queries: 12456,
    databases: 3,
    status: "active",
    joined: "Jan 20, 2026",
    usage: 62,
  },
  {
    id: 3,
    company: "DataFlow Systems",
    email: "admin@dataflow.com",
    plan: "Pro",
    queries: 78921,
    databases: 12,
    status: "active",
    joined: "Dec 12, 2025",
    usage: 94,
  },
  {
    id: 4,
    company: "CloudBase",
    email: "team@cloudbase.co",
    plan: "Starter",
    queries: 8234,
    databases: 2,
    status: "trial",
    joined: "Feb 1, 2026",
    usage: 41,
  },
  {
    id: 5,
    company: "SmartData",
    email: "info@smartdata.ai",
    plan: "Free",
    queries: 987,
    databases: 1,
    status: "active",
    joined: "Feb 3, 2026",
    usage: 19,
  },
  {
    id: 6,
    company: "QueryLab",
    email: "hello@querylab.io",
    plan: "Pro",
    queries: 156789,
    databases: 15,
    status: "suspended",
    joined: "Nov 8, 2025",
    usage: 0,
  },
];

const systemMetrics = [
  { time: "00:00", cpu: 45, memory: 62, requests: 1200 },
  { time: "04:00", cpu: 38, memory: 58, requests: 800 },
  { time: "08:00", cpu: 72, memory: 75, requests: 3200 },
  { time: "12:00", cpu: 85, memory: 82, requests: 4500 },
  { time: "16:00", cpu: 78, memory: 79, requests: 3800 },
  { time: "20:00", cpu: 65, memory: 71, requests: 2400 },
];

const systemHealth = [
  {
    component: "API Gateway",
    status: "healthy",
    uptime: "99.99%",
    responseTime: "45ms",
  },
  {
    component: "Database Cluster",
    status: "healthy",
    uptime: "99.95%",
    responseTime: "12ms",
  },
  {
    component: "AI Model Service",
    status: "healthy",
    uptime: "99.87%",
    responseTime: "234ms",
  },
  {
    component: "Cache Layer",
    status: "warning",
    uptime: "98.42%",
    responseTime: "8ms",
  },
  {
    component: "Message Queue",
    status: "healthy",
    uptime: "100%",
    responseTime: "3ms",
  },
];

export function AdminPanel() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Bar */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/dashboard">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-semibold">Admin Panel</h1>
              <p className="text-sm text-gray-600">Platform Owner Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              All Systems Operational
            </Badge>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6 space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {platformStats.map((stat) => (
            <Card key={stat.title}>
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                    <stat.icon className="w-5 h-5 text-white" />
                  </div>
                  {stat.trend === "up" && (
                    <span className="text-xs text-green-600 font-medium">
                      {stat.change}
                    </span>
                  )}
                  {stat.trend === "neutral" && (
                    <span className="text-xs text-gray-600 font-medium">
                      {stat.change}
                    </span>
                  )}
                </div>
                <h3 className="text-2xl font-bold mb-1">{stat.value}</h3>
                <p className="text-sm text-gray-600">{stat.title}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* System Metrics */}
        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>System Resource Usage</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
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
              <CardTitle>Request Volume</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={systemMetrics}>
                  <defs>
                    <linearGradient id="colorRequests" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ec4899" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ec4899" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="time" stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="requests"
                    stroke="#ec4899"
                    fillOpacity={1}
                    fill="url(#colorRequests)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* System Health */}
        <Card>
          <CardHeader>
            <CardTitle>System Health Indicators</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {systemHealth.map((component) => (
                <div
                  key={component.component}
                  className="flex items-center justify-between p-4 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {component.status === "healthy" ? (
                      <CheckCircle className="w-5 h-5 text-green-600" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-yellow-600" />
                    )}
                    <div>
                      <p className="font-medium">{component.component}</p>
                      <p className="text-sm text-gray-600">
                        Uptime: {component.uptime}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    <div>
                      <p className="text-sm text-gray-600">Response Time</p>
                      <p className="font-medium">{component.responseTime}</p>
                    </div>
                    {component.status === "healthy" ? (
                      <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                        Healthy
                      </Badge>
                    ) : (
                      <Badge className="bg-yellow-100 text-yellow-700 hover:bg-yellow-100">
                        Warning
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Tenant List */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Tenant Management</CardTitle>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search tenants..."
                  className="pl-10 w-[300px]"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Company</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Queries</TableHead>
                  <TableHead>Databases</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tenants.map((tenant) => (
                  <TableRow key={tenant.id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{tenant.company}</p>
                        <p className="text-xs text-gray-600">{tenant.email}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          tenant.plan === "Pro"
                            ? "default"
                            : tenant.plan === "Starter"
                            ? "secondary"
                            : "outline"
                        }
                      >
                        {tenant.plan}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">
                      {tenant.queries.toLocaleString()}
                    </TableCell>
                    <TableCell>{tenant.databases}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 max-w-[80px]">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${tenant.usage}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-600">
                          {tenant.usage}%
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {tenant.status === "active" && (
                        <Badge className="bg-green-100 text-green-700 hover:bg-green-100">
                          Active
                        </Badge>
                      )}
                      {tenant.status === "trial" && (
                        <Badge className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                          Trial
                        </Badge>
                      )}
                      {tenant.status === "suspended" && (
                        <Badge className="bg-red-100 text-red-700 hover:bg-red-100">
                          Suspended
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {tenant.joined}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem>View Details</DropdownMenuItem>
                          <DropdownMenuItem>Edit Plan</DropdownMenuItem>
                          <DropdownMenuItem>View Logs</DropdownMenuItem>
                          <DropdownMenuItem className="text-red-600">
                            Suspend Account
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
