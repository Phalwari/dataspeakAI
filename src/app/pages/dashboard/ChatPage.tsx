import { useState, useEffect, useRef } from "react";
import { API_BASE_URL } from "../../config/api";
import {
  MessageSquare,
  Plus,
  Trash2,
  Edit2,
  Check,
  X,
  Send,
  Sparkles,
  Database,
  FileText,
  Layers,
  ChevronDown,
  ChevronUp,
  Copy,
  ExternalLink,
  Bot,
  User,
  Search,
  Clock,
  ArrowRight,
  RefreshCw,
  Table as TableIcon,
  Users,
  Lock,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import {
  canModifyConversation,
  getConversationAccessBadge,
} from "../../utils/permissions";

interface SourceCitation {
  document_name: string;
  page_number?: number;
  content_type: string;
  reference_id?: string;
  snippet: string;
  score?: number;
  retrieval_similarity?: number;
  claim_support_score?: number;
  grounding_score?: number;
  grounding_status?: string;
  document_id?: number;
  chunk_id?: number;
  document_version?: number;
  is_grounded?: boolean;
}

interface SqlData {
  query: string;
  generated_sql: string;
  explanation: string;
  columns: string[];
  rows: Record<string, any>[];
  row_count: number;
  execution_time_ms: number;
  status: string;
  error_detail?: string;
}

interface ChatMessage {
  id: number;
  sender_role: "user" | "assistant" | "system";
  content: string;
  query_type?: "rag" | "sql" | "hybrid" | "user";
  metadata_json?: {
    sources?: SourceCitation[];
    sql_data?: SqlData;
    sql_agent?: {
      attempts?: number;
      corrections_made?: boolean;
    };
    grounding?: {
      status?: "supported" | "partially_supported" | "unsupported" | "unverified" | "no_claims";
      confidence?: number;
      has_low_confidence?: boolean;
      disclaimer?: string;
      unverified_reason?: string;
      claim_coverage_ratio?: number;
      total_claims_count?: number;
      verified_claims_count?: number;
      skipped_claims_count?: number;
      verified_claims?: Array<{
        claim: string;
        is_grounded: boolean;
        score: number;
        raw_similarity?: number;
        source?: string;
        page_number?: number;
        reason?: string;
      }>;
    };
    route_decision?: {
      route_type: string;
      confidence: number;
      reasoning: string;
    };
  };
  created_at: string;
}

interface ConversationItem {
  id: number;
  title: string;
  platform: string;
  created_at: string;
  updated_at: string;
  last_message?: string;
  message_count: number;
  user_id?: number | null;
  is_owner?: boolean;
  is_shared?: boolean;
}

export function ChatPage() {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sourcePreference, setSourcePreference] = useState<"auto" | "documents" | "database">("auto");
  const [searchFilter, setSearchFilter] = useState("");

  const activeConv = conversations.find((c) => c.id === activeConvId);
  const isSharedReadOnly = Boolean(activeConv && activeConv.is_shared && !activeConv.is_owner);

  // Editing Title
  const [editingConvId, setEditingConvId] = useState<number | null>(null);
  const [editTitleText, setEditTitleText] = useState("");

  // Citation Inspection Modal
  const [selectedCitation, setSelectedCitation] = useState<SourceCitation | null>(null);
  const [expandedSources, setExpandedSources] = useState<Record<number, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const activeRequestIdRef = useRef<string | null>(null);
  const activeConvIdRef = useRef<number | null>(activeConvId);
  const token = localStorage.getItem("token");

  useEffect(() => {
    activeConvIdRef.current = activeConvId;
  }, [activeConvId]);

  // Scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Clean up any in-flight stream on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      activeRequestIdRef.current = null;
    };
  }, []);

  // Handle Stop Streaming
  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    activeRequestIdRef.current = null;
    setIsLoading(false);
    setMessages((prev) =>
      prev.map((m, idx) =>
        idx === prev.length - 1 && m.sender_role === "assistant"
          ? {
              ...m,
              content: m.content
                ? m.content + "\n\n*(Generation stopped by user)*"
                : "*(Generation cancelled)*"
            }
          : m
      )
    );
  };

  // Handle Select Conversation with In-flight Stream Abort
  const handleSelectConversation = (id: number) => {
    if (id === activeConvId) return;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    activeRequestIdRef.current = null;
    setIsLoading(false);
    setActiveConvId(id);
  };

  // Fetch Conversation List
  const fetchConversations = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data: ConversationItem[] = await res.json();
        setConversations(data);
        if (data.length > 0 && activeConvId === null) {
          setActiveConvId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, []);

  // Fetch Active Conversation Messages
  useEffect(() => {
    if (!activeConvId) {
      setMessages([]);
      return;
    }

    const fetchMessages = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/conversations/${activeConvId}`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setMessages(data.messages || []);
        }
      } catch (err) {
        console.error("Failed to load messages:", err);
      }
    };

    fetchMessages();
  }, [activeConvId]);

  // Handle New Conversation
  const handleNewChat = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    activeRequestIdRef.current = null;
    setIsLoading(false);
    setActiveConvId(null);
    setMessages([]);
    setInputText("");
  };

  // Handle Send Message with True Token Streaming
  const handleSendMessage = async (customPrompt?: string) => {
    if (isSharedReadOnly) {
      toast.error("This conversation is shared with you as read-only. Only the creator can send messages.");
      return;
    }

    const textToSend = customPrompt || inputText;
    if (!textToSend.trim() || isLoading) return;

    const userMessageContent = textToSend.trim();
    setInputText("");

    // Optimistic user message
    const tempUserMsg: ChatMessage = {
      id: Date.now(),
      sender_role: "user",
      content: userMessageContent,
      query_type: "user",
      created_at: new Date().toISOString()
    };

    // Placeholder assistant message for incremental token streaming
    const assistantPlaceholderId = Date.now() + 1;
    const tempAssistantMsg: ChatMessage = {
      id: assistantPlaceholderId,
      sender_role: "assistant",
      content: "",
      created_at: new Date().toISOString()
    };

    setMessages((prev) => [...prev, tempUserMsg, tempAssistantMsg]);
    setIsLoading(true);

    const currentRequestId =
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `req_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    activeRequestIdRef.current = currentRequestId;
    const initialConvId = activeConvId;

    const abortCtrl = new AbortController();
    abortControllerRef.current = abortCtrl;

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        signal: abortCtrl.signal,
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          conversation_id: activeConvId,
          query: userMessageContent,
          source_preference: sourcePreference,
          stream: true
        })
      });

      if (!res.ok) {
        let errDetail = "Failed to generate response";
        try {
          const errJson = await res.json();
          if (errJson.detail) errDetail = errJson.detail;
        } catch {}
        throw new Error(errDetail);
      }

      if (!res.body) {
        throw new Error("No response body received from server");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        if (abortCtrl.signal.aborted || activeRequestIdRef.current !== currentRequestId) {
          try {
            await reader.cancel();
          } catch {}
          return;
        }

        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          if (abortCtrl.signal.aborted || activeRequestIdRef.current !== currentRequestId) {
            try {
              await reader.cancel();
            } catch {}
            return;
          }

          const trimmed = part.trim();
          if (!trimmed.startsWith("data:")) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr || jsonStr === "[DONE]") continue;

          try {
            const parsed = JSON.parse(jsonStr);

            if (parsed.error) {
              toast.error(parsed.error);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantPlaceholderId
                    ? { ...m, content: m.content || `*(Error: ${parsed.error})*` }
                    : m
                )
              );
            }

            if (parsed.chunk) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantPlaceholderId
                    ? { ...m, content: m.content + parsed.chunk }
                    : m
                )
              );
            }

            if (parsed.done) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantPlaceholderId
                    ? {
                        ...m,
                        id: parsed.message_id || m.id,
                        query_type: parsed.query_type || m.query_type,
                        metadata_json: {
                          sources: parsed.sources,
                          sql_data: parsed.sql_data,
                          grounding: parsed.grounding,
                          sql_agent: parsed.sql_agent
                        }
                      }
                    : m
                )
              );

              if (
                parsed.conversation_id &&
                (!activeConvIdRef.current || activeConvIdRef.current === initialConvId)
              ) {
                setActiveConvId(parsed.conversation_id);
              }
              fetchConversations();
            }
          } catch {
            // Incomplete JSON chunk in buffer, will be completed in next frame
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError" || abortCtrl.signal.aborted || activeRequestIdRef.current !== currentRequestId) {
        return;
      }
      toast.error(err.message || "Failed to process chat query");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantPlaceholderId
            ? {
                ...m,
                content:
                  m.content ||
                  "Sorry, I encountered an error connecting to the AI engine. Please try again."
              }
            : m
        )
      );
    } finally {
      if (activeRequestIdRef.current === currentRequestId) {
        abortControllerRef.current = null;
        activeRequestIdRef.current = null;
        setIsLoading(false);
      }
    }
  };

  // Delete Conversation
  const handleDeleteConversation = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    const targetConv = conversations.find((c) => c.id === id);
    if (targetConv && !canModifyConversation(targetConv)) {
      toast.error("Permission denied: You cannot delete a shared conversation.");
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        toast.success("Conversation deleted");
        setConversations((prev) => prev.filter((c) => c.id !== id));
        if (activeConvId === id) {
          const remaining = conversations.filter((c) => c.id !== id);
          if (remaining.length > 0) {
            handleSelectConversation(remaining[0].id);
          } else {
            handleNewChat();
          }
        }
      } else {
        const errJson = await res.json().catch(() => null);
        toast.error(errJson?.detail || "Failed to delete conversation");
      }
    } catch (err) {
      toast.error("Failed to delete conversation");
    }
  };

  // Save Renamed Title
  const handleSaveRename = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    const targetConv = conversations.find((c) => c.id === id);
    if (targetConv && !canModifyConversation(targetConv)) {
      toast.error("Permission denied: You cannot rename a shared conversation.");
      setEditingConvId(null);
      return;
    }

    if (!editTitleText.trim()) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ title: editTitleText.trim() })
      });
      if (res.ok) {
        toast.success("Conversation renamed");
        setConversations((prev) =>
          prev.map((c) => (c.id === id ? { ...c, title: editTitleText.trim() } : c))
        );
        setEditingConvId(null);
      } else {
        const errJson = await res.json().catch(() => null);
        toast.error(errJson?.detail || "Failed to rename conversation");
      }
    } catch (err) {
      toast.error("Failed to rename conversation");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const toggleSourceExpand = (msgId: number) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const samplePrompts = [
    { text: "Summarize key findings from our latest uploaded document", icon: FileText, pref: "documents" },
    { text: "How many total users or records are in our database?", icon: Database, pref: "database" },
    { text: "Compare structured database numbers with our policy manual", icon: Layers, pref: "auto" },
    { text: "What are the key guidelines and compliance rules mentioned in the handbook?", icon: FileText, pref: "documents" }
  ];

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-white overflow-hidden">
      {/* 1. Left Conversation Sidebar */}
      <aside className="w-80 border-r border-gray-200 bg-gray-50 flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-gray-200 space-y-3">
          <Button
            onClick={handleNewChat}
            className="w-full justify-start gap-2 bg-blue-600 hover:bg-blue-700 text-white shadow-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            New Conversation
          </Button>

          <div className="relative">
            <Search className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
            <Input
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              placeholder="Search chat history..."
              className="pl-9 h-9 bg-white text-xs"
            />
          </div>
        </div>

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {filteredConversations.length === 0 ? (
            <div className="text-center py-10 px-4 text-gray-400 text-xs">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
              No conversations found. Start a new chat!
            </div>
          ) : (
            filteredConversations.map((conv) => {
              const isActive = conv.id === activeConvId;
              const isEditing = conv.id === editingConvId;

              return (
                <div
                  key={conv.id}
                  onClick={() => {
                    if (!isEditing) handleSelectConversation(conv.id);
                  }}
                  className={`group relative flex flex-col gap-1 p-3 rounded-lg cursor-pointer transition-all border text-left ${
                    isActive
                      ? "bg-white border-blue-200 shadow-sm ring-1 ring-blue-500/20"
                      : "border-transparent hover:bg-gray-100/80 hover:border-gray-200"
                  }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    {isEditing ? (
                      <div className="flex items-center gap-1 w-full" onClick={(e) => e.stopPropagation()}>
                        <Input
                          value={editTitleText}
                          onChange={(e) => setEditTitleText(e.target.value)}
                          className="h-7 text-xs"
                          autoFocus
                        />
                        <button
                          onClick={(e) => handleSaveRename(e, conv.id)}
                          className="p-1 hover:bg-blue-100 text-blue-600 rounded"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setEditingConvId(null)}
                          className="p-1 hover:bg-gray-200 text-gray-500 rounded"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-2 min-w-0 flex-1">
                          <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? "text-blue-600" : "text-gray-400"}`} />
                          <span className="text-xs font-semibold text-gray-800 truncate">
                            {conv.title}
                          </span>
                        </div>
                        {canModifyConversation(conv) ? (
                          <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingConvId(conv.id);
                                setEditTitleText(conv.title);
                              }}
                              className="p-1 hover:bg-gray-200 text-gray-500 rounded"
                              title="Rename"
                            >
                              <Edit2 className="w-3 h-3" />
                            </button>
                            <button
                              onClick={(e) => handleDeleteConversation(e, conv.id)}
                              className="p-1 hover:bg-red-100 text-red-500 rounded"
                              title="Delete"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        ) : (
                          <div className="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[10px] text-amber-700 font-medium transition-opacity">
                            <Lock className="w-2.5 h-2.5 text-amber-600" />
                            <span>Read-only</span>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {conv.last_message && !isEditing && (
                    <p className="text-[11px] text-gray-500 truncate pl-5">
                      {conv.last_message}
                    </p>
                  )}

                  <div className="flex items-center gap-2 pl-5 pt-0.5 text-[10px] text-gray-400">
                    <Clock className="w-2.5 h-2.5" />
                    <span>{new Date(conv.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
                    <span>•</span>
                    <span>{conv.message_count} msgs</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* 2. Main Chat Thread Panel */}
      <main className="flex-1 flex flex-col bg-white overflow-hidden">
        {/* Chat Header */}
        <header className="h-14 border-b border-gray-200 px-6 flex items-center justify-between bg-white flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2 flex-wrap">
                <span>{activeConv?.title || "Unified Conversational Assistant"}</span>
                {isSharedReadOnly && (
                  <Badge variant="outline" className="text-[11px] bg-amber-50 text-amber-800 border-amber-200 gap-1 font-medium">
                    <Users className="w-3 h-3 text-amber-600" />
                    Shared (Read-Only)
                  </Badge>
                )}
                {activeConv?.is_shared && activeConv?.is_owner && (
                  <Badge variant="outline" className="text-[11px] bg-blue-50 text-blue-700 border-blue-200 gap-1 font-medium">
                    <Users className="w-3 h-3 text-blue-600" />
                    Shared with Team
                  </Badge>
                )}
                {activeConv && !activeConv.is_shared && (
                  <Badge variant="outline" className="text-[10px] text-gray-500 border-gray-200 font-normal">
                    Private
                  </Badge>
                )}
              </h2>
              <p className="text-[11px] text-gray-500">
                Grounded Multi-Modal RAG &amp; NL-to-SQL Query Engine
              </p>
            </div>
          </div>

          {/* Source Preference Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 font-medium hidden sm:inline">Source Engine:</span>
            <div className="inline-flex rounded-lg border border-gray-200 p-0.5 bg-gray-50 text-xs">
              <button
                type="button"
                onClick={() => setSourcePreference("auto")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                  sourcePreference === "auto"
                    ? "bg-white text-blue-700 shadow-xs border border-gray-200"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Sparkles className="w-3 h-3 text-blue-600" />
                Auto
              </button>
              <button
                type="button"
                onClick={() => setSourcePreference("documents")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                  sourcePreference === "documents"
                    ? "bg-white text-blue-700 shadow-xs border border-gray-200"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <FileText className="w-3 h-3 text-emerald-600" />
                Knowledge Base (RAG)
              </button>
              <button
                type="button"
                onClick={() => setSourcePreference("database")}
                className={`px-2.5 py-1 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                  sourcePreference === "database"
                    ? "bg-white text-blue-700 shadow-xs border border-gray-200"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                <Database className="w-3 h-3 text-purple-600" />
                Database (SQL)
              </button>
            </div>
          </div>
        </header>

        {/* Message Thread Scroll Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center mx-auto text-white shadow-md">
                <Sparkles className="w-7 h-7" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-gray-900">How can I assist with your data today?</h3>
                <p className="text-xs text-gray-500 max-w-md mx-auto">
                  Ask natural language questions across your uploaded PDF documents, knowledge base manuals, or connected SQL databases.
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4 text-left">
                {samplePrompts.map((p, idx) => {
                  const Icon = p.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => {
                        setSourcePreference(p.pref as any);
                        handleSendMessage(p.text);
                      }}
                      className="p-3.5 rounded-xl border border-gray-200 hover:border-blue-300 hover:bg-blue-50/40 transition-all text-left group bg-white shadow-xs"
                    >
                      <div className="flex items-center gap-2 mb-1.5 text-xs font-semibold text-gray-700 group-hover:text-blue-600">
                        <Icon className="w-3.5 h-3.5 text-blue-500" />
                        <span>Prompt Suggestion</span>
                      </div>
                      <p className="text-xs text-gray-600 leading-relaxed">{p.text}</p>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.sender_role === "user";
              const sources = msg.metadata_json?.sources || [];
              const sqlData = msg.metadata_json?.sql_data;
              const routeType = msg.query_type || "rag";
              const isSourcesExpanded = !!expandedSources[msg.id];

              return (
                <div
                  key={msg.id}
                  className={`flex gap-3 max-w-3xl ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs ${
                      isUser
                        ? "bg-blue-600 text-white font-semibold"
                        : "bg-gradient-to-tr from-blue-500 to-indigo-600 text-white shadow-xs"
                    }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  {/* Bubble Content */}
                  <div className={`space-y-3 max-w-[85%] ${isUser ? "items-end" : "items-start"}`}>
                    <div
                      className={`p-4 rounded-2xl text-xs leading-relaxed ${
                        isUser
                          ? "bg-blue-600 text-white rounded-tr-xs"
                          : "bg-gray-50 border border-gray-200 text-gray-800 rounded-tl-xs shadow-xs"
                      }`}
                    >
                      {/* Engine Tag for Assistant */}
                      {!isUser && (
                        <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-gray-200">
                          <div className="flex items-center gap-1.5">
                            {routeType === "rag" && (
                              <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">
                                <FileText className="w-2.5 h-2.5 mr-1" />
                                RAG Knowledge Base
                              </Badge>
                            )}
                            {routeType === "sql" && (
                              <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-200 text-[10px]">
                                <Database className="w-2.5 h-2.5 mr-1" />
                                SQL Database Query
                              </Badge>
                            )}
                            {routeType === "hybrid" && (
                              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-[10px]">
                                <Layers className="w-2.5 h-2.5 mr-1" />
                                Hybrid Multi-Source
                              </Badge>
                            )}
                            {msg.metadata_json?.sql_agent?.corrections_made && (
                              <Badge variant="outline" className="bg-indigo-50 text-indigo-700 border-indigo-200 text-[10px]">
                                <Sparkles className="w-2.5 h-2.5 mr-1" />
                                Self-Corrected (Attempt {msg.metadata_json.sql_agent.attempts || 2})
                              </Badge>
                            )}
                          </div>
                          <button
                            onClick={() => copyToClipboard(msg.content)}
                            className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors"
                            title="Copy response"
                          >
                            <Copy className="w-3 h-3" />
                          </button>
                        </div>
                      )}

                      {/* Natural Language Message Body */}
                      <div className="whitespace-pre-wrap">
                        {msg.content || (!isUser && isLoading ? (
                          <span className="inline-flex items-center gap-1.5 text-gray-400 py-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse [animation-delay:150ms]" />
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse [animation-delay:300ms]" />
                            <span className="text-[11px] ml-1 text-gray-400">Thinking & streaming...</span>
                          </span>
                        ) : null)}
                      </div>

                      {/* Hallucination / Low Grounding Disclaimer */}
                      {msg.metadata_json?.grounding?.disclaimer && (
                        <div className="mt-2.5 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-[11px] flex items-start gap-2">
                          <span className="font-semibold text-xs leading-none mt-0.5">⚠️</span>
                          <span className="leading-relaxed">{msg.metadata_json.grounding.disclaimer}</span>
                        </div>
                      )}
                    </div>

                    {/* SQL Execution Card (if present) */}
                    {sqlData && sqlData.status === "success" && (
                      <div className="bg-white border border-purple-200 rounded-xl p-3 shadow-xs space-y-2 text-xs">
                        <div className="flex items-center justify-between border-b border-gray-100 pb-2">
                          <div className="flex items-center gap-1.5 font-semibold text-purple-900">
                            <TableIcon className="w-3.5 h-3.5 text-purple-600" />
                            <span>Executed SQL ({sqlData.row_count} rows • {sqlData.execution_time_ms}ms)</span>
                          </div>
                          <button
                            onClick={() => copyToClipboard(sqlData.generated_sql)}
                            className="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 font-medium"
                          >
                            <Copy className="w-3 h-3" />
                            Copy SQL
                          </button>
                        </div>

                        <pre className="p-2.5 rounded-lg bg-gray-900 text-gray-100 font-mono text-[11px] overflow-x-auto">
                          {sqlData.generated_sql}
                        </pre>

                        {/* Interactive Data Table Preview */}
                        {sqlData.rows.length > 0 && (
                          <div className="overflow-x-auto max-h-56 border border-gray-200 rounded-lg">
                            <table className="w-full text-left text-[11px] border-collapse">
                              <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 font-semibold sticky top-0">
                                <tr>
                                  {sqlData.columns.map((col, cIdx) => (
                                    <th key={cIdx} className="p-2 border-r border-gray-200 last:border-r-0 whitespace-nowrap">
                                      {col}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-100">
                                {sqlData.rows.slice(0, 15).map((row, rIdx) => (
                                  <tr key={rIdx} className="hover:bg-gray-50/80">
                                    {sqlData.columns.map((col, cIdx) => (
                                      <td key={cIdx} className="p-2 border-r border-gray-100 last:border-r-0 text-gray-600 whitespace-nowrap">
                                        {row[col] !== null ? String(row[col]) : <span className="text-gray-300">NULL</span>}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Source Citations Section (if RAG chunks exist) */}
                    {sources.length > 0 && (
                      <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-xs space-y-2">
                        <div
                          onClick={() => toggleSourceExpand(msg.id)}
                          className="flex items-center justify-between cursor-pointer text-xs font-semibold text-gray-700 hover:text-blue-600 transition-colors select-none"
                        >
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <FileText className="w-3.5 h-3.5 text-blue-600" />
                            <span>Grounding Sources ({sources.length} Citation{sources.length > 1 ? "s" : ""})</span>
                            {msg.metadata_json?.grounding && (
                              <Badge
                                variant="outline"
                                className={`text-[9px] px-1.5 py-0 h-4 font-medium ${
                                  msg.metadata_json.grounding.status === "supported"
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : msg.metadata_json.grounding.status === "partially_supported"
                                    ? "bg-amber-50 text-amber-700 border-amber-200"
                                    : msg.metadata_json.grounding.status === "unverified"
                                    ? "bg-yellow-50 text-yellow-800 border-yellow-300"
                                    : msg.metadata_json.grounding.status === "no_claims"
                                    ? "bg-gray-100 text-gray-600 border-gray-200"
                                    : msg.metadata_json.grounding.status === "unsupported"
                                    ? "bg-red-50 text-red-700 border-red-200"
                                    : (msg.metadata_json.grounding.confidence ?? 0) >= 0.65
                                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                    : "bg-yellow-50 text-yellow-800 border-yellow-300"
                                }`}
                                title={msg.metadata_json.grounding.unverified_reason || msg.metadata_json.grounding.disclaimer || undefined}
                              >
                                {msg.metadata_json.grounding.status === "supported"
                                  ? `Verified (${msg.metadata_json.grounding.verified_claims_count ?? 0}/${msg.metadata_json.grounding.total_claims_count ?? 0} claims)`
                                  : msg.metadata_json.grounding.status === "partially_supported"
                                  ? `Partial Grounding (${msg.metadata_json.grounding.verified_claims_count ?? 0}/${msg.metadata_json.grounding.total_claims_count ?? 0} claims)`
                                  : msg.metadata_json.grounding.status === "unverified"
                                  ? "⚠️ Unverified Evidence"
                                  : msg.metadata_json.grounding.status === "no_claims"
                                  ? "No Factual Claims"
                                  : msg.metadata_json.grounding.status === "unsupported"
                                  ? "Evidence Contradicted"
                                  : (msg.metadata_json.grounding.confidence ?? 0) >= 0.65
                                  ? "Verified Grounding"
                                  : "Unverified Grounding"}
                              </Badge>
                            )}
                          </div>
                          {isSourcesExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5 text-gray-400" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                          )}
                        </div>

                        {/* Collapsible Citation Cards */}
                        {isSourcesExpanded && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-gray-100">
                            {sources.map((src, sIdx) => (
                              <div
                                key={sIdx}
                                onClick={() => setSelectedCitation(src)}
                                className="p-2.5 rounded-lg border border-gray-200 hover:border-blue-400 bg-gray-50/50 hover:bg-blue-50/30 cursor-pointer transition-all space-y-1 text-left"
                              >
                                <div className="flex items-center justify-between text-[11px] font-semibold text-gray-800">
                                  <span className="truncate max-w-[140px]">{src.document_name}</span>
                                  <div className="flex items-center gap-1">
                                    {src.page_number && (
                                      <Badge variant="secondary" className="text-[9px] px-1.5 py-0 h-4">
                                        p. {src.page_number}
                                      </Badge>
                                    )}
                                    {src.retrieval_similarity !== undefined && (
                                      <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5 bg-blue-50/50 text-blue-700 border-blue-200" title="Retrieval similarity">
                                        sim: {Math.round(src.retrieval_similarity * 100)}%
                                      </Badge>
                                    )}
                                    {(src.claim_support_score !== undefined || src.score !== undefined) && (
                                      <Badge
                                        variant="outline"
                                        className={`text-[9px] px-1.5 py-0 h-4 ${
                                          src.grounding_status === "unverified"
                                            ? "bg-yellow-50 text-yellow-800 border-yellow-300"
                                            : (src.claim_support_score ?? src.score ?? 0) >= 0.65
                                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                            : "bg-gray-100 text-gray-600 border-gray-200"
                                        }`}
                                      >
                                        {src.grounding_status === "unverified"
                                          ? "Unverified"
                                          : `support: ${Math.round((src.claim_support_score ?? src.score ?? 0) * 100)}%`}
                                      </Badge>
                                    )}
                                  </div>
                                </div>
                                <p className="text-[10px] text-gray-600 line-clamp-2 leading-relaxed">
                                  "{src.snippet}"
                                </p>
                                <div className="flex items-center justify-between text-[9px] text-blue-600 font-medium pt-1">
                                  <span>Inspect chunk</span>
                                  <ExternalLink className="w-2.5 h-2.5" />
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Loading Typing Indicator */}
          {isLoading && (
            <div className="flex gap-3 max-w-2xl mr-auto items-center">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white flex items-center justify-center shadow-xs">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-200 rounded-tl-xs shadow-xs flex items-center gap-2">
                <RefreshCw className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                <span className="text-xs text-gray-600 font-medium">Synthesizing retrieval answer...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 3. Bottom Chat Input Box */}
        <div className="p-4 border-t border-gray-200 bg-white flex-shrink-0">
          {isSharedReadOnly ? (
            <div className="max-w-4xl mx-auto p-3 rounded-xl bg-amber-50/90 border border-amber-200 text-center flex items-center justify-center gap-2.5 text-xs text-amber-900 shadow-xs">
              <Lock className="w-4 h-4 text-amber-700 flex-shrink-0" />
              <span>
                <strong>Read-Only Conversation:</strong> This thread was shared with you. You can review all answers, source citations, and query results, but only the creator can submit new messages.
              </span>
            </div>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="relative flex items-center max-w-4xl mx-auto"
            >
              <Input
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask anything about your documents or databases... (Press Enter to send)"
                disabled={isLoading}
                className="pr-12 py-3 h-12 rounded-xl text-xs bg-gray-50 border-gray-200 focus:bg-white shadow-xs"
              />
              {isLoading ? (
                <Button
                  type="button"
                  size="sm"
                  onClick={handleStopGeneration}
                  title="Stop generation"
                  className="absolute right-1.5 top-1.5 bottom-1.5 px-3 h-9 rounded-lg bg-red-600 hover:bg-red-700 text-white shadow-xs flex items-center gap-1.5 text-xs font-medium transition-all"
                >
                  <div className="w-2.5 h-2.5 bg-white rounded-xs" />
                  <span>Stop</span>
                </Button>
              ) : (
                <Button
                  type="submit"
                  size="sm"
                  disabled={!inputText.trim()}
                  className="absolute right-1.5 top-1.5 bottom-1.5 h-9 w-9 p-0 rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
                >
                  <Send className="w-4 h-4" />
                </Button>
              )}
            </form>
          )}
          <div className="text-center mt-2">
            <span className="text-[10px] text-gray-400">
              Answers are generated with Google Gemini 2.5 Flash grounded on your tenant's indexed data.
            </span>
          </div>
        </div>
      </main>

      {/* Citation Chunk Details Modal */}
      <Dialog open={!!selectedCitation} onOpenChange={() => setSelectedCitation(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-sm font-bold text-gray-900">
              <FileText className="w-4 h-4 text-blue-600" />
              <span>Source Citation Details</span>
            </DialogTitle>
            <DialogDescription className="text-xs text-gray-500">
              Grounded document chunk retrieved from tenant knowledge base.
            </DialogDescription>
          </DialogHeader>

          {selectedCitation && (
            <div className="space-y-3 pt-2 text-xs">
              <div className="grid grid-cols-2 gap-2 p-2.5 rounded-lg bg-gray-50 border border-gray-200 text-[11px]">
                <div>
                  <span className="text-gray-500">Document:</span>
                  <p className="font-semibold text-gray-800">{selectedCitation.document_name}</p>
                </div>
                <div>
                  <span className="text-gray-500">Page Number:</span>
                  <p className="font-semibold text-gray-800">
                    {selectedCitation.page_number ? `Page ${selectedCitation.page_number}` : "N/A"}
                  </p>
                </div>
                <div>
                  <span className="text-gray-500">Content Type:</span>
                  <p className="font-semibold text-gray-800 capitalize">{selectedCitation.content_type}</p>
                </div>
                <div>
                  <span className="text-gray-500">Relevance Score:</span>
                  <p className="font-semibold text-gray-800">{selectedCitation.score || "N/A"}</p>
                </div>
              </div>

              <div>
                <span className="text-gray-500 block mb-1 font-medium">Extracted Text Content:</span>
                <div className="p-3 bg-gray-900 text-gray-100 rounded-lg max-h-60 overflow-y-auto font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                  {selectedCitation.snippet}
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedCitation(null)}
                >
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
