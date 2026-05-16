import { useState } from "react";
import { API_BASE_URL } from "../../config/api";
import {
  Search,
  Filter,
  Download,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";

const logs = [
  {
    id: 1,
    userQuestion: "Show me all users registered in the last 30 days",
    generatedQuery: "SELECT * FROM users WHERE created_at >= NOW() - INTERVAL '30 days'",
    database: "PostgreSQL - Production DB",
    status: "success",
    executionTime: "124ms",
    timestamp: "2026-02-06 14:23:45",
    rows: 247,
  },
  {
    id: 2,
    userQuestion: "What's the total revenue from premium subscriptions?",
    generatedQuery: "db.subscriptions.aggregate([{ $match: { plan: 'premium' } }, { $group: { _id: null, total: { $sum: '$amount' } } }])",
    database: "MongoDB - Analytics DB",
    status: "success",
    executionTime: "89ms",
    timestamp: "2026-02-06 14:18:32",
    rows: 1,
  },
  {
    id: 3,
    userQuestion: "List all pending orders with customer information",
    generatedQuery: "SELECT o.*, c.name, c.email FROM orders o JOIN customers c ON o.customer_id = c.id WHERE o.status = 'pending'",
    database: "PostgreSQL - Production DB",
    status: "success",
    executionTime: "156ms",
    timestamp: "2026-02-06 14:12:18",
    rows: 89,
  },
  {
    id: 4,
    userQuestion: "Get active subscriptions expiring in next 7 days",
    generatedQuery: "SELECT * FROM subscriptions WHERE status = 'active' AND expires_at BETWEEN NOW() AND NOW() + INTERVAL '7 days'",
    database: "Firebase - User Data",
    status: "failed",
    executionTime: "0ms",
    timestamp: "2026-02-06 14:05:22",
    rows: 0,
    error: "Connection timeout",
  },
  {
    id: 5,
    userQuestion: "Show top 10 products by sales volume",
    generatedQuery: "SELECT p.name, COUNT(oi.id) as sales FROM products p JOIN order_items oi ON p.id = oi.product_id GROUP BY p.id ORDER BY sales DESC LIMIT 10",
    database: "PostgreSQL - Production DB",
    status: "success",
    executionTime: "203ms",
    timestamp: "2026-02-06 13:58:47",
    rows: 10,
  },
  {
    id: 6,
    userQuestion: "Find users who haven't logged in for 90 days",
    generatedQuery: "SELECT * FROM users WHERE last_login_at < NOW() - INTERVAL '90 days'",
    database: "PostgreSQL - Production DB",
    status: "success",
    executionTime: "167ms",
    timestamp: "2026-02-06 13:45:12",
    rows: 342,
  },
  {
    id: 7,
    userQuestion: "Calculate average order value by month",
    generatedQuery: "db.orders.aggregate([{ $group: { _id: { $month: '$created_at' }, avgValue: { $avg: '$total' } } }])",
    database: "MongoDB - Analytics DB",
    status: "success",
    executionTime: "112ms",
    timestamp: "2026-02-06 13:32:56",
    rows: 12,
  },
];

export function LogsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filteredLogs = logs.filter((log) =>
    statusFilter === "all" ? true : log.status === statusFilter
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold mb-2">Logs & History</h1>
          <p className="text-gray-600">
            View and analyze all queries processed by your chatbot
          </p>
        </div>

        <Button className="gap-2">
          <Download className="w-4 h-4" />
          Export Logs
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <Clock className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Queries</p>
                <p className="text-2xl font-bold">2,547</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Successful</p>
                <p className="text-2xl font-bold">2,431</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                <XCircle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Failed</p>
                <p className="text-2xl font-bold">116</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center">
                <Clock className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Avg Response</p>
                <p className="text-2xl font-bold">142ms</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search queries..."
                className="pl-10"
              />
            </div>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>

            <Select defaultValue="all">
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Database" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Databases</SelectItem>
                <SelectItem value="postgresql">PostgreSQL</SelectItem>
                <SelectItem value="mongodb">MongoDB</SelectItem>
                <SelectItem value="firebase">Firebase</SelectItem>
              </SelectContent>
            </Select>

            <Select defaultValue="24h">
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Time Range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1h">Last Hour</SelectItem>
                <SelectItem value="24h">Last 24 Hours</SelectItem>
                <SelectItem value="7d">Last 7 Days</SelectItem>
                <SelectItem value="30d">Last 30 Days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader>
          <CardTitle>Query History</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>User Question</TableHead>
                <TableHead>Database</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Execution Time</TableHead>
                <TableHead>Rows</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredLogs.map((log) => (
                <TableRow key={log.id} className="cursor-pointer hover:bg-gray-50">
                  <TableCell className="text-sm text-gray-600">
                    {log.timestamp}
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium text-sm mb-1">
                        {log.userQuestion}
                      </p>
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded text-gray-600 block overflow-x-auto">
                        {log.generatedQuery.length > 80
                          ? log.generatedQuery.substring(0, 80) + "..."
                          : log.generatedQuery}
                      </code>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {log.database}
                  </TableCell>
                  <TableCell>
                    {log.status === "success" ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Success
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                        <XCircle className="w-3.5 h-3.5" />
                        Failed
                      </span>
                    )}
                    {log.error && (
                      <p className="text-xs text-red-600 mt-1">{log.error}</p>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {log.executionTime}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {log.rows}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
