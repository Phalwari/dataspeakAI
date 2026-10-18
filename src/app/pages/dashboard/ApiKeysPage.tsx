import { useState, useEffect } from "react";
import { API_BASE_URL } from "../../config/api";
import { Plus, Copy, RefreshCw, Trash2, Eye, EyeOff, Check } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";

export function ApiKeysPage() {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [copiedKey, setCopiedKey] = useState<number | null>(null);
  const [visibleKeys, setVisibleKeys] = useState<Set<number>>(new Set());
  
  const [apiKeys, setApiKeys] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [newGeneratedKey, setNewGeneratedKey] = useState<string | null>(null);
  const [copiedNewKey, setCopiedNewKey] = useState(false);

  const fetchApiKeys = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/keys`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setApiKeys(data);
      }
    } catch (error) {
      console.error("Failed to fetch API keys:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApiKeys();
  }, []);

  const handleGenerateKey = async () => {
    const token = localStorage.getItem("token");
    if (!token || !name) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ name, description })
      });

      if (response.ok) {
        const data = await response.json();
        setNewGeneratedKey(data.key);
        setName("");
        setDescription("");
        fetchApiKeys();
      }
    } catch (error) {
      console.error("Failed to generate API key:", error);
    }
  };

  const handleRevokeKey = async (id: number) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/keys/${id}/revoke`, {
        method: "PUT",
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (response.ok) {
        fetchApiKeys();
      }
    } catch (error) {
      console.error("Failed to revoke API key:", error);
    }
  };

  const handleDeleteKey = async (id: number) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/keys/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (response.ok) {
        fetchApiKeys();
      }
    } catch (error) {
      console.error("Failed to delete API key:", error);
    }
  };

  const copyToClipboard = (key: string, id: number) => {
    navigator.clipboard.writeText(key);
    setCopiedKey(id);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const toggleKeyVisibility = (id: number) => {
    setVisibleKeys((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const maskKey = (key: string) => {
    const prefix = key.substring(0, 12);
    const suffix = key.substring(key.length - 4);
    return `${prefix}${"•".repeat(20)}${suffix}`;
  };

  const activeKeysCount = apiKeys.filter(k => k.status === 'active').length;
  const totalRequestsCount = apiKeys.reduce((acc, curr) => acc + (curr.total_requests || 0), 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold mb-2">API Keys</h1>
          <p className="text-gray-600">
            Manage your API keys for accessing the chatbot platform
          </p>
        </div>

        <Dialog
          open={isDialogOpen}
          onOpenChange={(open) => {
            setIsDialogOpen(open);
            if (!open) {
              setNewGeneratedKey(null);
              setCopiedNewKey(false);
            }
          }}
        >
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Generate API Key
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[520px]">
            {newGeneratedKey ? (
              <>
                <DialogHeader>
                  <DialogTitle className="text-green-700 flex items-center gap-2">
                    <Check className="w-5 h-5 text-green-600" />
                    API Key Generated Successfully
                  </DialogTitle>
                  <DialogDescription>
                    Please copy your new API key now. For your security, this key will <strong>never be shown again</strong>.
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="generated-key">Your Secret API Key</Label>
                    <div className="flex items-center gap-2">
                      <Input
                        id="generated-key"
                        readOnly
                        value={newGeneratedKey}
                        className="font-mono text-sm bg-gray-50 select-all"
                      />
                      <Button
                        type="button"
                        variant="outline"
                        className="gap-1.5 shrink-0"
                        onClick={() => {
                          navigator.clipboard.writeText(newGeneratedKey);
                          setCopiedNewKey(true);
                          setTimeout(() => setCopiedNewKey(false), 3000);
                        }}
                      >
                        {copiedNewKey ? (
                          <>
                            <Check className="w-4 h-4 text-green-600" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="w-4 h-4" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                    <p className="text-sm text-amber-800">
                      <strong>Warning:</strong> You will not be able to view this key again after closing this dialog. If you lose this key, you will need to revoke it and generate a new one.
                    </p>
                  </div>
                </div>

                <DialogFooter>
                  <Button
                    onClick={() => {
                      setNewGeneratedKey(null);
                      setCopiedNewKey(false);
                      setIsDialogOpen(false);
                    }}
                  >
                    I Have Saved My Key
                  </Button>
                </DialogFooter>
              </>
            ) : (
              <>
                <DialogHeader>
                  <DialogTitle>Generate New API Key</DialogTitle>
                  <DialogDescription>
                    Create a new API key to integrate with your applications
                  </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="key-name">Key Name</Label>
                    <Input
                      id="key-name"
                      placeholder="e.g., Production Key"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="key-description">Description (Optional)</Label>
                    <Input
                      id="key-description"
                      placeholder="What will this key be used for?"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                    />
                  </div>

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">
                      <strong>Important:</strong> Your API key will only be shown once immediately upon creation.
                      Make sure to copy and store it securely.
                    </p>
                  </div>
                </div>

                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleGenerateKey} disabled={!name}>
                    Generate Key
                  </Button>
                </DialogFooter>
              </>
            )}
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-gray-600 mb-2">Active Keys</p>
            <p className="text-3xl font-bold">{activeKeysCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-gray-600 mb-2">Total Requests</p>
            <p className="text-3xl font-bold">{totalRequestsCount.toLocaleString()}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <p className="text-sm text-gray-600 mb-2">Requests Today</p>
            <p className="text-3xl font-bold">1,234</p>
          </CardContent>
        </Card>
      </div>

      {/* API Keys Table */}
      <Card>
        <CardHeader>
          <CardTitle>Your API Keys</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead>Requests</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {apiKeys.map((apiKey) => (
                <TableRow key={apiKey.id}>
                  <TableCell className="font-medium">{apiKey.name}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <code className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {visibleKeys.has(apiKey.id)
                          ? apiKey.key
                          : maskKey(apiKey.key)}
                      </code>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => toggleKeyVisibility(apiKey.id)}
                      >
                        {visibleKeys.has(apiKey.id) ? (
                          <EyeOff className="w-3.5 h-3.5" />
                        ) : (
                          <Eye className="w-3.5 h-3.5" />
                        )}
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>
                    {apiKey.status === "active" ? (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700">
                        Revoked
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {new Date(apiKey.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-sm text-gray-600">
                    {apiKey.last_used_at ? new Date(apiKey.last_used_at).toLocaleDateString() : "Never"}
                  </TableCell>
                  <TableCell className="text-sm">
                    {(apiKey.total_requests || 0).toLocaleString()}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => copyToClipboard(apiKey.key, apiKey.id)}
                      >
                        {copiedKey === apiKey.id ? (
                          <Check className="w-4 h-4 text-green-600" />
                        ) : (
                          <Copy className="w-4 h-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleRevokeKey(apiKey.id)}
                        disabled={apiKey.status === "revoked"}
                        title="Revoke Key"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleDeleteKey(apiKey.id)}
                        title="Delete Key"
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Usage Instructions */}
      <Card>
        <CardHeader>
          <CardTitle>Using Your API Key</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="font-medium mb-2">Authentication</h4>
            <p className="text-sm text-gray-600 mb-2">
              Include your API key in the request headers:
            </p>
            <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-x-auto">
              {`curl https://api.omniquery.ai/v1/query \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Show all users"}'`}
            </pre>
          </div>

          <div>
            <h4 className="font-medium mb-2">Rate Limits</h4>
            <p className="text-sm text-gray-600">
              Starter plan: 10,000 requests/month • Pro plan: Unlimited requests
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
