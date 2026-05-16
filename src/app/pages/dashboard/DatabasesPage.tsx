import { useState, useEffect } from "react";
import { API_BASE_URL } from "../../config/api";
import { Plus, CheckCircle, XCircle, Settings, Trash2, Database, Table, Search, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
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

const databases = [
  {
    id: 1,
    name: "Production DB",
    type: "PostgreSQL",
    host: "prod-db.example.com",
    database: "main_db",
    status: "connected",
    lastSync: "2 minutes ago",
    queries: 12534,
  },
  {
    id: 2,
    name: "Analytics DB",
    type: "MongoDB",
    host: "analytics.example.com",
    database: "analytics",
    status: "connected",
    lastSync: "5 minutes ago",
    queries: 8421,
  },
  {
    id: 3,
    name: "User Data",
    type: "Firebase",
    host: "project-id.firebaseio.com",
    database: "users",
    status: "error",
    lastSync: "1 hour ago",
    queries: 3245,
  },
];

export function DatabasesPage() {
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
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tableData, setTableData] = useState<any[]>([]);
  const [isFetchingTables, setIsFetchingTables] = useState(false);
  const [isFetchingData, setIsFetchingData] = useState(false);
  const [tableStats, setTableStats] = useState<{rows: number, columns: number} | null>(null);
  const [explorerError, setExplorerError] = useState("");

  const fetchDatabases = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/databases`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDatabases(data);
        setIsLoading(false);

        // Fetch stats for each database individually without blocking the main list
        data.forEach(async (db: any) => {
          try {
            const statsRes = await fetch(`${API_BASE_URL}/api/databases/${db.id}/stats`, {
              headers: { "Authorization": `Bearer ${token}` }
            });
            if (statsRes.ok) {
              const stats = await statsRes.json();
              setDatabases(currentDbs => 
                currentDbs.map(d => d.id === db.id ? { ...d, stats } : d)
              );
            }
          } catch (e) {
            console.error(`Failed to fetch stats for DB ${db.id}`, e);
          }
        });
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
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ name, db_type: dbType, host, username, password, database })
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
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ name, db_type: dbType, host, username, password, database })
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
        fetchDatabases(); // Refresh list
      }
    } catch (error) {
      console.error("Failed to add database:", error);
    }
  };

  const handleDeleteDatabase = async (id: number) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/databases/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
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
    setSelectedTable(null);
    setTableData([]);
    setExplorerError("");
    setIsFetchingTables(true);

    const token = localStorage.getItem("token");
    try {
      const response = await fetch(`${API_BASE_URL}/api/databases/${db.id}/tables`, {
        headers: { "Authorization": `Bearer ${token}` }
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
        headers: { "Authorization": `Bearer ${token}` }
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
        headers: { "Authorization": `Bearer ${token}` }
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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold mb-2">Databases</h1>
          <p className="text-gray-600">
            Manage your database connections and configurations
          </p>
        </div>

        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Add Database
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[550px]">
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

              <div className="space-y-2">
                <Label htmlFor="db-host">Host</Label>
                <Input
                  id="db-host"
                  placeholder="localhost:5432"
                  value={host}
                  onChange={(e) => setHost(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="db-username">Username</Label>
                  <Input id="db-username" placeholder="admin" value={username} onChange={(e) => setUsername(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="db-password">Password</Label>
                  <Input id="db-password" type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="db-database">Technical Database Name</Label>
                <Input id="db-database" placeholder="e.g. my_database" value={database} onChange={(e) => setDatabase(e.target.value)} />
              </div>

              {testMessage && (
                <div className={`p-3 rounded text-sm ${testStatus === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
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
              <Button onClick={handleAddDatabase}>
                Add Database
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Database List */}
      <div className="grid gap-6">
        {databases.length === 0 && !isLoading && (
          <div className="text-center p-8 border border-dashed rounded-lg bg-gray-50">
            <p className="text-gray-500">No databases connected yet. Click "Add Database" to get started.</p>
          </div>
        )}
        {databases.map((db) => (
          <Card key={db.id}>
            <CardContent className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <h3 className="text-lg font-semibold">{db.name}</h3>
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

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600 mb-1">Type</p>
                      <p className="font-medium">{db.db_type}</p>
                    </div>
                    <div>
                      <p className="text-gray-600 mb-1">Host</p>
                      <p className="font-medium">{db.host}</p>
                    </div>
                    <div>
                      <p className="text-gray-600 mb-1">DB Name</p>
                      <p className="font-medium">{db.database}</p>
                    </div>
                    {db.stats && (
                      <div className="bg-blue-50 px-3 py-2 rounded-md border border-blue-100 flex items-center gap-4 col-span-2 md:col-span-1">
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

                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={() => openExplorer(db)}>
                    View Data
                  </Button>
                  <Button variant="ghost" size="icon">
                    <Settings className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDeleteDatabase(db.id)}>
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Database Explorer Modal */}
      <Dialog open={isExplorerOpen} onOpenChange={setIsExplorerOpen}>
        {(() => {
          const liveDb = databases.find(d => d.id === selectedDb?.id) || selectedDb;
          return (
            <DialogContent className="sm:max-w-[90vw] h-[80vh] flex flex-col p-0">
              <DialogHeader className="p-6 pb-0">
                <DialogTitle className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-blue-600" />
                  Explorer: {liveDb?.name}
                </DialogTitle>
                <DialogDescription className="flex items-center gap-4">
                  <span>Browse tables and preview data in your {liveDb?.db_type} database.</span>
                  {liveDb?.stats && (
                    <div className="flex items-center gap-3 bg-blue-50 px-2 py-0.5 rounded border border-blue-100 text-[10px] font-bold text-blue-700 uppercase">
                      <span>{liveDb.stats.table_count} Total Tables</span>
                    </div>
                  )}
                </DialogDescription>
              </DialogHeader>

          <div className="flex-1 flex overflow-hidden p-6 gap-6">
            {/* Sidebar - Tables List */}
            <div className="w-64 flex flex-col gap-4 border-r pr-6">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-500" />
                <Input placeholder="Search tables..." className="pl-9 h-9" />
              </div>
              
              <div className="flex-1 overflow-y-auto space-y-1">
                {isFetchingTables ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                  </div>
                ) : tables.length > 0 ? (
                  tables.map((table) => (
                    <button
                      key={table}
                      onClick={() => fetchTableData(table)}
                      className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                        selectedTable === table 
                          ? "bg-blue-50 text-blue-700" 
                          : "text-gray-700 hover:bg-gray-100"
                      }`}
                    >
                      <Table className="w-4 h-4 opacity-70" />
                      {table}
                    </button>
                  ))
                ) : (
                  <p className="text-sm text-gray-500 italic px-3 py-2">No tables found.</p>
                )}
              </div>
            </div>

            {/* Content - Data Table */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {explorerError && (
                <div className="mb-4 p-4 bg-red-50 text-red-700 rounded-lg text-sm flex items-center gap-2">
                  <XCircle className="w-4 h-4" />
                  {explorerError}
                </div>
              )}

              {selectedTable ? (
                <div className="flex-1 flex flex-col overflow-hidden bg-white border rounded-lg shadow-sm">
                  <div className="p-3 border-b bg-gray-50 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold flex items-center gap-2">
                        <Table className="w-4 h-4" />
                        Preview: {selectedTable}
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
                  
                  <div className="flex-1 overflow-auto">
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
                              <th key={header} className="px-4 py-2 border-b font-semibold text-gray-700 whitespace-nowrap">
                                {header}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {tableData.map((row, i) => (
                            <tr key={i} className="hover:bg-gray-50 border-b">
                              {Object.values(row).map((val: any, j) => (
                                <td key={j} className="px-4 py-2 text-gray-600 truncate max-w-[200px]">
                                  {val === null ? <span className="text-gray-400 italic">null</span> : String(val)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : (
                      <div className="flex items-center justify-center h-full text-gray-500 italic">
                        No data available in this table.
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed rounded-lg bg-gray-50">
                  <Database className="w-12 h-12 text-gray-300 mb-3" />
                  <p className="text-gray-500 font-medium">Select a table from the sidebar to preview data</p>
                </div>
              )}
            </div>
          </div>

          <DialogFooter className="p-4 border-t bg-gray-50">
            <Button onClick={() => setIsExplorerOpen(false)}>Close Explorer</Button>
          </DialogFooter>
        </DialogContent>
          );
        })()}
      </Dialog>
    </div>
  );
}
