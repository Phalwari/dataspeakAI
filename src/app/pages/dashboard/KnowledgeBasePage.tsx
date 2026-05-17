import { useState, useEffect } from "react";
import { API_BASE_URL } from "../../config/api";
import { Link } from "react-router";
import {
  FileText,
  Upload,
  Search,
  MoreVertical,
  Trash2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Plus,
  Eye,
  Info,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import { Badge } from "../../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../../components/ui/dialog";
import { ScrollArea } from "../../components/ui/scroll-area";

export function KnowledgeBasePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [documents, setDocuments] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  const [selectedDocument, setSelectedDocument] = useState<any>(null);
  const [documentChunks, setDocumentChunks] = useState<any[]>([]);
  const [isChunksLoading, setIsChunksLoading] = useState(false);
  
  const [selectedStatsDocument, setSelectedStatsDocument] = useState<any>(null);

  const [testQuery, setTestQuery] = useState("");
  const [testResults, setTestResults] = useState<any[]>([]);
  const [isTestQueryOpen, setIsTestQueryOpen] = useState(false);
  const [isTestingQuery, setIsTestingQuery] = useState(false);

  const handleTestQuery = async () => {
    if (!testQuery.trim()) return;
    setIsTestingQuery(true);
    setTestResults([]);
    const token = localStorage.getItem("token");
    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ query: testQuery })
      });
      if (response.ok) {
        const data = await response.json();
        setTestResults(data.results);
      }
    } catch (error) {
      console.error("Failed to execute test query:", error);
    } finally {
      setIsTestingQuery(false);
    }
  };


  const fetchDocuments = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/documents`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      }
    } catch (error) {
      console.error("Failed to fetch documents:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
    // Poll for status updates
    const interval = setInterval(fetchDocuments, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id: number) => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      await fetch(`${API_BASE_URL}/api/documents/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      fetchDocuments();
    } catch (error) {
      console.error("Failed to delete document:", error);
    }
  };

  const fetchDocumentChunks = async (document: any) => {
    setSelectedDocument(document);
    setDocumentChunks([]);
    setIsChunksLoading(true);
    
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/documents/${document.id}/chunks`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setDocumentChunks(data.chunks);
      }
    } catch (error) {
      console.error("Failed to fetch chunks:", error);
    } finally {
      setIsChunksLoading(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "Completed":
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case "Processing":
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case "Failed":
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      Completed: "default",
      Processing: "secondary",
      Failed: "destructive",
    };
    return (
      <Badge variant={variants[status] || "outline"} className="gap-1">
        {getStatusIcon(status)}
        {status}
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Knowledge Base</h1>
        <p className="text-gray-600 mt-1">
          Upload and manage documents for AI-powered semantic search
        </p>
      </div>

      {/* Overview Cards */}
      <div className="grid md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Documents</p>
                <p className="text-2xl font-bold">{documents.length}</p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                <FileText className="w-6 h-6 text-blue-600" />
              </div>
            </div>
            <p className="text-xs text-green-600 mt-2">total files</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Total Embeddings</p>
                <p className="text-2xl font-bold">
                  {documents.reduce((acc, curr) => acc + (curr.embeddings_count || 0), 0).toLocaleString()}
                </p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-purple-100 flex items-center justify-center">
                <Search className="w-6 h-6 text-purple-600" />
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-2">Vector database</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Storage Used</p>
                <p className="text-2xl font-bold">
                  {(documents.reduce((acc, curr) => acc + (curr.size || 0), 0) / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-green-100 flex items-center justify-center">
                <FileText className="w-6 h-6 text-green-600" />
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-2">of 5 GB limit</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Indexing Status</p>
                <p className="text-2xl font-bold">
                  {documents.filter(d => d.status === "Completed").length} / {documents.length}
                </p>
              </div>
              <div className="w-12 h-12 rounded-lg bg-yellow-100 flex items-center justify-center">
                <RefreshCw className="w-6 h-6 text-yellow-600" />
              </div>
            </div>
            <p className="text-xs text-gray-600 mt-2">
              {documents.filter(d => d.status === "Processing").length} processing
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Documents Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Documents</CardTitle>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search documents..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 w-64"
                />
              </div>
              <Button variant="outline" className="gap-2" onClick={() => setIsTestQueryOpen(true)}>
                <Search className="w-4 h-4" />
                Test AI Query
              </Button>
              <Link to="/dashboard/upload-documents">
                <Button className="gap-2">
                  <Plus className="w-4 h-4" />
                  Upload Documents
                </Button>
              </Link>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>File Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Upload Date</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Embeddings</TableHead>
                <TableHead className="w-12"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.map((doc) => (
                <TableRow key={doc.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-gray-400" />
                      {doc.name}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">{doc.file_type}</Badge>
                  </TableCell>
                  <TableCell className="text-gray-600">
                    {new Date(doc.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>{getStatusBadge(doc.status)}</TableCell>
                  <TableCell className="text-gray-600">
                    {(doc.size / 1024).toFixed(1)} KB
                  </TableCell>
                  <TableCell className="text-gray-600">
                    {doc.embeddings_count.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center justify-end gap-2">
                      <Button 
                        variant="ghost" 
                        size="icon" 
                        className="text-red-500 hover:text-red-600 hover:bg-red-50"
                        onClick={() => handleDelete(doc.id)}
                        title="Delete Document"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => fetchDocumentChunks(doc)}>
                            <Eye className="w-4 h-4 mr-2" />
                            View Embeddings
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setSelectedStatsDocument(doc)}>
                            <Info className="w-4 h-4 mr-2" />
                            View Details
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <RefreshCw className="w-4 h-4 mr-2" />
                            Re-index
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* View Embeddings Dialog */}
      <Dialog open={!!selectedDocument} onOpenChange={(open) => !open && setSelectedDocument(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Document Embeddings</DialogTitle>
            <DialogDescription>
              Viewing the semantic chunks extracted from {selectedDocument?.name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="mt-4">
            {isChunksLoading ? (
              <div className="flex items-center justify-center p-8">
                <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
              </div>
            ) : documentChunks.length === 0 ? (
              <div className="text-center p-8 text-gray-500">
                No embeddings found. This document may still be processing or failed to vectorize.
              </div>
            ) : (
              <ScrollArea className="h-[400px] rounded-md border p-4">
                <div className="space-y-4">
                  {documentChunks.map((chunk, index) => (
                    <div key={chunk.id} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="secondary">Chunk {index + 1}</Badge>
                        <span className="text-xs text-gray-400 font-mono" title={chunk.id}>
                          {chunk.id.substring(0, 8)}...
                        </span>
                      </div>
                      <p className="text-sm text-gray-700 whitespace-pre-wrap">
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Test AI Query Dialog */}
      <Dialog open={isTestQueryOpen} onOpenChange={setIsTestQueryOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Test AI Knowledge Base</DialogTitle>
            <DialogDescription>
              Ask a question to see how the AI retrieves relevant chunks from your documents.
            </DialogDescription>
          </DialogHeader>
          
          <div className="mt-4 space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="E.g., What is the main objective of the project?"
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTestQuery()}
              />
              <Button onClick={handleTestQuery} disabled={isTestingQuery || !testQuery.trim()}>
                {isTestingQuery ? <RefreshCw className="w-4 h-4 animate-spin" /> : "Search"}
              </Button>
            </div>

            <div className="mt-4">
              {isTestingQuery ? (
                <div className="flex items-center justify-center p-8">
                  <RefreshCw className="w-6 h-6 text-blue-600 animate-spin" />
                </div>
              ) : testResults.length > 0 ? (
                <ScrollArea className="h-[400px] rounded-md border p-4">
                  <div className="space-y-4">
                    {testResults.map((result, index) => (
                      <div key={index} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Badge variant="default" className="bg-blue-600">Match #{index + 1}</Badge>
                            <span className="text-xs text-gray-500 flex items-center gap-1">
                              <FileText className="w-3 h-3" />
                              {result.metadata?.source || "Unknown Document"}
                            </span>
                          </div>
                          <span className="text-xs font-mono bg-white px-2 py-1 rounded border border-gray-200">
                            Score: {result.score.toFixed(4)}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap mt-3 pl-2 border-l-2 border-blue-200">
                          {result.content}
                        </p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              ) : testQuery && !isTestingQuery ? (
                <div className="text-center p-8 text-gray-500 border rounded-md">
                  No matching results found. Try asking something else or upload more documents.
                </div>
              ) : null}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* View Details Dialog */}
      <Dialog open={!!selectedStatsDocument} onOpenChange={(open) => !open && setSelectedStatsDocument(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Document Details</DialogTitle>
            <DialogDescription>
              Detailed statistics and metadata for {selectedStatsDocument?.name}
            </DialogDescription>
          </DialogHeader>
          
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <p className="text-sm text-gray-500 mb-1">File Type</p>
                <p className="font-medium">{selectedStatsDocument?.file_type}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <p className="text-sm text-gray-500 mb-1">File Size</p>
                <p className="font-medium">
                  {selectedStatsDocument ? (selectedStatsDocument.size / 1024).toFixed(2) : 0} KB
                </p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <p className="text-sm text-gray-500 mb-1">Total Sentences</p>
                <p className="font-medium">{selectedStatsDocument?.line_count || 0}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <p className="text-sm text-gray-500 mb-1">Total Paragraphs</p>
                <p className="font-medium">{selectedStatsDocument?.paragraph_count || 0}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <p className="text-sm text-gray-500 mb-1">Total Tables</p>
                <p className="font-medium">{selectedStatsDocument?.table_count || 0}</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                <p className="text-sm text-gray-500 mb-1">Total Images</p>
                <p className="font-medium">{selectedStatsDocument?.image_count || 0}</p>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

    </div>
  );
}
