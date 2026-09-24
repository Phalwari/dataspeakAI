import React, { useState } from "react";
import { API_BASE_URL } from "../config/api";
import {
  Sparkles,
  Send,
  Copy,
  Check,
  Code,
  Table,
  Clock,
  AlertCircle,
  Loader2,
  Database,
  RefreshCw,
} from "lucide-react";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";
import { Input } from "./ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { toast } from "sonner";

interface QueryChatMessage {
  id: string;
  query: str;
  generated_sql?: str;
  explanation?: str;
  columns?: str[];
  rows?: Record<string, any>[];
  row_count?: number;
  execution_time_ms?: number;
  status: "pending" | "success" | "error";
  error_detail?: str;
  timestamp: string;
}

interface QueryChatPanelProps {
  databases: any[];
  defaultDatabaseId?: number;
  onClose?: () => void;
}

const SAMPLE_QUESTIONS = [
  "Show me the top 10 users with their roles",
  "How many total orders are in the database?",
  "List active database connections and hosts",
  "Show the 5 most recently created records",
];

export function QueryChatPanel({
  databases,
  defaultDatabaseId,
  onClose,
}: QueryChatPanelProps) {
  const [selectedDbId, setSelectedDbId] = useState<string>(
    defaultDatabaseId ? String(defaultDatabaseId) : databases[0]?.id ? String(databases[0].id) : ""
  );
  const [inputQuery, setInputQuery] = useState("");
  const [messages, setMessages] = useState<QueryChatMessage[]>([]);
  const [isQuerying, setIsQuerying] = useState(false);
  const [copiedSqlId, setCopiedSqlId] = useState<string | null>(null);

  const handleSendQuery = async (queryToRun?: string) => {
    const activeQuery = queryToRun || inputQuery;
    if (!activeQuery.trim()) return;
    if (!selectedDbId) {
      toast.error("Please select a database first.");
      return;
    }

    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Authentication token missing. Please log in.");
      return;
    }

    const msgId = Date.now().toString();
    const newMsg: QueryChatMessage = {
      id: msgId,
      query: activeQuery,
      status: "pending",
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, newMsg]);
    if (!queryToRun) setInputQuery("");
    setIsQuerying(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          database_id: parseInt(selectedDbId, 10),
          query: activeQuery,
        }),
      });

      const data = await response.json();

      if (response.ok && data.status === "success") {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === msgId
              ? {
                  ...msg,
                  status: "success",
                  generated_sql: data.generated_sql,
                  explanation: data.explanation,
                  columns: data.columns || [],
                  rows: data.rows || [],
                  row_count: data.row_count || 0,
                  execution_time_ms: data.execution_time_ms || 0,
                }
              : msg
          )
        );
      } else {
        const errDetail = data.error_detail || data.detail || "Query processing failed.";
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === msgId
              ? {
                  ...msg,
                  status: "error",
                  generated_sql: data.generated_sql || "",
                  explanation: data.explanation || "",
                  error_detail: errDetail,
                }
              : msg
          )
        );
        toast.error(`Query Error: ${errDetail}`);
      }
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === msgId
            ? {
                ...msg,
                status: "error",
                error_detail: err.message || "Failed to communicate with backend.",
              }
            : msg
        )
      );
      toast.error("Network error executing query.");
    } finally {
      setIsQuerying(false);
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSqlId(id);
    toast.success("SQL copied to clipboard!");
    setTimeout(() => setCopiedSqlId(null), 2000);
  };

  const selectedDb = databases.find((d) => String(d.id) === selectedDbId);

  return (
    <div className="flex flex-col h-full bg-white rounded-lg overflow-hidden border shadow-sm">
      {/* Header */}
      <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-indigo-50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600 text-white rounded-lg shadow-sm">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              Conversational NL-to-SQL Engine
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full font-medium border border-blue-200">
                Gemini 2.5 Flash
              </span>
            </h2>
            <p className="text-xs text-gray-500">
              Query your relational databases using plain English with read-only security guardrails
            </p>
          </div>
        </div>

        {/* Database Selector */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Database className="w-4 h-4 text-gray-500" />
            <Select value={selectedDbId} onValueChange={setSelectedDbId}>
              <SelectTrigger className="w-[200px] h-9 bg-white">
                <SelectValue placeholder="Select Database" />
              </SelectTrigger>
              <SelectContent>
                {databases.map((db) => (
                  <SelectItem key={db.id} value={String(db.id)}>
                    {db.name} ({db.db_type})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {onClose && (
            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          )}
        </div>
      </div>

      {/* Main Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 bg-gray-50/50">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <div className="p-4 bg-blue-100 text-blue-600 rounded-full mb-4">
              <Sparkles className="w-8 h-8" />
            </div>
            <h3 className="text-base font-semibold text-gray-800 mb-1">
              Ask any question about your data
            </h3>
            <p className="text-sm text-gray-500 max-w-md mb-6">
              Our AI engine automatically introspects schema details, writes safe parameterized SQL,
              and executes it with 100-row capping.
            </p>

            {/* Suggested Prompts */}
            <div className="w-full max-w-lg space-y-2">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider text-left mb-2">
                Suggested Sample Questions
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {SAMPLE_QUESTIONS.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendQuery(q)}
                    className="p-3 text-xs text-left bg-white hover:bg-blue-50 hover:border-blue-300 border rounded-lg shadow-sm transition-all text-gray-700 font-medium flex items-center justify-between group"
                  >
                    <span>{q}</span>
                    <Sparkles className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 text-blue-600 transition-opacity ml-2 shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="space-y-3">
              {/* User Question Bubble */}
              <div className="flex justify-end">
                <div className="bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-none text-sm max-w-[80%] shadow-sm font-medium">
                  {msg.query}
                </div>
              </div>

              {/* AI Response Card */}
              <div className="flex justify-start">
                <div className="w-full max-w-[95%] bg-white border rounded-xl shadow-sm overflow-hidden">
                  {msg.status === "pending" ? (
                    <div className="p-6 flex items-center gap-3 text-blue-600">
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span className="text-sm font-medium">
                        Introspecting schema & generating SQL with Gemini 2.5 Flash...
                      </span>
                    </div>
                  ) : msg.status === "error" ? (
                    <div className="p-4 bg-red-50 border-l-4 border-red-500 text-red-800 space-y-2">
                      <div className="flex items-center gap-2 font-semibold text-sm">
                        <AlertCircle className="w-4 h-4 text-red-600" />
                        Query Failed / Security Exception
                      </div>
                      <p className="text-xs">{msg.error_detail}</p>
                      {msg.generated_sql && (
                        <div className="mt-2 bg-red-100/80 p-2.5 rounded text-xs font-mono overflow-x-auto">
                          {msg.generated_sql}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="divide-y">
                      {/* Explanation Header */}
                      {msg.explanation && (
                        <div className="p-4 bg-blue-50/50 text-sm text-gray-800 font-medium flex items-start gap-2.5">
                          <Sparkles className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                          <span>{msg.explanation}</span>
                        </div>
                      )}

                      {/* SQL Code Block */}
                      {msg.generated_sql && (
                        <div className="p-4 bg-slate-900 text-slate-100 text-xs font-mono relative group">
                          <div className="flex items-center justify-between mb-2 text-slate-400 font-sans text-[11px] border-b border-slate-800 pb-1.5">
                            <span className="flex items-center gap-1.5 font-medium">
                              <Code className="w-3.5 h-3.5 text-blue-400" />
                              Generated SQL ({selectedDb?.db_type || "SQL"})
                            </span>
                            <button
                              onClick={() => copyToClipboard(msg.generated_sql!, msg.id)}
                              className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                            >
                              {copiedSqlId === msg.id ? (
                                <>
                                  <Check className="w-3 h-3 text-green-400" />
                                  <span className="text-[10px] text-green-400">Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3 h-3" />
                                  <span className="text-[10px]">Copy SQL</span>
                                </>
                              )}
                            </button>
                          </div>
                          <pre className="overflow-x-auto leading-relaxed text-blue-300">
                            {msg.generated_sql}
                          </pre>
                        </div>
                      )}

                      {/* Query Execution Metadata & Results */}
                      <div className="p-4 space-y-3">
                        <div className="flex items-center justify-between text-xs text-gray-500">
                          <div className="flex items-center gap-3">
                            <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded text-gray-700 font-medium">
                              <Table className="w-3.5 h-3.5 text-blue-600" />
                              {msg.row_count} {msg.row_count === 1 ? "Row" : "Rows"}
                            </span>
                            <span className="flex items-center gap-1 bg-gray-100 px-2 py-1 rounded text-gray-700 font-medium">
                              <Clock className="w-3.5 h-3.5 text-emerald-600" />
                              {msg.execution_time_ms} ms
                            </span>
                          </div>
                          <span className="text-[11px] text-gray-400">Capped at LIMIT 100</span>
                        </div>

                        {/* Tabular Data Grid */}
                        {msg.rows && msg.rows.length > 0 ? (
                          <div className="border rounded-lg overflow-x-auto max-h-[300px]">
                            <table className="w-full text-xs text-left border-collapse">
                              <thead className="bg-gray-100 sticky top-0 z-10 font-semibold text-gray-700 border-b">
                                <tr>
                                  {msg.columns?.map((col) => (
                                    <th key={col} className="px-3 py-2 border-r last:border-r-0 whitespace-nowrap">
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {msg.rows.map((row, rIdx) => (
                                  <tr key={rIdx} className="border-b hover:bg-blue-50/30 transition-colors">
                                    {msg.columns?.map((col, cIdx) => (
                                      <td
                                        key={cIdx}
                                        className="px-3 py-2 border-r last:border-r-0 text-gray-600 max-w-[200px] truncate"
                                      >
                                        {row[col] === null ? (
                                          <span className="text-gray-400 italic">null</span>
                                        ) : (
                                          String(row[col])
                                        )}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="p-4 border rounded-lg text-center text-xs text-gray-500 bg-gray-50">
                            Query executed successfully but returned 0 rows.
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input Bar */}
      <div className="p-3 border-t bg-white flex items-center gap-2">
        <Input
          placeholder={
            selectedDb
              ? `Ask a question about '${selectedDb.name}' database...`
              : "Select a database to ask questions..."
          }
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSendQuery();
            }
          }}
          disabled={isQuerying || !selectedDbId}
          className="flex-1 h-10 text-sm"
        />

        <Button
          onClick={() => handleSendQuery()}
          disabled={isQuerying || !inputQuery.trim() || !selectedDbId}
          className="h-10 px-4 bg-blue-600 hover:bg-blue-700 text-white gap-2"
        >
          {isQuerying ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span>Query</span>
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
