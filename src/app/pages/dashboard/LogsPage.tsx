import { useState, useEffect, useCallback } from "react";
import { API_BASE_URL } from "../../config/api";
import { toast } from "sonner";
import {
  Search,
  Download,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Database,
  Filter,
  FileCode2,
  Sparkles,
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

interface LogItem {
  id: number;
  userQuestion: string;
  generatedQuery: string;
  database: string;
  status: string;
  executionTime: string;
  timestamp: string;
  rows: number;
  tokens?: number;
  error?: string | null;
}

interface LogStats {
  total_queries: number;
  successful: number;
  failed: number;
  success_rate: number;
  avg_response_time_ms: number;
}

interface DatabaseOption {
  id: number;
  name: string;
  db_type: string;
}

export function LogsPage() {
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [stats, setStats] = useState<LogStats>({
    total_queries: 0,
    successful: 0,
    failed: 0,
    success_rate: 100,
    avg_response_time_ms: 0,
  });
  const [databases, setDatabases] = useState<DatabaseOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  // Filters and pagination state
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedDb, setSelectedDb] = useState<string>("all");
  const [searchInput, setSearchInput] = useState<string>("");
  const [activeSearch, setActiveSearch] = useState<string>("");
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(20);
  const [total, setTotal] = useState<number>(0);

  // Fetch databases list for the filter dropdown
  useEffect(() => {
    const fetchDatabases = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await fetch(`${API_BASE_URL}/api/databases`, {
          headers: {
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        if (res.ok) {
          const data = await res.json();
          setDatabases(data);
        }
      } catch (err) {
        console.error("Failed to load databases list", err);
      }
    };
    fetchDatabases();
  }, []);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("token");
      const params = new URLSearchParams({
        page: page.toString(),
        limit: limit.toString(),
      });
      if (statusFilter !== "all") {
        params.append("status", statusFilter);
      }
      if (selectedDb !== "all") {
        params.append("database_id", selectedDb);
      }
      if (activeSearch.trim()) {
        params.append("search", activeSearch.trim());
      }

      const res = await fetch(`${API_BASE_URL}/api/logs?${params.toString()}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        throw new Error(`Failed to load logs: ${res.statusText}`);
      }

      const json = await res.json();
      setLogs(json.items || []);
      setTotal(json.total || 0);
      setStats({
        total_queries: json.total_queries || 0,
        successful: json.successful || 0,
        failed: json.failed || 0,
        success_rate: json.success_rate || 0,
        avg_response_time_ms: json.avg_response_time_ms || 0,
      });
    } catch (err: any) {
      console.error("Error fetching logs:", err);
      toast.error("Failed to load query logs");
    } finally {
      setLoading(false);
    }
  }, [page, limit, statusFilter, selectedDb, activeSearch]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // Handle live debounce or Enter key on search
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setActiveSearch(searchInput);
  };

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const token = localStorage.getItem("token");
      const params = new URLSearchParams();
      if (statusFilter !== "all") {
        params.append("status", statusFilter);
      }
      if (selectedDb !== "all") {
        params.append("database_id", selectedDb);
      }
      if (activeSearch.trim()) {
        params.append("search", activeSearch.trim());
      }

      const res = await fetch(`${API_BASE_URL}/api/logs/export?${params.toString()}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });

      if (!res.ok) {
        throw new Error("Failed to export logs");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `query_logs_${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        if (document.body.contains(a)) {
          document.body.removeChild(a);
        }
      }, 200);

      toast.success("Query logs exported to CSV");
    } catch (err: any) {
      console.error("Export error:", err);
      toast.error("Failed to export query logs");
    } finally {
      setExporting(false);
    }
  };

  const totalPages = Math.ceil(total / limit) || 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold mb-1 text-gray-900">Query Logs & Audit History</h1>
          <p className="text-gray-600 text-sm">
            Inspect natural language queries, generated SQL execution metrics, and error traces
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={fetchLogs}
            variant="outline"
            size="sm"
            className="gap-2"
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            onClick={handleExportCsv}
            disabled={exporting || logs.length === 0}
            className="gap-2"
            size="sm"
          >
            <Download className="w-4 h-4" />
            {exporting ? "Exporting..." : "Export CSV"}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                <Clock className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Queries</p>
                <p className="text-2xl font-bold text-gray-900">{stats.total_queries.toLocaleString()}</p>
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
                <p className="text-sm text-gray-600">Successful Queries</p>
                <p className="text-2xl font-bold text-green-700">
                  {stats.successful.toLocaleString()}
                  <span className="text-xs text-gray-500 font-normal ml-2">
                    ({stats.success_rate}%)
                  </span>
                </p>
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
                <p className="text-sm text-gray-600">Failed Queries</p>
                <p className="text-2xl font-bold text-red-700">{stats.failed.toLocaleString()}</p>
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
                <p className="text-sm text-gray-600">Avg Latency</p>
                <p className="text-2xl font-bold text-purple-700">{stats.avg_response_time_ms} ms</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters Bar */}
      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search by natural question or generated SQL..."
                className="pl-10"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
            </div>

            <Select
              value={statusFilter}
              onValueChange={(val) => {
                setStatusFilter(val);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-full md:w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="success">Success</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={selectedDb}
              onValueChange={(val) => {
                setSelectedDb(val);
                setPage(1);
              }}
            >
              <SelectTrigger className="w-full md:w-[200px]">
                <SelectValue placeholder="All Databases" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Databases</SelectItem>
                {databases.map((db) => (
                  <SelectItem key={db.id} value={db.id.toString()}>
                    {db.name} ({db.db_type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button type="submit" variant="secondary" className="gap-2">
              <Filter className="w-4 h-4" /> Filter
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Logs Table */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base font-semibold">Execution Records ({total})</CardTitle>
          <div className="text-xs text-gray-500">
            Page {page} of {totalPages}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-16 text-center text-gray-500 space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto text-blue-600" />
              <p className="text-sm font-medium">Loading live execution logs...</p>
            </div>
          ) : logs.length > 0 ? (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[170px]">Timestamp</TableHead>
                    <TableHead className="min-w-[320px]">User Question & SQL</TableHead>
                    <TableHead className="w-[160px]">Database</TableHead>
                    <TableHead className="w-[110px]">Status</TableHead>
                    <TableHead className="w-[100px]">Latency</TableHead>
                    <TableHead className="w-[80px]">Rows</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id} className="hover:bg-gray-50/80 transition-colors">
                      <TableCell className="text-xs text-gray-500 whitespace-nowrap">
                        {log.timestamp || "—"}
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <p className="font-medium text-sm text-gray-900 leading-snug">
                            {log.userQuestion || "Direct Query"}
                          </p>
                          {log.generatedQuery && (
                            <code className="text-xs bg-gray-50 border border-gray-200 px-2 py-1 rounded text-gray-700 block font-mono overflow-x-auto max-w-xl">
                              {log.generatedQuery}
                            </code>
                          )}
                          {log.error && (
                            <p className="text-xs text-red-600 font-mono bg-red-50 p-1.5 rounded border border-red-100">
                              Error: {log.error}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-gray-600 font-medium">
                        <span className="inline-flex items-center gap-1.5">
                          <Database className="w-3.5 h-3.5 text-gray-400" />
                          {log.database}
                        </span>
                      </TableCell>
                      <TableCell>
                        {log.status === "success" ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                            <CheckCircle className="w-3 h-3" /> Success
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
                            <XCircle className="w-3 h-3" /> Failed
                          </span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-gray-600 font-mono">
                        {log.executionTime}
                      </TableCell>
                      <TableCell className="text-xs text-gray-600 font-mono">
                        {log.rows}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="py-16 text-center text-gray-500">
              <FileCode2 className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <p className="font-medium text-base text-gray-800">No Query Logs Found</p>
              <p className="text-xs text-gray-500 mt-1 max-w-md mx-auto">
                {activeSearch || statusFilter !== "all" || selectedDb !== "all"
                  ? "No logs matched your active filter criteria. Try clearing search filters."
                  : "No queries have been executed by this tenant yet. Execute queries in the Chat workspace to see execution traces."}
              </p>
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-gray-100 pt-4 mt-4">
              <p className="text-xs text-gray-500">
                Showing {(page - 1) * limit + 1} to {Math.min(page * limit, total)} of {total} records
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1 || loading}
                  className="gap-1"
                >
                  <ChevronLeft className="w-4 h-4" /> Previous
                </Button>
                <span className="text-xs font-medium text-gray-700 px-2">
                  {page} / {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages || loading}
                  className="gap-1"
                >
                  Next <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
