import { useState, useEffect } from "react";
import { API_BASE_URL } from "../../config/api";
import { Copy, Check, MessageSquare, X } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { Switch } from "../../components/ui/switch";
import { toast } from "sonner";

export function ChatbotWidgetPage() {
  const [copied, setCopied] = useState(false);
  const [themeColor, setThemeColor] = useState("#3b82f6");
  const [greetingMessage, setGreetingMessage] = useState(
    "Hi! I'm your AI assistant. Ask me anything about your data."
  );
  const [position, setPosition] = useState<"bottom-right" | "bottom-left">("bottom-right");
  const [welcomeDelay, setWelcomeDelay] = useState(3);
  const [maxHistory, setMaxHistory] = useState(10);
  const [widgetTitle, setWidgetTitle] = useState("AI Assistant");
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(true);

  useEffect(() => {
    const fetchConfig = async () => {
      const token = localStorage.getItem("token");
      if (!token) return;

      try {
        const response = await fetch(`${API_BASE_URL}/api/chatbot-config`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (response.ok) {
          const data = await response.json();
          setThemeColor(data.theme_color);
          setGreetingMessage(data.greeting_message);
          setPosition(data.position as any);
          setWelcomeDelay(data.welcome_delay);
          setMaxHistory(data.max_history);
          setWidgetTitle(data.widget_title || "AI Assistant");
          setSoundEnabled(data.sound_enabled ?? true);
        }
      } catch (error) {
        console.error("Failed to fetch chatbot config:", error);
      }
    };
    fetchConfig();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      await fetch(`${API_BASE_URL}/api/chatbot-config`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
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
      toast.success("Configuration saved successfully");
    } catch (error) {
      console.error("Failed to save config:", error);
      toast.error("Failed to save configuration");
    } finally {
      setIsSaving(false);
    }
  };

  const embedCode = `<!-- OmniQuery AI Chatbot Widget -->
<script src="https://cdn.omniquery.ai/widget.js"></script>
<script>
  OmniQueryAI.init({
    apiKey: "YOUR_API_KEY",
    themeColor: "${themeColor}",
    widgetTitle: "${widgetTitle}",
    greeting: "${greetingMessage}",
    position: "${position}"
  });
</script>`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(embedCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold mb-2">Chatbot Widget</h1>
        <p className="text-gray-600">
          Customize and embed your AI chatbot on your website
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Configuration */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Widget Configuration</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <Tabs defaultValue="appearance">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="appearance">Appearance</TabsTrigger>
                  <TabsTrigger value="behavior">Behavior</TabsTrigger>
                </TabsList>

                <TabsContent value="appearance" className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label htmlFor="theme-color">Theme Color</Label>
                    <div className="flex gap-2">
                      <Input
                        id="theme-color"
                        type="color"
                        value={themeColor}
                        onChange={(e) => setThemeColor(e.target.value)}
                        className="w-20 h-10"
                      />
                      <Input
                        value={themeColor}
                        onChange={(e) => setThemeColor(e.target.value)}
                        className="flex-1"
                      />
                    </div>
                    <p className="text-xs text-gray-600">
                      Choose the primary color for your chatbot widget
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Position</Label>
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        variant={
                          position === "bottom-right" ? "default" : "outline"
                        }
                        onClick={() => setPosition("bottom-right")}
                        className="w-full"
                      >
                        Bottom Right
                      </Button>
                      <Button
                        variant={
                          position === "bottom-left" ? "default" : "outline"
                        }
                        onClick={() => setPosition("bottom-left")}
                        className="w-full"
                      >
                        Bottom Left
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="greeting">Greeting Message</Label>
                    <Textarea
                      id="greeting"
                      value={greetingMessage}
                      onChange={(e) => setGreetingMessage(e.target.value)}
                      rows={3}
                      placeholder="Enter your greeting message..."
                    />
                    <p className="text-xs text-gray-600">
                      This message will be shown when the chatbot opens
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="widget-title">Widget Title</Label>
                    <Input
                      id="widget-title"
                      value={widgetTitle}
                      onChange={(e) => setWidgetTitle(e.target.value)}
                      placeholder="e.g. AI Assistant"
                    />
                    <p className="text-xs text-gray-600">
                      The name displayed in the chatbot header
                    </p>
                  </div>
                </TabsContent>

                <TabsContent value="behavior" className="space-y-4 mt-4">
                  <div className="space-y-2">
                    <Label htmlFor="welcome-delay">Welcome Delay (seconds)</Label>
                    <Input
                      id="welcome-delay"
                      type="number"
                      value={welcomeDelay}
                      onChange={(e) => setWelcomeDelay(Number(e.target.value))}
                      min="0"
                      max="30"
                    />
                    <p className="text-xs text-gray-600">
                      Time before showing the welcome message
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="max-history">Conversation History</Label>
                    <Input
                      id="max-history"
                      type="number"
                      value={maxHistory}
                      onChange={(e) => setMaxHistory(Number(e.target.value))}
                      min="5"
                      max="50"
                    />
                    <p className="text-xs text-gray-600">
                      Number of previous messages to remember
                    </p>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Sound Notifications</Label>
                      <p className="text-xs text-gray-600">
                        Play sound when new message arrives
                      </p>
                    </div>
                    <Switch
                      checked={soundEnabled}
                      onCheckedChange={setSoundEnabled}
                    />
                  </div>
                </TabsContent>
              </Tabs>

              <Button 
                className="w-full" 
                onClick={handleSave} 
                disabled={isSaving}
              >
                {isSaving ? "Saving..." : "Save Configuration"}
              </Button>
            </CardContent>
          </Card>

          {/* Embed Code */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Embed Code</CardTitle>
                <div className="px-2 py-1 bg-green-100 text-green-700 text-[10px] font-bold uppercase rounded tracking-wider">Production Ready</div>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                <p className="text-sm text-gray-600 leading-relaxed">
                  To install the chatbot on your website, copy and paste this snippet before the closing{" "}
                  <code className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono text-pink-600">
                    &lt;/body&gt;
                  </code>{" "}
                  tag.
                </p>
 
                <div className="group relative">
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-gray-200 to-gray-100 rounded-xl blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
                  <div className="relative">
                    <pre className="bg-gray-950 text-gray-300 p-5 rounded-xl text-xs font-mono overflow-x-auto border border-gray-800 shadow-2xl">
                      <code className="language-html">
                        {embedCode}
                      </code>
                    </pre>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="absolute top-3 right-3 gap-2 bg-white/10 hover:bg-white/20 border-white/10 text-white backdrop-blur-sm transition-all"
                      onClick={copyToClipboard}
                    >
                      {copied ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-green-400" />
                          <span className="text-xs">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span className="text-xs">Copy Code</span>
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
 
              <div className="flex gap-4 p-4 bg-amber-50 border border-amber-200 rounded-xl">
                <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                  <span className="text-amber-600 font-bold">!</span>
                </div>
                <div>
                  <h4 className="text-sm font-bold text-amber-900 mb-1">Configuration Required</h4>
                  <p className="text-xs text-amber-800 leading-relaxed">
                    Make sure to replace <code className="bg-amber-100/50 px-1 py-0.5 rounded font-mono">YOUR_API_KEY</code> with your actual production key from the <a href="/dashboard/api-keys" className="underline font-bold hover:text-amber-600 transition-colors">API Keys page</a>.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Preview */}
        <div>
          <Card className="sticky top-6 overflow-hidden">
            <CardHeader className="border-b bg-gray-50/50">
              <CardTitle className="text-sm font-medium text-gray-500 uppercase tracking-wider">Live Preview</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="bg-slate-200 aspect-[4/5] lg:aspect-auto lg:h-[650px] relative overflow-hidden group">
                {/* Mock Website Background */}
                <div className="absolute inset-0 p-8">
                  <div className="w-full h-8 bg-white/60 rounded mb-6 animate-pulse" />
                  <div className="flex gap-4 mb-8">
                    <div className="w-2/3 h-40 bg-white/40 rounded animate-pulse" />
                    <div className="flex-1 h-40 bg-white/40 rounded animate-pulse" />
                  </div>
                  <div className="space-y-3">
                    <div className="w-full h-4 bg-white/30 rounded" />
                    <div className="w-5/6 h-4 bg-white/30 rounded" />
                    <div className="w-4/6 h-4 bg-white/30 rounded" />
                  </div>
                </div>

                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <p className="text-sm font-medium text-slate-400 bg-white/80 px-4 py-2 rounded-full shadow-sm">Your website preview</p>
                </div>

                {/* Chatbot Widget Preview */}
                <div
                  className={`absolute ${
                    position === "bottom-right" ? "right-8 items-end" : "left-8 items-start"
                  } bottom-8 z-10 flex flex-col`}
                >
                  {/* Chatbot Window */}
                  {isPreviewOpen && (
                    <div 
                      className={`absolute bottom-24 ${
                        position === "bottom-right" ? "right-0" : "left-0"
                      } w-[350px] sm:w-[380px] h-[480px] bg-white rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.15)] flex flex-col border border-gray-100 overflow-hidden transition-all duration-300 animate-in fade-in slide-in-from-bottom-4`}
                    >
                      {/* Header */}
                      <div
                        className="p-4 flex items-center justify-between shadow-sm"
                        style={{ backgroundColor: themeColor }}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center">
                            <MessageSquare className="w-5 h-5 text-white" />
                          </div>
                          <div>
                            <h3 className="font-bold text-white text-sm leading-tight">
                              {widgetTitle}
                            </h3>
                            <div className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                              <p className="text-[10px] font-medium text-white/90 uppercase tracking-wider">Online</p>
                            </div>
                          </div>
                        </div>
                        <button 
                          onClick={() => setIsPreviewOpen(false)}
                          className="w-8 h-8 rounded-full hover:bg-white/10 flex items-center justify-center text-white/80 hover:text-white transition-colors"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      </div>

                      {/* Messages */}
                      <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-gray-50/30">
                        <div className="flex gap-2">
                          <div
                            className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm"
                            style={{ backgroundColor: themeColor }}
                          >
                            <MessageSquare className="w-4 h-4 text-white" />
                          </div>
                          <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none p-3 shadow-sm max-w-[80%]">
                            <p className="text-sm text-gray-800 leading-relaxed">{greetingMessage}</p>
                          </div>
                        </div>

                        <div className="flex gap-2 justify-end">
                          <div
                            className="rounded-2xl rounded-tr-none p-3 shadow-md max-w-[80%]"
                            style={{
                              backgroundColor: themeColor,
                              color: "white",
                            }}
                          >
                            <p className="text-sm font-medium">
                              Show me all orders from last week
                            </p>
                          </div>
                        </div>

                        <div className="flex gap-2">
                          <div
                            className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center shadow-sm"
                            style={{ backgroundColor: themeColor }}
                          >
                            <MessageSquare className="w-4 h-4 text-white" />
                          </div>
                          <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none p-3 shadow-sm max-w-[80%]">
                            <p className="text-sm text-gray-800 leading-relaxed">
                              I found 127 orders from last week. Total value:
                              <span className="font-bold ml-1">$15,432</span>. Would you like me to show you more details?
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Input */}
                      <div className="p-4 bg-white border-t border-gray-100">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            placeholder="Type your message..."
                            className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 transition-all"
                            style={{ "--tw-ring-color": themeColor } as any}
                          />
                          <button
                            className="w-10 h-10 rounded-xl text-white shadow-lg shadow-primary/20 flex items-center justify-center transition-transform hover:scale-105 active:scale-95"
                            style={{ backgroundColor: themeColor }}
                          >
                            <svg className="w-5 h-5 rotate-90" fill="currentColor" viewBox="0 0 20 20">
                              <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                            </svg>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Chatbot Button */}
                  <div
                    onClick={() => setIsPreviewOpen(!isPreviewOpen)}
                    className="w-16 h-16 rounded-full shadow-[0_8px_30px_rgb(0,0,0,0.12)] flex items-center justify-center cursor-pointer transition-all duration-300 hover:scale-110 active:scale-95 group/btn relative overflow-hidden"
                    style={{ backgroundColor: themeColor }}
                  >
                    <div className="absolute inset-0 bg-white/0 group-hover/btn:bg-white/10 transition-colors" />
                    {isPreviewOpen ? (
                       <X className="w-7 h-7 text-white animate-in spin-in-90 duration-300" />
                    ) : (
                      <MessageSquare className="w-7 h-7 text-white animate-in zoom-in duration-300" />
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
