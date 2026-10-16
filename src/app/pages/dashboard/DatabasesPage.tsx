import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router";
import { API_BASE_URL } from "../../config/api";
import { Plus, CheckCircle, XCircle, Settings, Trash2, Database, Table, Search, Loader2, Sparkles, Network } from "lucide-react";
import { Button } from "../../components/ui/button";
import { QueryChatPanel } from "../../components/QueryChatPanel";

import { Card, CardContent } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";

// Slim scrollbar, no arrow buttons (self-contained, no global CSS needed)
const THIN_SCROLL =
  "[scrollbar-width:thin] [scrollbar-color:#cbd5e1_transparent] " +
  "[&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar]:h-1.5 " +
  "[&::-webkit-scrollbar-button]:hidden " +
  "[&::-webkit-scrollbar-track]:bg-transparent " +
  "[&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-thumb]:rounded-full " +
  "[&::-webkit-scrollbar-thumb:hover]:bg-slate-400";

export function DatabasesPage() {
  const navigate = useNavigate();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [databases, setDatabases] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Form state
  const [name, setName] = useState("");
  const [dbType, setDbType] = useState("postgresql");
  const [host, setHost] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [database, setDatabase] = useState("");

  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [testMessage, setTestMessage] = useState("");

  // Explorer state
  const [isExplorerOpen, setIsExplorerOpen] = useState(false);
  const [selectedDb, setSelectedDb] = useState<any>(null);
  const [tables, setTables] = useState<string[]>([]);
  const [tableSearch, setTableSearch] = useState("");
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableData, setTableData] = useState<any[]>([]);
  const [isFetchingTables, setIsFetchingTables] = useState(false);
  const [isFetchingData, setIsFetchingData] = useState(false);
  const [tableStats, setTableStats] = useState<{ rows: number; columns: number } | null>(null);
  const [explorerError, setExplorerError] = useState("");

  // AI Query Chat Modal State
  const [isQueryModalOpen, setIsQueryModalOpen] = useState(false);
  const [queryDbId, setQueryDbId] = useState<number | undefined>(undefined);

  const openAiQuery = (db?: any) => {
    if (db) {
      setQueryDbId(db.id);
    } else if (databases.length > 0) {
      setQueryDbId(databases[0].id);
    }
    setIsQueryModalOpen(true);
  };

  const fetchDatabases = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/databases`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setDatabases(data);
        setIsLoading(false);

        // Fetch stats for each database individually without blocking the main list
        data.forEach(async (db: any) => {
          try {
            const statsRes = await fetch(`${API_BASE_URL}/api/databases/${db.id}/stats`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            if (statsRes.ok) {
              const stats = await statsRes.json();
              setDatabases((currentDbs) =>
                currentDbs.map((d) => (d.id === db.id ? { ...d, stats } : d))
              );
            }
          } catch (e) {
            console.error(`Failed to fetch stats for DB ${db.id}`, e);
          }
        });
      } else {
        setIsLoading(false);
      }
    } catch (error) {
      console.error("Failed to fetch databases:", error);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDatabases();
  }, []);

  const handleTestConnection = async () => {
    setTestStatus("testing");
    setTestMessage("");
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/databases/test`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name, db_type: dbType, host, username, password, database }),
      });

      const data = await response.json();
      if (response.ok) {
        setTestStatus("success");
        setTestMessage("Connection successful!");
      } else {
        setTestStatus("error");
        setTestMessage(data.detail || "Connection failed.");
      }
    } catch (error) {
      setTestStatus("error");
      setTestMessage("An error occurred while testing.");
    }
  };

  const handleAddDatabase = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/databases`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name, db_type: dbType, host, username, password, database }),
      });

      if (response.ok) {
        setIsDialogOpen(false);
        // Reset form
        setName("");
        setHost("");
        setUsername("");
        setPassword("");
        setDatabase("");
        setTestStatus("idle");
        setTestMessage("");
        fetchDatabases(); // Refresh list
      }
    } catch (error) {
      console.error("Failed to add database:", error);
    }
  };

  const handleDeleteDatabase = async (id: number) => {
    if (!window.confirm("Delete this database connection?")) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/databases/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        fetchDatabases();
      }
    } catch (error) {
      console.error("Failed to delete database:", error);
    }
  };

  const openExplorer = async (db: any) => {
    setSelectedDb(db);
    setIsExplorerOpen(true);
    setTables([]);
    setTableSearch("");
    setSelectedTable(null);
    setTableData([]);
    setTableStats(null);
    setExplorerError("");
    setIsFetchingTables(true);

    const token = localStorage.getItem("token");
    try {
      const response = await fetch(`${API_BASE_URL}/api/databases/${db.id}/tables`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTables(data);
      } else {
        const err = await response.json();
        setExplorerError(err.detail || "Failed to fetch tables");
      }
    } catch (error) {
      setExplorerError("An error occurred while fetching tables");
    } finally {
      setIsFetchingTables(false);
    }
  };

  const fetchTableData = async (tableName: string) => {
    setSelectedTable(tableName);
    setTableData([]);
    setTableStats(null);
    setExplorerError("");
    setIsFetchingData(true);

    const token = localStorage.getItem("token");
    try {
      const response = await fetch(`${API_BASE_URL}/api/databases/${selectedDb.id}/tables/${tableName}/data`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setTableData(data);
      } else {
        const err = await response.json();
        setExplorerError(err.detail || "Failed to fetch data");
      }

      // Fetch table stats
      const statsRes = await fetch(`${API_BASE_URL}/api/databases/${selectedDb.id}/tables/${tableName}/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (statsRes.ok) {
        const stats = await statsRes.json();
        setTableStats(stats);
      }
    } catch (error) {
      setExplorerError("An error occurred while fetching data");
    } finally {
      setIsFetchingData(false);
    }
  };

  const liveDb = databases.find((d) => d.id === selectedDb?.id) || selectedDb;

  const filteredTables = useMemo(
    () => tables.filter((t) => t.toLowerCase().includes(tableSearch.toLowerCase())),
    [tables, tableSearch]
  );

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Page header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-xl sm:text-2xl font-semibold mb-1 sm:mb-2">Databases</h1>
          <p className="text-sm sm:text-base text-gray-600">
            Manage your database connections and configurations
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <Button
            variant="outline"
            className="flex-1 sm:flex-none gap-2 border-blue-200 text-blue-700 bg-blue-50/50 hover:bg-blue-100"
            onClick={() => openAiQuery()}
          >
            <Sparkles className="w-4 h-4 text-blue-600" />
            AI Query Assistant
          </Button>

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button className="flex-1 sm:flex-none gap-2">
                <Plus className="w-4 h-4" />
                Add Database
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[550px] max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Add New Database</DialogTitle>
                <DialogDescription>
                  Connect a new database to your AI chatbot platform
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="db-name">Display Name</Label>
                  <Input id="db-name" placeholder="e.g. Production Server" value={name} onChange={(e) => setName(e.target.value)} />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="db-type">Database Type</Label>
                  <Select value={dbType} onValueChange={setDbType}>
                    <SelectTrigger id="db-type">
                      <SelectValue placeholder="Select database type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="postgresql">PostgreSQL</SelectItem>
                      <SelectItem value="mysql">MySQL</SelectItem>
                      <SelectItem value="mongodb">MongoDB</SelectItem>
                      <SelectItem value="firebase">Firebase</SelectItem>
                      <SelectItem value="mariadb">MariaDB</SelectItem>
                      <SelectItem value="sqlite">SQLite</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {dbType !== "sqlite" && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="db-host">Host</Label>
                      <Input
                        id="db-host"
                        placeholder="localhost:5432"
                        value={host}
                        onChange={(e) => setHost(e.target.value)}
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="db-username">Username</Label>
                        <Input id="db-username" placeholder="admin" value={username} onChange={(e) => setUsername(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="db-password">Password</Label>
                        <Input id="db-password" type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
                      </div>
                    </div>
                  </>
                )}

                <div className="space-y-2">
                  <Label htmlFor="db-database">
                    {dbType === "sqlite" ? "Full SQLite File Path" : "Technical Database Name"}
                  </Label>
                  <Input
                    id="db-database"
                    placeholder={dbType === "sqlite" ? "e.g. C:\\Users\\...\\chinook.db" : "e.g. my_database"}
                    value={database}
                    onChange={(e) => setDatabase(e.target.value)}
                  />
                </div>

                {testMessage && (
                  <div className={`p-3 rounded text-sm ${testStatus === "success" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {testMessage}
                  </div>
                )}
              </div>

              <DialogFooter className="gap-2">
                <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                  Cancel
                </Button>
                <Button variant="secondary" onClick={handleTestConnection} disabled={testStatus === "testing"}>
                  {testStatus === "testing" ? "Testing..." : "Test Connection"}
                </Button>
                <Button onClick={handleAddDatabase}>Add Database</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Database List */}
      <div className="grid gap-4 sm:gap-6">
        {isLoading && (
          <div className="flex items-center justify-center py-10 text-blue-600">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
        )}

        {databases.length === 0 && !isLoading && (
          <div className="text-center p-6 sm:p-8 border border-dashed rounded-lg bg-gray-50">
            <p className="text-gray-500 text-sm sm:text-base">
              No databases connected yet. Click "Add Database" to get started.
            </p>
          </div>
        )}

        {databases.map((db) => (
          <Card key={db.id}>
            <CardContent className="p-4 sm:p-6">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-3">
                    <h3 className="text-lg font-semibold break-words min-w-0">{db.name}</h3>
                    {db.status === "connected" || db.status === "success" ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                        <CheckCircle className="w-3.5 h-3.5" />
                        Connected
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                        <XCircle className="w-3.5 h-3.5" />
                        Connection Error
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 sm:gap-4 text-sm">
                    <div className="min-w-0">
                      <p className="text-gray-600 mb-1">Type</p>
                      <p className="font-medium">{db.db_type}</p>
                    </div>
                    <div className="min-w-0">
                      <p className="text-gray-600 mb-1">Host</p>
                      <p className="font-medium break-all line-clamp-2" title={db.host || ""}>
                        {db.host || "—"}
                      </p>
                    </div>
                    <div className="min-w-0">
                      <p className="text-gray-600 mb-1">DB Name</p>
                      <p className="font-medium break-all line-clamp-2" title={db.database || ""}>
                        {db.database || "—"}
                      </p>
                    </div>
                    {db.stats && (
                      <div className="bg-blue-50 px-3 py-2 rounded-md border border-blue-100 flex items-center gap-4 self-start w-fit max-w-full">
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-blue-600 font-bold">Tables</p>
                          <p className="text-sm font-semibold text-blue-900">{db.stats.table_count}</p>
                        </div>
                        <div className="h-8 w-[1px] bg-blue-200"></div>
                        <div>
                          <p className="text-[10px] uppercase tracking-wider text-blue-600 font-bold">Rows</p>
                          <p className="text-sm font-semibold text-blue-900">
                            {db.stats.tables?.reduce((acc: number, t: any) => acc + (t.rows || 0), 0).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap items-center gap-2 lg:flex-shrink-0 lg:justify-end">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={() => openAiQuery(db)}
                    className="flex-1 sm:flex-none gap-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-sm hover:from-blue-700 hover:to-indigo-700"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Query AI
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="flex-1 sm:flex-none"
                    onClick={() => openExplorer(db)}
                  >
                    View Data
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/dashboard/databases/${db.id}/erd`)}
                    className="flex-1 sm:flex-none gap-1.5"
                  >
                    <Network className="w-3.5 h-3.5" />
                    View ERD
                  </Button>
                  <div className="flex items-center ml-auto lg:ml-0">
                    <Button variant="ghost" size="icon" aria-label="Settings">
                      <Settings className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Delete database"
                      onClick={() => handleDeleteDatabase(db.id)}
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Database Explorer Modal */}
      <Dialog open={isExplorerOpen} onOpenChange={setIsExplorerOpen}>
        <DialogContent className="sm:max-w-[90vw] h-[90vh] sm:h-[80vh] max-h-[90vh] flex flex-col p-0 gap-0 overflow-hidden">
          <DialogHeader className="p-4 sm:p-6 pb-0 flex-shrink-0">
            <DialogTitle className="flex items-center gap-2 min-w-0">
              <Database className="w-5 h-5 text-blue-600 flex-shrink-0" />
              <span className="truncate">Explorer: {liveDb?.name}</span>
            </DialogTitle>
            <DialogDescription className="flex flex-wrap items-center gap-2 sm:gap-4">
              <span>Browse tables and preview data in your {liveDb?.db_type} database.</span>
              {liveDb?.stats && (
                <span className="inline-flex items-center gap-3 bg-blue-50 px-2 py-0.5 rounded border border-blue-100 text-[10px] font-bold text-blue-700 uppercase">
                  {liveDb.stats.table_count} Total Tables
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="flex-1 min-h-0 flex flex-col md:flex-row overflow-hidden p-3 sm:p-6 gap-3 md:gap-6">
            {/* Sidebar - Tables List */}
            <div className="w-full md:w-64 max-h-44 md:max-h-none flex flex-col gap-3 md:gap-4 flex-shrink-0 min-h-0 md:border-r md:pr-6 border-b md:border-b-0 pb-3 md:pb-0">
              <div className="relative flex-shrink-0">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
                <Input
                  placeholder="Search tables..."
                  className="pl-9 h-9"
                  value={tableSearch}
                  onChange={(e) => setTableSearch(e.target.value)}
                />
              </div>

              <div className={`flex-1 min-h-0 overflow-y-auto space-y-1 ${THIN_SCROLL}`}>
                {isFetchingTables ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                  </div>
                ) : filteredTables.length > 0 ? (
                  filteredTables.map((table) => (
                    <button
                      key={table}
                      onClick={() => fetchTableData(table)}
                      className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${selectedTable === table
                          ? "bg-blue-50 text-blue-700"
                          : "text-gray-700 hover:bg-gray-100"
                        }`}
                    >
                      <Table className="w-4 h-4 opacity-70 flex-shrink-0" />
                      <span className="truncate">{table}</span>
                    </button>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 italic px-3 py-2">No tables found.</p>
                )}
              </div>
            </div>

            {/* Content - Data Table */}
            <div className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden">
              {explorerError && (
                <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg text-sm flex items-center gap-2">
                  <XCircle className="w-4 h-4 flex-shrink-0" />
                  <span className="break-words min-w-0">{explorerError}</span>
                </div>
              )}

              {selectedTable ? (
                <div className="flex-1 min-h-0 flex flex-col overflow-hidden bg-white border rounded-lg shadow-sm">
                  <div className="p-3 border-b bg-gray-50 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2 sm:gap-3 min-w-0">
                      <span className="text-sm font-semibold flex items-center gap-2 min-w-0">
                        <Table className="w-4 h-4 flex-shrink-0" />
                        <span className="truncate">Preview: {selectedTable}</span>
                      </span>
                      {tableStats && (
                        <div className="flex items-center gap-2 text-[10px] font-bold text-gray-500 uppercase bg-gray-100 px-2 py-0.5 rounded">
                          <span>{tableStats.rows.toLocaleString()} Rows</span>
                          <span>{tableStats.columns} Columns</span>
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-gray-500">Showing first 100 rows</span>
                  </div>

                  <div className={`flex-1 min-h-0 overflow-auto ${THIN_SCROLL}`}>
                    {isFetchingData ? (
                      <div className="flex flex-col items-center justify-center h-full gap-2">
                        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
                        <p className="text-sm text-gray-500 font-medium">Loading data...</p>
                      </div>
                    ) : tableData.length > 0 ? (
                      <table className="w-full text-sm text-left border-collapse">
                        <thead className="bg-gray-50 sticky top-0 z-10 shadow-sm">
                          <tr>
                            {Object.keys(tableData[0]).map((header) => (
                              <th key={header} className="px-3 sm:px-4 py-2 border-b font-semibold text-gray-700 whitespace-nowrap">
                                {header}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {tableData.map((row, i) => (
                            <tr key={i} className="hover:bg-gray-50 border-b">
                              {Object.values(row).map((val: any, j) => (
                                <td key={j} className="px-3 sm:px-4 py-2 text-gray-600 truncate max-w-[200px]">
                                  {val === null ? <span className="text-gray-400 italic">null</span> : String(val)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="flex items-center justify-center h-full text-gray-500 italic p-4 text-center">
                        No data available in this table.
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed rounded-lg bg-gray-50 p-4 text-center">
                  <Database className="w-10 h-10 sm:w-12 sm:h-12 text-gray-300 mb-3" />
                  <p className="text-gray-500 font-medium text-sm sm:text-base">
                    Select a table to preview data
                  </p>
                </div>
              )}
            </div>
          </div>

          <DialogFooter className="p-3 sm:p-4 border-t bg-gray-50 flex-shrink-0">
            <Button onClick={() => setIsExplorerOpen(false)}>Close Explorer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Conversational NL-to-SQL Query Modal */}
      <Dialog open={isQueryModalOpen} onOpenChange={setIsQueryModalOpen}>
        <DialogContent className="max-w-[calc(100%-1rem)] sm:max-w-[85vw] h-[90vh] sm:h-[85vh] p-0 overflow-hidden flex flex-col gap-0">
          <QueryChatPanel
            databases={databases}
            defaultDatabaseId={queryDbId}
            onClose={() => setIsQueryModalOpen(false)}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
}