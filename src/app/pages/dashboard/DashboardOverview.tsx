import {
  TrendingUp,
  Database,
  Activity,
  CreditCard,
  ArrowUpRight,
  ArrowDownRight,
  FileText,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import {
  LineChart,
  Line,
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

const stats = [
  {
    title: "Total Queries",
    value: "24,567",
    change: "+12.5%",
    trend: "up",
    icon: TrendingUp,
  },
  {
    title: "Connected Databases",
    value: "5",
    change: "+2",
    trend: "up",
    icon: Database,
  },
  {
    title: "Uploaded Documents",
    value: "42",
    change: "+6",
    trend: "up",
    icon: FileText,
  },
  {
    title: "API Calls Today",
    value: "1,234",
    change: "-5.2%",
    trend: "down",
    icon: Activity,
  },
  {
    title: "Subscription Plan",
    value: "Starter",
    change: "$49/mo",
    trend: "neutral",
    icon: CreditCard,
  },
];

const queryData = [
  { name: "Mon", queries: 2400 },
  { name: "Tue", queries: 1398 },
  { name: "Wed", queries: 3800 },
  { name: "Thu", queries: 3908 },
  { name: "Fri", queries: 4800 },
  { name: "Sat", queries: 3800 },
  { name: "Sun", queries: 4300 },
];

const databaseActivity = [
  { name: "PostgreSQL", queries: 8500 },
  { name: "MongoDB", queries: 6200 },
  { name: "Firebase", queries: 4300 },
];

const recentQueries = [
  {
    question: "Show all users from last month",
    database: "PostgreSQL",
    status: "success",
    time: "2 minutes ago",
  },
  {
    question: "Get total revenue by product category",
    database: "MongoDB",
    status: "success",
    time: "5 minutes ago",
  },
  {
    question: "List pending orders with customer info",
    database: "PostgreSQL",
    status: "success",
    time: "12 minutes ago",
  },
  {
    question: "Find active subscriptions expiring soon",
    database: "Firebase",
    status: "failed",
    time: "18 minutes ago",
  },
];

export function DashboardOverview() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Dashboard Overview</h1>
        <p className="text-gray-600">
          Monitor your AI chatbot performance and usage
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat) => (
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
                  <div className="text-gray-600 text-sm">{stat.change}</div>
                )}
              </div>
              <h3 className="text-2xl font-bold mb-1">{stat.value}</h3>
              <p className="text-sm text-gray-600">{stat.title}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Query Volume</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={queryData}>
                <defs>
                  <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="queries"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorQueries)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Database Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={databaseActivity}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip />
                <Bar dataKey="queries" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Queries */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Queries</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentQueries.map((query, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-4 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1">
                  <p className="font-medium mb-1">{query.question}</p>
                  <p className="text-sm text-gray-600">
                    {query.database} • {query.time}
                  </p>
                </div>
                <div>
                  {query.status === "success" ? (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                      Success
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                      Failed
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
