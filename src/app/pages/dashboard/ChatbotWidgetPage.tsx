import { useState, useEffect, useMemo, useRef } from "react";
import { API_BASE_URL } from "../../config/api";
import {
  Copy,
  Check,
  RefreshCw,
  Shield,
  ShieldAlert,
  Globe,
  Database,
  Key,
  ExternalLink,
  Plus,
  Trash2,
  AlertTriangle,
  Code2,
  Sliders,
  CheckCircle2,
  Lock,
  Ban,
  Power,
  XCircle
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Switch } from "../../components/ui/switch";
import { Badge } from "../../components/ui/badge";
import { Checkbox } from "../../components/ui/checkbox";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from "../../components/ui/alert-dialog";
import { toast } from "sonner";

interface WidgetKeyData {
  id: number;
  tenant_id: number;
  public_key: string;
  name: string;
  allowed_origins: string[];
  enabled: boolean;
  monthly_message_cap: number;
  allow_sql: boolean;
  allowed_database_ids: number[];
  previous_key?: string | null;
  previous_key_expires_at?: string | null;
  created_at: string;
  updated_at?: string | null;
}

interface DatabaseConnection {
  id: number;
  name: string;
  db_type: string;
  database?: string;
  status?: string;
}

export function ChatbotWidgetPage() {
  // Widget Appearance & Behavior Config
  const [themeColor, setThemeColor] = useState("#3b82f6");
  const [greetingMessage, setGreetingMessage] = useState(
    "Hi! I'm your AI assistant. Ask me anything about your data."
  );
  const [position, setPosition] = useState<"bottom-right" | "bottom-left">("bottom-right");
  const [welcomeDelay, setWelcomeDelay] = useState(3);
  const [maxHistory, setMaxHistory] = useState(10);
  const [widgetTitle, setWidgetTitle] = useState("AI Assistant");
  const [soundEnabled, setSoundEnabled] = useState(true);

  // Widget Publishable Key & Security
  const [widgetKey, setWidgetKey] = useState<WidgetKeyData | null>(null);
  const [originsList, setOriginsList] = useState<string[]>([]);
  const [newOriginInput, setNewOriginInput] = useState("");
  const [allowSql, setAllowSql] = useState(false);
  const [allowedDbIds, setAllowedDbIds] = useState<number[]>([]);
  const [connectedDatabases, setConnectedDatabases] = useState<DatabaseConnection[]>([]);

  // UI States
  const [isSavingConfig, setIsSavingConfig] = useState(false);
  const [isSavingSecurity, setIsSavingSecurity] = useState(false);
  const [isRotating, setIsRotating] = useState(false);
  const [isRevoking, setIsRevoking] = useState(false);
  const [isReenabling, setIsReenabling] = useState(false);
  const [isRevokeDialogOpen, setIsRevokeDialogOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [copiedIframe, setCopiedIframe] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [previewReloadKey, setPreviewReloadKey] = useState(0);

  const previewIframeRef = useRef<HTMLIFrameElement>(null);

  // Fetch initial data: Config, Widget Key, Databases
  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setIsLoading(true);
    const token = localStorage.getItem("token");
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      // 1. Fetch Chatbot Config
      const configRes = await fetch(`${API_BASE_URL}/api/chatbot-config`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (configRes.ok) {
        const cfg = await configRes.json();
        setThemeColor(cfg.theme_color || "#3b82f6");
        setGreetingMessage(cfg.greeting_message || "Hi! I'm your AI assistant. Ask me anything about your data.");
        setPosition((cfg.position as any) || "bottom-right");
        setWelcomeDelay(cfg.welcome_delay ?? 3);
        setMaxHistory(cfg.max_history ?? 10);
        setWidgetTitle(cfg.widget_title || "AI Assistant");
        setSoundEnabled(cfg.sound_enabled ?? true);
      }

      // 2. Fetch Databases for SQL Allowlist
      const dbRes = await fetch(`${API_BASE_URL}/api/databases`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (dbRes.ok) {
        const dbs = await dbRes.json();
        setConnectedDatabases(dbs || []);
      }

      // 3. Fetch or Initialize Widget Publishable Key
      const keysRes = await fetch(`${API_BASE_URL}/api/keys/widget`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (keysRes.ok) {
        const keys: WidgetKeyData[] = await keysRes.json();
        if (keys && keys.length > 0) {
          const activeKey = keys[0];
          setWidgetKey(activeKey);
          setOriginsList(activeKey.allowed_origins || []);
          setAllowSql(activeKey.allow_sql || false);
          setAllowedDbIds(activeKey.allowed_database_ids || []);
        } else {
          // Auto-create initial publishable widget key with current browser origin
          const currentOrigin = window.location.origin;
          const createRes = await fetch(`${API_BASE_URL}/api/keys/widget`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
              name: "Default Website Widget",
              allowed_origins: [currentOrigin],
              monthly_message_cap: 2500,
              allow_sql: false,
              allowed_database_ids: []
            })
          });
          if (createRes.ok) {
            const createdKey: WidgetKeyData = await createRes.json();
            setWidgetKey(createdKey);
            setOriginsList(createdKey.allowed_origins || []);
            setAllowSql(createdKey.allow_sql || false);
            setAllowedDbIds(createdKey.allowed_database_ids || []);
          }
        }
      }
    } catch (err) {
      console.error("Failed to load chatbot widget configuration:", err);
      toast.error("Could not load chatbot configuration");
    } finally {
      setIsLoading(false);
    }
  };

  // Save Appearance & Behavior
  const handleSaveConfig = async () => {
    setIsSavingConfig(true);
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/chatbot-config`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          theme_color: themeColor,
          greeting_message: greetingMessage,
          position,
          welcome_delay: welcomeDelay,
          max_history: maxHistory,
          widget_title: widgetTitle,
          sound_enabled: soundEnabled
        })
      });

      if (!res.ok) throw new Error("Failed to save appearance");

      toast.success("Widget configuration updated!");
      // Reload preview to show new config
      setPreviewReloadKey((k) => k + 1);
    } catch (err) {
      console.error("Save config error:", err);
      toast.error("Failed to save widget configuration");
    } finally {
      setIsSavingConfig(false);
    }
  };

  // Save Security Settings (Origins + SQL Policy)
  const handleSaveSecurity = async () => {
    if (!widgetKey) return;
    setIsSavingSecurity(true);
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/keys/widget/${widgetKey.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          allowed_origins: originsList,
          allow_sql: allowSql,
          allowed_database_ids: allowedDbIds
        })
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to update security rules");
      }

      const updated = await res.json();
      setWidgetKey(updated);
      setOriginsList(updated.allowed_origins || []);
      setAllowSql(updated.allow_sql || false);
      setAllowedDbIds(updated.allowed_database_ids || []);
      toast.success("Security & access rules saved successfully!");
      setPreviewReloadKey((k) => k + 1);
    } catch (err: any) {
      console.error("Save security error:", err);
      toast.error(err.message || "Failed to save security settings");
    } finally {
      setIsSavingSecurity(false);
    }
  };

  // Rotate Key
  const handleRotateKey = async () => {
    if (!widgetKey) return;
    const confirmRotate = window.confirm(
      "Rotate this publishable key? A new public key will be generated immediately.\n\nYour previous key will remain valid for a 24-hour grace window to prevent any downtime while updating host websites."
    );
    if (!confirmRotate) return;

    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Authentication required");
      return;
    }

    setIsRotating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/keys/widget/${widgetKey.id}/rotate`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) throw new Error("Failed to rotate key");

      const rotData = await res.json();
      setWidgetKey((prev) =>
        prev
          ? {
              ...prev,
              public_key: rotData.new_key,
              previous_key: rotData.previous_key,
              previous_key_expires_at: rotData.previous_key_expires_at,
              enabled: true
            }
          : null
      );
      toast.success("Widget key rotated! 24-hour grace window active for old key.");
      setPreviewReloadKey((k) => k + 1);
    } catch (err) {
      console.error("Key rotation error:", err);
      toast.error("Failed to rotate key");
    } finally {
      setIsRotating(false);
    }
  };

  // Revoke Key (SEC-08)
  const handleRevokeKey = async () => {
    if (!widgetKey) return;
    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Authentication required");
      return;
    }

    setIsRevoking(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/keys/widget/${widgetKey.id}/revoke`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}` }
      });

      if (!res.ok) throw new Error("Failed to revoke key");

      const updated = await res.json();
      setWidgetKey(updated);
      toast.success("Widget key has been revoked. All active sessions are terminated.");
      setPreviewReloadKey((k) => k + 1);
    } catch (err: any) {
      console.error("Revoke key error:", err);
      toast.error(err.message || "Failed to revoke key");
    } finally {
      setIsRevoking(false);
      setIsRevokeDialogOpen(false);
    }
  };

  // Re-enable Key
  const handleReenableKey = async () => {
    if (!widgetKey) return;
    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Authentication required");
      return;
    }

    setIsReenabling(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/keys/widget/${widgetKey.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ enabled: true })
      });

      if (!res.ok) throw new Error("Failed to re-enable key");

      const updated = await res.json();
      setWidgetKey(updated);
      toast.success("Widget key re-enabled successfully!");
      setPreviewReloadKey((k) => k + 1);
    } catch (err: any) {
      console.error("Re-enable key error:", err);
      toast.error(err.message || "Failed to re-enable key");
    } finally {
      setIsReenabling(false);
    }
  };

  // Origin List Management
  const handleAddOrigin = () => {
    const trimmed = newOriginInput.trim();
    if (!trimmed) return;

    if (trimmed === "*") {
      toast.error("Wildcard '*' origins are forbidden for widget security.");
      return;
    }

    if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
      toast.error("Origin must include scheme (e.g., https://example.com or http://localhost:3000)");
      return;
    }

    const normalized = trimmed.replace(/\/+$/, "");
    if (originsList.includes(normalized)) {
      toast.info("Origin is already in the allowlist.");
      setNewOriginInput("");
      return;
    }

    setOriginsList([...originsList, normalized]);
    setNewOriginInput("");
  };

  const handleAddCurrentOrigin = () => {
    const cur = window.location.origin;
    if (!originsList.includes(cur)) {
      setOriginsList([...originsList, cur]);
      toast.success(`Added ${cur} to allowlist`);
    } else {
      toast.info("Current origin is already in allowlist");
    }
  };

  const handleRemoveOrigin = (index: number) => {
    setOriginsList(originsList.filter((_, i) => i !== index));
  };

  // Toggle Database Selection for SQL
  const handleToggleDb = (dbId: number) => {
    if (allowedDbIds.includes(dbId)) {
      setAllowedDbIds(allowedDbIds.filter((id) => id !== dbId));
    } else {
      setAllowedDbIds([...allowedDbIds, dbId]);
    }
  };

  // Generated Snippets
  const scriptSnippet = useMemo(() => {
    const key = widgetKey ? widgetKey.public_key : "pk_live_your_widget_key";
    return `<!-- DataSpeakAI Standalone Chatbot Widget -->\n<script \n  src="${API_BASE_URL}/widget.js" \n  data-key="${key}" \n  async\n></script>`;
  }, [widgetKey]);

  const iframeSnippet = useMemo(() => {
    const key = widgetKey ? widgetKey.public_key : "pk_live_your_widget_key";
    return `<iframe \n  src="${API_BASE_URL}/embed/${key}" \n  width="400" \n  height="640" \n  style="border:none; border-radius:16px; box-shadow:0 10px 25px rgba(0,0,0,0.15);" \n  allow="clipboard-write"\n></iframe>`;
  }, [widgetKey]);

  const copyScriptSnippet = () => {
    navigator.clipboard.writeText(scriptSnippet);
    setCopiedSnippet(true);
    toast.success("Script tag copied to clipboard!");
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const copyIframeSnippet = () => {
    navigator.clipboard.writeText(iframeSnippet);
    setCopiedIframe(true);
    toast.success("Iframe snippet copied to clipboard!");
    setTimeout(() => setCopiedIframe(false), 2000);
  };

  const copyPublicKey = () => {
    if (!widgetKey) return;
    navigator.clipboard.writeText(widgetKey.public_key);
    setCopiedKey(true);
    toast.success("Public key copied!");
    setTimeout(() => setCopiedKey(false), 2000);
  };

  // Sandbox HTML for the Real /widget.js Live Preview
  const sandboxSrcDoc = useMemo(() => {
    const pubKey = widgetKey ? widgetKey.public_key : "";
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Host Website Preview</title>
  <style>
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 24px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%);
      color: #334155;
      min-height: 100vh;
      overflow-x: hidden;
    }
    .preview-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
      max-width: 420px;
    }
    .tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 4px 10px;
      border-radius: 9999px;
      background: #e0f2fe;
      color: #0369a1;
      margin-bottom: 14px;
    }
    h2 {
      margin: 0 0 10px 0;
      font-size: 18px;
      font-weight: 700;
      color: #0f172a;
    }
    p {
      margin: 0 0 18px 0;
      font-size: 13px;
      line-height: 1.6;
      color: #64748b;
    }
    .bar {
      height: 8px;
      border-radius: 4px;
      background: #f1f5f9;
      margin-bottom: 8px;
    }
  </style>
</head>
<body>
  <div class="preview-card">
    <div class="tag">● Simulated Host Website</div>
    <h2>Customer Portal Preview</h2>
    <p>This frame simulates your live website. The button in the corner is rendered directly by the standalone <code>widget.js</code> bundle inside an open Shadow DOM root.</p>
    <div class="bar" style="width: 90%;"></div>
    <div class="bar" style="width: 75%;"></div>
    <div class="bar" style="width: 50%;"></div>
  </div>

  <!-- Real Standalone Chatbot Script -->
  <script src="${API_BASE_URL}/widget.js" data-key="${pubKey}" data-api="${API_BASE_URL}" async></script>
</body>
</html>`;
  }, [widgetKey, previewReloadKey]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">Standalone Chatbot Widget</h1>
            <Badge variant="outline" className="border-blue-200 text-blue-700 bg-blue-50/50">
              Phase 2 Enterprise
            </Badge>
          </div>
          <p className="text-sm text-gray-600 mt-1">
            Embed an ultra-lightweight (&lt;32 KB), non-invasive AI chatbot onto any website with strict origin allowlisting and multi-tenant security.
          </p>
        </div>

        {/* Public Key Display & Actions */}
        {widgetKey && (
          <div className="flex items-center gap-2 bg-gray-50 border rounded-xl p-2.5 shadow-sm">
            <div className="flex flex-col text-right">
              <div className="flex items-center gap-1.5 justify-end">
                <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider">Publishable Key</span>
                {widgetKey.enabled ? (
                  <span className="inline-flex items-center px-1.5 py-0.2 rounded-full text-[9px] font-semibold bg-emerald-100 text-emerald-800">
                    Active
                  </span>
                ) : (
                  <span className="inline-flex items-center px-1.5 py-0.2 rounded-full text-[9px] font-semibold bg-rose-100 text-rose-800">
                    Revoked
                  </span>
                )}
              </div>
              <span className="font-mono text-xs font-semibold text-gray-700">
                {widgetKey.public_key.substring(0, 14)}...{widgetKey.public_key.slice(-6)}
              </span>
            </div>
            <Button size="sm" variant="ghost" className="h-8 px-2" onClick={copyPublicKey}>
              {copiedKey ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5 text-gray-600" />}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 gap-1.5 text-xs font-medium text-amber-700 border-amber-300 hover:bg-amber-50"
              onClick={handleRotateKey}
              disabled={isRotating}
            >
              <RefreshCw className={`w-3 h-3 ${isRotating ? "animate-spin" : ""}`} />
              Rotate
            </Button>
            {widgetKey.enabled ? (
              <AlertDialog open={isRevokeDialogOpen} onOpenChange={setIsRevokeDialogOpen}>
                <AlertDialogTrigger asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 gap-1.5 text-xs font-medium text-rose-700 border-rose-300 hover:bg-rose-50"
                    disabled={isRevoking}
                  >
                    <Ban className="w-3 h-3" />
                    Revoke
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle className="text-red-600 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5" /> Revoke Publishable Widget Key?
                    </AlertDialogTitle>
                    <AlertDialogDescription className="space-y-2 text-sm text-slate-600">
                      <p>
                        Revoking this key immediately disables the chatbot widget on all external websites.
                      </p>
                      <p className="font-medium text-slate-800">
                        All active sessions and visitor connections will be blocked immediately.
                      </p>
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleRevokeKey}
                      className="bg-red-600 hover:bg-red-700 text-white"
                    >
                      {isRevoking ? "Revoking..." : "Yes, Revoke Key"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="h-8 gap-1.5 text-xs font-medium text-emerald-700 border-emerald-300 hover:bg-emerald-50"
                onClick={handleReenableKey}
                disabled={isReenabling}
              >
                <Power className="w-3 h-3" />
                {isReenabling ? "Enabling..." : "Re-enable"}
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Revoked / Inactive Key Banner (SEC-08) */}
      {widgetKey && !widgetKey.enabled && (
        <div className="p-4 bg-rose-50 border border-rose-300 rounded-xl flex items-start justify-between gap-3 text-rose-900 animate-in fade-in">
          <div className="flex items-start gap-3">
            <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="space-y-1 text-sm">
              <span className="font-bold">Widget Key is Revoked & Inactive! </span>
              <p className="text-xs text-rose-800/90 leading-relaxed">
                Anonymous visitors on external websites cannot initialize chat sessions or execute queries. Re-enable this key or rotate to generate a new active publishable key.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <Button size="sm" variant="outline" className="bg-white text-xs h-8 border-rose-300 text-rose-700 hover:bg-rose-100" onClick={handleReenableKey} disabled={isReenabling}>
              <Power className="w-3.5 h-3.5 mr-1" /> Re-enable Key
            </Button>
            <Button size="sm" className="bg-rose-600 hover:bg-rose-700 text-white text-xs h-8" onClick={handleRotateKey} disabled={isRotating}>
              <RefreshCw className="w-3.5 h-3.5 mr-1" /> Rotate to New Key
            </Button>
          </div>
        </div>
      )}

      {/* Warning Banner: Allowlist is Empty */}
      {originsList.length === 0 && (
        <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl flex items-start gap-3 text-amber-900 animate-in fade-in">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-sm">
            <span className="font-bold">Widget Allowlist is Empty! </span>
            Requests from all external websites will be blocked with HTTP 403. Add your production domain or click below to enable the widget.
            <div className="mt-2">
              <Button size="sm" variant="outline" className="bg-white text-xs h-7 gap-1" onClick={handleAddCurrentOrigin}>
                <Plus className="w-3 h-3" /> Add Current Origin ({window.location.origin})
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Grace Window Notice */}
      {widgetKey?.previous_key && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between text-xs text-blue-900">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-blue-600 shrink-0" />
            <span>
              <strong>Key Rotation Grace Window Active:</strong> Your previous key (<code>{widgetKey.previous_key.substring(0, 12)}...</code>) remains valid until{" "}
              {widgetKey.previous_key_expires_at ? new Date(widgetKey.previous_key_expires_at).toLocaleTimeString() : "24 hours"}.
            </span>
          </div>
        </div>
      )}

      {/* Main Grid: Settings & Live Preview */}
      <div className="grid lg:grid-cols-12 gap-8 items-start">
        {/* Left Side: Configuration Tabs (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <Tabs defaultValue="snippet" className="w-full">
            <TabsList className="grid grid-cols-4 w-full">
              <TabsTrigger value="snippet" className="text-xs gap-1.5">
                <Code2 className="w-3.5 h-3.5" /> Embed Code
              </TabsTrigger>
              <TabsTrigger value="origins" className="text-xs gap-1.5">
                <Globe className="w-3.5 h-3.5" /> Allowed Origins
              </TabsTrigger>
              <TabsTrigger value="security" className="text-xs gap-1.5">
                <Database className="w-3.5 h-3.5" /> Data & SQL
              </TabsTrigger>
              <TabsTrigger value="appearance" className="text-xs gap-1.5">
                <Sliders className="w-3.5 h-3.5" /> Appearance
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: Embed Snippet */}
            <TabsContent value="snippet" className="space-y-4 mt-4">
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-semibold">Production Embed Snippet</CardTitle>
                    <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px]">
                      Shadow DOM IIFE
                    </Badge>
                  </div>
                  <CardDescription className="text-xs">
                    Paste this snippet before the closing <code>&lt;/body&gt;</code> tag on your website. It loads synchronously at under 12 KB gzipped.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="relative group">
                    <pre className="bg-slate-950 text-slate-100 p-4 rounded-xl text-xs font-mono overflow-x-auto border border-slate-800 shadow-inner">
                      <code>{scriptSnippet}</code>
                    </pre>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="absolute top-3 right-3 gap-1.5 text-xs bg-white/10 hover:bg-white/20 text-white border border-white/10"
                      onClick={copyScriptSnippet}
                    >
                      {copiedSnippet ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
                      {copiedSnippet ? "Copied" : "Copy Snippet"}
                    </Button>
                  </div>

                  {/* Architecture & Security Guarantees */}
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="p-3 bg-slate-50 border rounded-lg text-xs space-y-1">
                      <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                        <Lock className="w-3.5 h-3.5 text-blue-600" /> Zero Secret Leakage
                      </div>
                      <p className="text-slate-500 text-[11px] leading-relaxed">
                        Uses a publishable key (<code>pk_live_</code>). Your database credentials and tenant secret tokens are never exposed.
                      </p>
                    </div>
                    <div className="p-3 bg-slate-50 border rounded-lg text-xs space-y-1">
                      <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                        <Shield className="w-3.5 h-3.5 text-emerald-600" /> CSS Isolation
                      </div>
                      <p className="text-slate-500 text-[11px] leading-relaxed">
                        Mounted inside an open Shadow DOM root with pixel-pinned sizing. Host styles cannot break the widget.
                      </p>
                    </div>
                  </div>

                  {/* Iframe Fallback Section */}
                  <div className="border-t pt-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs font-medium text-slate-700">Optional Fallback: Full Iframe Embed</Label>
                      <Button size="sm" variant="ghost" className="h-6 text-[11px] text-blue-600 px-2" onClick={copyIframeSnippet}>
                        {copiedIframe ? "Copied" : "Copy Iframe"}
                      </Button>
                    </div>
                    <pre className="bg-slate-900 text-slate-200 p-3 rounded-lg text-[11px] font-mono overflow-x-auto border border-slate-800">
                      <code>{iframeSnippet}</code>
                    </pre>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* TAB 2: Allowed Origins */}
            <TabsContent value="origins" className="space-y-4 mt-4">
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-semibold">Origin Allowlist</CardTitle>
                    <Badge variant="outline" className="text-xs">
                      {originsList.length} Allowed
                    </Badge>
                  </div>
                  <CardDescription className="text-xs">
                    Strict CORS & HMAC origin protection. The widget only opens and exchanges tokens for domains listed here.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Add Origin Input */}
                  <div className="flex gap-2">
                    <Input
                      placeholder="https://example.com or http://localhost:3000"
                      value={newOriginInput}
                      onChange={(e) => setNewOriginInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleAddOrigin()}
                      className="text-xs"
                    />
                    <Button size="sm" onClick={handleAddOrigin} className="gap-1 shrink-0">
                      <Plus className="w-3.5 h-3.5" /> Add
                    </Button>
                  </div>

                  <div className="flex items-center justify-between">
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-xs h-7 gap-1 text-slate-600"
                      onClick={handleAddCurrentOrigin}
                    >
                      <Plus className="w-3 h-3" /> Quick Add Current Origin ({window.location.origin})
                    </Button>
                  </div>

                  {/* Current List */}
                  <div className="border rounded-xl divide-y bg-slate-50/50 max-h-56 overflow-y-auto">
                    {originsList.length === 0 ? (
                      <div className="p-4 text-center text-xs text-slate-400">
                        No origins configured. Widget is currently blocked on all external domains.
                      </div>
                    ) : (
                      originsList.map((origin, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 text-xs">
                          <div className="flex items-center gap-2">
                            <Globe className="w-3.5 h-3.5 text-blue-500" />
                            <span className="font-mono font-medium text-slate-700">{origin}</span>
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-7 w-7 p-0 text-slate-400 hover:text-red-600"
                            onClick={() => handleRemoveOrigin(idx)}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      ))
                    )}
                  </div>

                  <Button className="w-full" onClick={handleSaveSecurity} disabled={isSavingSecurity}>
                    {isSavingSecurity ? "Saving Allowlist..." : "Save Origin Allowlist"}
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            {/* TAB 3: Data-Access & SQL Policy */}
            <TabsContent value="security" className="space-y-4 mt-4">
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base font-semibold">Data-Access Security & SQL Policy</CardTitle>
                    <Badge variant={allowSql ? "destructive" : "secondary"} className="text-xs">
                      {allowSql ? "SQL Mode Enabled" : "RAG-Only Mode"}
                    </Badge>
                  </div>
                  <CardDescription className="text-xs">
                    Control whether anonymous visitors are permitted to query connected SQL databases or only uploaded documents.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-5">
                  {/* Allow SQL Switch */}
                  <div className="flex items-center justify-between p-4 bg-slate-50 border rounded-xl">
                    <div className="space-y-0.5 pr-4">
                      <Label className="text-sm font-semibold text-slate-900">Enable Natural Language SQL Mode</Label>
                      <p className="text-xs text-slate-500 leading-relaxed">
                        When enabled, visitors can ask questions that trigger natural language queries against selected databases.
                      </p>
                    </div>
                    <Switch checked={allowSql} onCheckedChange={setAllowSql} />
                  </div>

                  {/* Warning / Guardrail Notice */}
                  {allowSql ? (
                    <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl space-y-2 text-xs text-amber-900">
                      <div className="flex items-center gap-2 font-bold text-amber-800">
                        <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
                        SQL Security Guardrails Active
                      </div>
                      <p className="leading-relaxed">
                        DataSpeakAI deterministically validates all generated SQL:
                      </p>
                      <ul className="list-disc pl-5 space-y-1 text-amber-800/90 text-[11px]">
                        <li>DDL/DML keywords (DROP, DELETE, UPDATE, INSERT, ALTER) are strictly rejected.</li>
                        <li>Multi-statement and stacked queries (semicolon tricks) are blocked.</li>
                        <li>Queries execute through read-only connections capped at 100 preview rows.</li>
                        <li>Sensitive PII columns (passwords, tokens, SSNs) are automatically masked.</li>
                        <li>Visitors receive synthesized natural language answers, never raw database credentials.</li>
                      </ul>
                    </div>
                  ) : (
                    <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-xs text-emerald-900">
                      <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                      <div>
                        <strong>Safe RAG-Only Mode:</strong> Visitors are restricted strictly to indexing and querying your uploaded document knowledge base. Connected databases are completely inaccessible.
                      </div>
                    </div>
                  )}

                  {/* Database Checkboxes (Shown if SQL allowed) */}
                  {allowSql && (
                    <div className="space-y-3 pt-1">
                      <Label className="text-xs font-semibold text-slate-800">Permitted Database Connections</Label>
                      {connectedDatabases.length === 0 ? (
                        <p className="text-xs text-slate-400 italic">
                          No connected databases found. Connect databases in the Databases tab first.
                        </p>
                      ) : (
                        <div className="space-y-2 border rounded-xl p-3 bg-slate-50/50 max-h-48 overflow-y-auto">
                          {connectedDatabases.map((db) => (
                            <div key={db.id} className="flex items-center space-x-2 text-xs">
                              <Checkbox
                                id={`db-${db.id}`}
                                checked={allowedDbIds.includes(db.id)}
                                onCheckedChange={() => handleToggleDb(db.id)}
                              />
                              <Label htmlFor={`db-${db.id}`} className="font-normal cursor-pointer flex items-center gap-2">
                                <span className="font-medium text-slate-800">{db.name}</span>
                                <Badge variant="outline" className="text-[10px] py-0 px-1.5 uppercase font-mono">
                                  {db.db_type}
                                </Badge>
                              </Label>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <Button className="w-full" onClick={handleSaveSecurity} disabled={isSavingSecurity}>
                    {isSavingSecurity ? "Saving Security..." : "Save Data-Access Policy"}
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>

            {/* TAB 4: Appearance & Behavior */}
            <TabsContent value="appearance" className="space-y-4 mt-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Branding & Interaction</CardTitle>
                  <CardDescription className="text-xs">
                    Customize your chatbot's launcher color, greeting, position, and conversation behavior.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Theme Color */}
                  <div className="space-y-2">
                    <Label htmlFor="theme-color" className="text-xs font-semibold">
                      Theme Color
                    </Label>
                    <div className="flex gap-2">
                      <Input
                        id="theme-color"
                        type="color"
                        value={themeColor}
                        onChange={(e) => setThemeColor(e.target.value)}
                        className="w-14 h-9 p-1 cursor-pointer"
                      />
                      <Input
                        value={themeColor}
                        onChange={(e) => setThemeColor(e.target.value)}
                        className="font-mono text-xs flex-1"
                      />
                    </div>
                  </div>

                  {/* Position */}
                  <div className="space-y-2">
                    <Label className="text-xs font-semibold">Widget Position</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        type="button"
                        variant={position === "bottom-right" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setPosition("bottom-right")}
                        className="text-xs"
                      >
                        Bottom Right
                      </Button>
                      <Button
                        type="button"
                        variant={position === "bottom-left" ? "default" : "outline"}
                        size="sm"
                        onClick={() => setPosition("bottom-left")}
                        className="text-xs"
                      >
                        Bottom Left
                      </Button>
                    </div>
                  </div>

                  {/* Widget Title */}
                  <div className="space-y-2">
                    <Label htmlFor="title" className="text-xs font-semibold">
                      Widget Header Title
                    </Label>
                    <Input
                      id="title"
                      value={widgetTitle}
                      onChange={(e) => setWidgetTitle(e.target.value)}
                      placeholder="AI Data Assistant"
                      className="text-xs"
                    />
                  </div>

                  {/* Greeting Message */}
                  <div className="space-y-2">
                    <Label htmlFor="greeting" className="text-xs font-semibold">
                      Greeting Message
                    </Label>
                    <Textarea
                      id="greeting"
                      value={greetingMessage}
                      onChange={(e) => setGreetingMessage(e.target.value)}
                      rows={3}
                      className="text-xs"
                    />
                  </div>

                  {/* Behavior options */}
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="delay" className="text-xs font-semibold">
                        Welcome Delay (s)
                      </Label>
                      <Input
                        id="delay"
                        type="number"
                        min="0"
                        max="30"
                        value={welcomeDelay}
                        onChange={(e) => setWelcomeDelay(Number(e.target.value))}
                        className="text-xs"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="history" className="text-xs font-semibold">
                        Max History Messages
                      </Label>
                      <Input
                        id="history"
                        type="number"
                        min="2"
                        max="50"
                        value={maxHistory}
                        onChange={(e) => setMaxHistory(Number(e.target.value))}
                        className="text-xs"
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <div className="space-y-0.5">
                      <Label className="text-xs font-semibold">Sound Notifications</Label>
                      <p className="text-[11px] text-slate-500">Play chime when responses complete</p>
                    </div>
                    <Switch checked={soundEnabled} onCheckedChange={setSoundEnabled} />
                  </div>

                  <Button className="w-full mt-2" onClick={handleSaveConfig} disabled={isSavingConfig}>
                    {isSavingConfig ? "Saving Configuration..." : "Save Appearance & Branding"}
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Side: Real Standalone /widget.js Live Preview (5 cols) */}
        <div className="lg:col-span-5 sticky top-6 space-y-3">
          <Card className="overflow-hidden shadow-lg border-slate-200">
            <CardHeader className="bg-slate-50 border-b py-3 px-4 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Live Sandbox Preview
                </CardTitle>
                <p className="text-[10px] text-slate-500 mt-0.5">Powered by real /widget.js bundle</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs gap-1.5 px-2 bg-white"
                onClick={() => setPreviewReloadKey((k) => k + 1)}
              >
                <RefreshCw className="w-3 h-3 text-slate-500" />
                Reload
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="w-full h-[620px] bg-slate-100 relative">
                <iframe
                  ref={previewIframeRef}
                  key={previewReloadKey}
                  srcDoc={sandboxSrcDoc}
                  title="DataSpeakAI Standalone Chatbot Widget Preview"
                  className="w-full h-full border-none"
                  sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
