import { useState, useEffect, useRef, useMemo } from "react";
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
  ChevronRight,
  Copy,
  ExternalLink,
  Bot,
  User,
  Search,
  Clock,
  RefreshCw,
  PanelLeftClose,
  PanelLeftOpen,
  Table as TableIcon
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

interface SourceCitation {
  document_name: string;
  page_number?: number;
  content_type: string;
  reference_id?: string;
  snippet: string;
  score?: number;
  grounding_score?: number;
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
      confidence?: number;
      has_low_confidence?: boolean;
      disclaimer?: string;
      verified_claims?: Array<{
        claim: string;
        is_grounded: boolean;
        score: number;
        source?: string;
        page_number?: number;
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
}

type SourcePreference = "auto" | "documents" | "database";

/* ---------- constants & helpers ---------- */

// Slim scrollbar, no arrow buttons. Self-contained (no global CSS needed).
const THIN_SCROLL =
  "[scrollbar-width:thin] [scrollbar-color:#cbd5e1_transparent] " +
  "[&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar]:h-1.5 " +
  "[&::-webkit-scrollbar-button]:hidden " +
  "[&::-webkit-scrollbar-track]:bg-transparent " +
  "[&::-webkit-scrollbar-thumb]:bg-slate-300 [&::-webkit-scrollbar-thumb]:rounded-full " +
  "[&::-webkit-scrollbar-thumb:hover]:bg-slate-400";

const SOURCE_OPTIONS: {
  key: SourcePreference;
  icon: any;
  iconClass: string;
  full: string;
  short: string;
}[] = [
    { key: "auto", icon: Sparkles, iconClass: "text-blue-600", full: "Auto", short: "Auto" },
    { key: "documents", icon: FileText, iconClass: "text-emerald-600", full: "Knowledge Base (RAG)", short: "KB" },
    { key: "database", icon: Database, iconClass: "text-purple-600", full: "Database (SQL)", short: "SQL" }
  ];

const GROUP_ORDER = ["Today", "Yesterday", "Previous 7 days", "Older"];
const GENERIC_TITLE = /^(widget chat|new chat|new conversation|untitled.*)$/i;
const LONG_MESSAGE_CHARS = 600;
const LONG_MESSAGE_LINES = 10;
const SQL_PREVIEW_ROWS = 5;

const getGroupLabel = (iso: string) => {
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const diffDays = Math.round((startOfDay(new Date()) - startOfDay(new Date(iso))) / 86400000);
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays <= 7) return "Previous 7 days";
  return "Older";
};

// Generic titles like "Widget Chat" are replaced by the last message preview
const getDisplayTitle = (c: ConversationItem) => {
  if (GENERIC_TITLE.test((c.title || "").trim()) && c.last_message) {
    const t = c.last_message.replace(/\s+/g, " ").trim();
    return t.length > 40 ? t.slice(0, 40) + "…" : t;
  }
  return c.title;
};

const isMobileViewport = () => typeof window !== "undefined" && window.innerWidth < 768;

export function ChatPage() {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sourcePreference, setSourcePreference] = useState<SourcePreference>("auto");
  const [searchFilter, setSearchFilter] = useState("");

  // Layout / collapse state
  const [listOpen, setListOpen] = useState<boolean>(() => !isMobileViewport());
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({ Older: true });
  const [expandedMsgs, setExpandedMsgs] = useState<Record<number, boolean>>({});
  const [expandedSql, setExpandedSql] = useState<Record<number, boolean>>({});
  const [showAllRows, setShowAllRows] = useState<Record<number, boolean>>({});

  // Editing Title
  const [editingConvId, setEditingConvId] = useState<number | null>(null);
  const [editTitleText, setEditTitleText] = useState("");

  // Citation Inspection Modal
  const [selectedCitation, setSelectedCitation] = useState<SourceCitation | null>(null);
  const [expandedSources, setExpandedSources] = useState<Record<number, boolean>>({});

  const scrollRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const token = localStorage.getItem("token");

  // Scroll only the message container (never the page)
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: isLoading ? "auto" : "smooth" });
  }, [messages, isLoading]);

  // Clean up any in-flight stream on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const closeListOnMobile = () => {
    if (isMobileViewport()) setListOpen(false);
  };

  const toggleMap = (
    setter: React.Dispatch<React.SetStateAction<Record<number, boolean>>>,
    id: number
  ) => setter((prev) => ({ ...prev, [id]: !prev[id] }));

  // Handle Stop Streaming
  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
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
    setIsLoading(false);
    setActiveConvId(null);
    setMessages([]);
    setInputText("");
    closeListOnMobile();
  };

  // Handle Send Message with True Token Streaming
  const handleSendMessage = async (customPrompt?: string) => {
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
        } catch { }
        throw new Error(errDetail);
      }

      if (!res.body) {
        throw new Error("No response body received from server");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        if (abortCtrl.signal.aborted) {
          try {
            await reader.cancel();
          } catch { }
          return;
        }

        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
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
                (!activeConvId || activeConvId !== parsed.conversation_id)
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
      if (err.name === "AbortError" || abortCtrl.signal.aborted) {
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
      abortControllerRef.current = null;
      setIsLoading(false);
    }
  };

  // Delete Conversation
  const handleDeleteConversation = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
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
            setActiveConvId(remaining[0].id);
          } else {
            handleNewChat();
          }
        }
      }
    } catch (err) {
      toast.error("Failed to delete conversation");
    }
  };

  // Save Renamed Title
  const handleSaveRename = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
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
      }
    } catch (err) {
      toast.error("Failed to rename conversation");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard");
  };

  const filteredConversations = useMemo(
    () =>
      conversations.filter((c) =>
        `${c.title} ${c.last_message || ""}`.toLowerCase().includes(searchFilter.toLowerCase())
      ),
    [conversations, searchFilter]
  );

  const groupedConversations = useMemo(() => {
    const groups: Record<string, ConversationItem[]> = {};
    filteredConversations.forEach((c) => {
      const label = getGroupLabel(c.updated_at || c.created_at);
      if (!groups[label]) groups[label] = [];
      groups[label].push(c);
    });
    return groups;
  }, [filteredConversations]);

  const activeConversation = conversations.find((c) => c.id === activeConvId);

  const samplePrompts = [
    { text: "Summarize key findings from our latest uploaded document", icon: FileText, pref: "documents" },
    { text: "How many total users or records are in our database?", icon: Database, pref: "database" },
    { text: "Compare structured database numbers with our policy manual", icon: Layers, pref: "auto" },
    { text: "What are the key guidelines and compliance rules mentioned in the handbook?", icon: FileText, pref: "documents" }
  ];

  const renderConversation = (conv: ConversationItem) => {
    const isActive = conv.id === activeConvId;
    const isEditing = conv.id === editingConvId;
    const displayTitle = getDisplayTitle(conv);
    const titleIsDerived = displayTitle !== conv.title;

    return (
      <div
        key={conv.id}
        onClick={() => {
          if (isEditing) return;
          setActiveConvId(conv.id);
          closeListOnMobile();
        }}
        className={`group relative flex flex-col gap-1 p-3 rounded-lg cursor-pointer transition-all border text-left ${isActive
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
              <div className="flex items-center gap-2 min-w-0">
                <MessageSquare
                  className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? "text-blue-600" : "text-gray-400"}`}
                />
                <span className="text-xs font-semibold text-gray-800 truncate">{displayTitle}</span>
              </div>
              <div className="opacity-100 md:opacity-0 md:group-hover:opacity-100 flex items-center gap-0.5 transition-opacity flex-shrink-0">
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
            </>
          )}
        </div>

        {conv.last_message && !isEditing && !titleIsDerived && (
          <p className="text-[11px] text-gray-500 truncate pl-5">{conv.last_message}</p>
        )}

        <div className="flex items-center gap-2 pl-5 pt-0.5 text-[10px] text-gray-400">
          <Clock className="w-2.5 h-2.5" />
          <span>
            {new Date(conv.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
          <span>•</span>
          <span>{conv.message_count} msgs</span>
          {conv.platform && (
            <Badge
              variant="outline"
              className="ml-auto bg-gray-100 text-gray-600 border-gray-200 text-[9px] px-1.5 py-0 h-4 capitalize"
            >
              {conv.platform}
            </Badge>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="relative flex h-full min-h-0 bg-white overflow-hidden">
      {/* Mobile backdrop for the conversation drawer */}
      {listOpen && (
        <div
          className="md:hidden absolute inset-0 z-20 bg-black/30"
          onClick={() => setListOpen(false)}
        />
      )}

      {/* 1. Left Conversation Sidebar (drawer on mobile, collapsible panel on desktop) */}
      <aside
        className={`${listOpen ? "flex" : "hidden"} absolute inset-y-0 left-0 z-30 w-[85%] max-w-xs md:static md:z-auto md:w-72 lg:w-80 md:max-w-none border-r border-gray-200 bg-gray-50 flex-col flex-shrink-0 min-h-0 shadow-xl md:shadow-none`}
      >
        <div className="p-3 sm:p-4 border-b border-gray-200 space-y-3 flex-shrink-0">
          <div className="flex items-center gap-2">
            <Button
              onClick={handleNewChat}
              className="flex-1 justify-start gap-2 bg-blue-600 hover:bg-blue-700 text-white shadow-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              New Conversation
            </Button>
            <button
              type="button"
              onClick={() => setListOpen(false)}
              aria-label="Close conversation list"
              className="md:hidden p-2 rounded-lg text-gray-500 hover:bg-gray-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

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

        {/* Conversation List (grouped by date, each group collapsible) */}
        <div className={`flex-1 min-h-0 overflow-y-auto p-2 space-y-2 ${THIN_SCROLL}`}>
          {filteredConversations.length === 0 ? (
            <div className="text-center py-10 px-4 text-gray-400 text-xs">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
              No conversations found. Start a new chat!
            </div>
          ) : (
            GROUP_ORDER.filter((g) => groupedConversations[g]?.length).map((group) => {
              const items = groupedConversations[group];
              const isCollapsed = !searchFilter && !!collapsedGroups[group];

              return (
                <div key={group} className="space-y-1">
                  <button
                    type="button"
                    onClick={() =>
                      setCollapsedGroups((prev) => ({ ...prev, [group]: !prev[group] }))
                    }
                    className="w-full flex items-center gap-1 px-2 py-1.5 text-[11px] font-semibold text-gray-500 hover:text-gray-800 transition-colors select-none"
                  >
                    {isCollapsed ? (
                      <ChevronRight className="w-3.5 h-3.5" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5" />
                    )}
                    <span>{group}</span>
                    <span className="text-gray-400 font-normal">({items.length})</span>
                  </button>
                  {!isCollapsed && items.map(renderConversation)}
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* 2. Main Chat Thread Panel */}
      <main className="flex-1 min-w-0 min-h-0 flex flex-col bg-white overflow-hidden">
        {/* Chat Header */}
        <header className="min-h-14 border-b border-gray-200 px-3 sm:px-4 lg:px-6 py-2 flex items-center justify-between gap-2 bg-white flex-shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setListOpen((prev) => !prev)}
              aria-label={listOpen ? "Hide conversations" : "Show conversations"}
              title={listOpen ? "Hide conversations" : "Show conversations"}
              className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition-colors flex-shrink-0"
            >
              {listOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
            </button>
            <div className="hidden sm:flex w-8 h-8 rounded-full bg-blue-50 border border-blue-200 items-center justify-center text-blue-600 flex-shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-gray-900 truncate">
                {activeConversation ? getDisplayTitle(activeConversation) : "Unified Conversational Assistant"}
              </h2>
              <p className="hidden lg:block text-[11px] text-gray-500 truncate">
                Grounded Multi-Modal RAG &amp; NL-to-SQL Query Engine
              </p>
            </div>
          </div>

          {/* Source Preference Selector */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-xs text-gray-500 font-medium hidden xl:inline">Source Engine:</span>
            <div className="inline-flex rounded-lg border border-gray-200 p-0.5 bg-gray-50 text-xs">
              {SOURCE_OPTIONS.map((opt) => {
                const Icon = opt.icon;
                const active = sourcePreference === opt.key;
                return (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => setSourcePreference(opt.key)}
                    title={opt.full}
                    className={`px-2 sm:px-2.5 py-1 rounded-md font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap ${active
                        ? "bg-white text-blue-700 shadow-xs border border-gray-200"
                        : "text-gray-600 hover:text-gray-900"
                      }`}
                  >
                    <Icon className={`w-3 h-3 ${opt.iconClass}`} />
                    <span className="hidden xl:inline">{opt.full}</span>
                    <span className="xl:hidden">{opt.short}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </header>

        {/* Message Thread Scroll Area */}
        <div
          ref={scrollRef}
          className={`flex-1 min-h-0 overflow-y-auto overflow-x-hidden p-3 sm:p-6 space-y-5 sm:space-y-6 ${THIN_SCROLL}`}
        >
          {messages.length === 0 ? (
            <div className="max-w-2xl mx-auto py-6 sm:py-12 text-center space-y-6">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center mx-auto text-white shadow-md">
                <Sparkles className="w-7 h-7" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg sm:text-xl font-bold text-gray-900">
                  How can I assist with your data today?
                </h3>
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
                        setSourcePreference(p.pref as SourcePreference);
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
            messages.map((msg, idx) => {
              const isUser = msg.sender_role === "user";
              const sources = msg.metadata_json?.sources || [];
              const sqlData = msg.metadata_json?.sql_data;
              const routeType = msg.query_type || "rag";
              const isSourcesExpanded = !!expandedSources[msg.id];

              // Long answers collapse (never while that answer is still streaming)
              const isStreamingThis = isLoading && idx === messages.length - 1 && !isUser;
              const isLong =
                !isUser &&
                !isStreamingThis &&
                (msg.content.length > LONG_MESSAGE_CHARS ||
                  msg.content.split("\n").length > LONG_MESSAGE_LINES);
              const isMsgExpanded = !!expandedMsgs[msg.id];
              const clampMsg = isLong && !isMsgExpanded;

              // SQL card state
              const sqlOpen = !!expandedSql[msg.id];
              const rowsExpanded = !!showAllRows[msg.id];
              const visibleRows = sqlData
                ? rowsExpanded
                  ? sqlData.rows
                  : sqlData.rows.slice(0, SQL_PREVIEW_ROWS)
                : [];

              return (
                <div
                  key={msg.id}
                  className={`flex gap-2 sm:gap-3 w-full max-w-3xl ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs ${isUser
                        ? "bg-blue-600 text-white font-semibold"
                        : "bg-gradient-to-tr from-blue-500 to-indigo-600 text-white shadow-xs"
                      }`}
                  >
                    {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  {/* Bubble Content */}
                  <div
                    className={`min-w-0 space-y-3 max-w-[88%] sm:max-w-[85%] ${isUser ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`p-3 sm:p-4 rounded-2xl text-xs leading-relaxed ${isUser
                          ? "bg-blue-600 text-white rounded-tr-xs"
                          : "bg-gray-50 border border-gray-200 text-gray-800 rounded-tl-xs shadow-xs"
                        }`}
                    >
                      {/* Engine Tag for Assistant */}
                      {!isUser && (
                        <div className="flex items-center justify-between gap-2 mb-2 pb-2 border-b border-gray-200">
                          <div className="flex items-center gap-1.5 flex-wrap min-w-0">
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
                            className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors flex-shrink-0"
                            title="Copy response"
                          >
                            <Copy className="w-3 h-3" />
                          </button>
                        </div>
                      )}

                      {/* Natural Language Message Body */}
                      <div className={`whitespace-pre-wrap break-words ${clampMsg ? "line-clamp-6" : ""}`}>
                        {msg.content || (!isUser && isLoading ? (
                          <span className="inline-flex items-center gap-1.5 text-gray-400 py-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse [animation-delay:150ms]" />
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse [animation-delay:300ms]" />
                            <span className="text-[11px] ml-1 text-gray-400">Thinking & streaming...</span>
                          </span>
                        ) : null)}
                      </div>

                      {isLong && (
                        <button
                          type="button"
                          onClick={() => toggleMap(setExpandedMsgs, msg.id)}
                          className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-blue-600 hover:text-blue-800"
                        >
                          {isMsgExpanded ? (
                            <>
                              Show less <ChevronUp className="w-3 h-3" />
                            </>
                          ) : (
                            <>
                              Show more <ChevronDown className="w-3 h-3" />
                            </>
                          )}
                        </button>
                      )}

                      {/* Hallucination / Low Grounding Disclaimer */}
                      {msg.metadata_json?.grounding?.disclaimer && (
                        <div className="mt-2.5 p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-[11px] flex items-start gap-2">
                          <span className="font-semibold text-xs leading-none mt-0.5">⚠️</span>
                          <span className="leading-relaxed">{msg.metadata_json.grounding.disclaimer}</span>
                        </div>
                      )}
                    </div>

                    {/* SQL Execution Card (collapsed by default) */}
                    {sqlData && sqlData.status === "success" && (
                      <div className="bg-white border border-purple-200 rounded-xl p-3 shadow-xs space-y-2 text-xs">
                        <div
                          onClick={() => toggleMap(setExpandedSql, msg.id)}
                          className="flex items-center justify-between gap-2 cursor-pointer select-none"
                        >
                          <div className="flex items-center gap-1.5 font-semibold text-purple-900 min-w-0">
                            {sqlOpen ? (
                              <ChevronDown className="w-3.5 h-3.5 text-purple-600 flex-shrink-0" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-purple-600 flex-shrink-0" />
                            )}
                            <TableIcon className="w-3.5 h-3.5 text-purple-600 flex-shrink-0" />
                            <span className="truncate">
                              Executed SQL ({sqlData.row_count} rows • {sqlData.execution_time_ms}ms)
                            </span>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              copyToClipboard(sqlData.generated_sql);
                            }}
                            className="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 font-medium flex-shrink-0"
                          >
                            <Copy className="w-3 h-3" />
                            <span className="hidden sm:inline">Copy SQL</span>
                          </button>
                        </div>

                        {sqlOpen && (
                          <div className="space-y-2 pt-2 border-t border-gray-100">
                            <pre className={`p-2.5 rounded-lg bg-gray-900 text-gray-100 font-mono text-[11px] overflow-x-auto ${THIN_SCROLL}`}>
                              {sqlData.generated_sql}
                            </pre>

                            {/* Interactive Data Table Preview */}
                            {sqlData.rows.length > 0 && (
                              <>
                                <div
                                  className={`overflow-auto max-h-56 border border-gray-200 rounded-lg ${THIN_SCROLL}`}
                                >
                                  <table className="w-full text-left text-[11px] border-collapse">
                                    <thead className="bg-gray-50 border-b border-gray-200 text-gray-700 font-semibold sticky top-0">
                                      <tr>
                                        {sqlData.columns.map((col, cIdx) => (
                                          <th
                                            key={cIdx}
                                            className="p-2 border-r border-gray-200 last:border-r-0 whitespace-nowrap"
                                          >
                                            {col}
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100">
                                      {visibleRows.map((row, rIdx) => (
                                        <tr key={rIdx} className="hover:bg-gray-50/80">
                                          {sqlData.columns.map((col, cIdx) => (
                                            <td
                                              key={cIdx}
                                              className="p-2 border-r border-gray-100 last:border-r-0 text-gray-600 whitespace-nowrap"
                                            >
                                              {row[col] !== null ? String(row[col]) : <span className="text-gray-300">NULL</span>}
                                            </td>
                                          ))}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                                {sqlData.rows.length > SQL_PREVIEW_ROWS && (
                                  <button
                                    type="button"
                                    onClick={() => toggleMap(setShowAllRows, msg.id)}
                                    className="text-[11px] font-medium text-purple-600 hover:text-purple-800"
                                  >
                                    {rowsExpanded
                                      ? "Show fewer rows"
                                      : `Show all ${sqlData.rows.length} rows`}
                                  </button>
                                )}
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Source Citations Section (if RAG chunks exist) */}
                    {sources.length > 0 && (
                      <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-xs space-y-2">
                        <div
                          onClick={() => toggleMap(setExpandedSources, msg.id)}
                          className="flex items-center justify-between gap-2 cursor-pointer text-xs font-semibold text-gray-700 hover:text-blue-600 transition-colors select-none"
                        >
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <FileText className="w-3.5 h-3.5 text-blue-600" />
                            <span>
                              Grounding Sources ({sources.length} Citation{sources.length > 1 ? "s" : ""})
                            </span>
                            {msg.metadata_json?.grounding?.confidence !== undefined && (
                              <Badge
                                variant="outline"
                                className={`text-[9px] px-1.5 py-0 h-4 ${msg.metadata_json.grounding.has_low_confidence
                                    ? "bg-amber-50 text-amber-700 border-amber-200"
                                    : "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  }`}
                              >
                                {msg.metadata_json.grounding.has_low_confidence ? "Low Grounding" : "Verified Grounding"} ({Math.round(msg.metadata_json.grounding.confidence * 100)}%)
                              </Badge>
                            )}
                          </div>
                          {isSourcesExpanded ? (
                            <ChevronUp className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          )}
                        </div>

                        {/* Collapsible Citation Cards */}
                        {isSourcesExpanded && (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-gray-100">
                            {sources.map((src, sIdx) => (
                              <div
                                key={sIdx}
                                onClick={() => setSelectedCitation(src)}
                                className="p-2.5 rounded-lg border border-gray-200 hover:border-blue-400 bg-gray-50/50 hover:bg-blue-50/30 cursor-pointer transition-all space-y-1 text-left min-w-0"
                              >
                                <div className="flex items-center justify-between gap-2 text-[11px] font-semibold text-gray-800">
                                  <span className="truncate min-w-0">{src.document_name}</span>
                                  <div className="flex items-center gap-1 flex-shrink-0">
                                    {src.page_number && (
                                      <Badge variant="secondary" className="text-[9px] px-1.5 py-0 h-4">
                                        p. {src.page_number}
                                      </Badge>
                                    )}
                                    {(src.score !== undefined || src.grounding_score !== undefined) && (
                                      <Badge
                                        variant="outline"
                                        className={`text-[9px] px-1.5 py-0 h-4 ${(src.grounding_score ?? src.score ?? 0) >= 0.65
                                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                            : "bg-gray-100 text-gray-600 border-gray-200"
                                          }`}
                                      >
                                        {Math.round((src.grounding_score ?? src.score ?? 0) * 100)}%
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
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-600 text-white flex items-center justify-center shadow-xs flex-shrink-0">
                <Bot className="w-4 h-4 animate-spin" />
              </div>
              <div className="p-3.5 rounded-2xl bg-gray-50 border border-gray-200 rounded-tl-xs shadow-xs flex items-center gap-2">
                <RefreshCw className="w-3.5 h-3.5 text-blue-600 animate-spin" />
                <span className="text-xs text-gray-600 font-medium">Synthesizing retrieval answer...</span>
              </div>
            </div>
          )}
        </div>

        {/* 3. Bottom Chat Input Box */}
        <div className="p-3 sm:p-4 border-t border-gray-200 bg-white flex-shrink-0">
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
              placeholder="Ask anything about your documents or databases..."
              disabled={isLoading}
              className="pr-24 sm:pr-12 py-3 h-12 rounded-xl text-xs bg-gray-50 border-gray-200 focus:bg-white shadow-xs"
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
          <div className="hidden sm:block text-center mt-2">
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
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-2.5 rounded-lg bg-gray-50 border border-gray-200 text-[11px]">
                <div className="min-w-0">
                  <span className="text-gray-500">Document:</span>
                  <p className="font-semibold text-gray-800 break-words">{selectedCitation.document_name}</p>
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
                <div
                  className={`p-3 bg-gray-900 text-gray-100 rounded-lg max-h-60 overflow-y-auto font-mono text-[11px] leading-relaxed whitespace-pre-wrap break-words ${THIN_SCROLL}`}
                >
                  {selectedCitation.snippet}
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button size="sm" variant="outline" onClick={() => setSelectedCitation(null)}>
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