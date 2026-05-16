import { useState, useRef } from "react";
import { API_BASE_URL } from "../../config/api";
import { useNavigate } from "react-router";
import {
  Upload,
  File,
  X,
  CheckCircle2,
  AlertCircle,
  ArrowLeft,
  Info,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Slider } from "../../components/ui/slider";
import { Switch } from "../../components/ui/switch";
import { Progress } from "../../components/ui/progress";

export function UploadDocumentsPage() {
  const navigate = useNavigate();
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadComplete, setUploadComplete] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [chunkSize, setChunkSize] = useState([512]);
  const [chunkOverlap, setChunkOverlap] = useState([50]);
  const [embeddingModel, setEmbeddingModel] = useState("openai");
  const [autoIndex, setAutoIndex] = useState(true);
  const [chunkingStrategy, setChunkingStrategy] = useState("paragraph");
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      setSelectedFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const removeFile = (index: number) => {
    setSelectedFiles(selectedFiles.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    setIsUploading(true);
    setUploadProgress(0);
    const token = localStorage.getItem("token");
    if (!token) return;

    for (const file of selectedFiles) {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("chunk_size", chunkSize[0].toString());
      formData.append("chunk_overlap", chunkOverlap[0].toString());
      formData.append("chunking_strategy", chunkingStrategy);

      try {
        await fetch(`${API_BASE_URL}/api/documents/upload`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`
          },
          body: formData
        });
      } catch (error) {
        console.error("Failed to upload document:", error);
      }
      setUploadProgress(prev => prev + (100 / selectedFiles.length));
    }
    
    setIsUploading(false);
    setUploadComplete(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate("/dashboard/knowledge-base")}
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <h1 className="text-3xl font-bold">Upload Documents</h1>
          </div>
          <p className="text-gray-600 ml-12">
            Add documents to your knowledge base for AI-powered search
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {/* Upload Area */}
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Select Files</CardTitle>
              <CardDescription>
                Upload PDF, DOCX, TXT, or CSV files (max 10MB each)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <label
                htmlFor="file-upload"
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="block border-2 border-dashed border-gray-300 rounded-lg p-12 text-center hover:border-blue-400 transition-colors cursor-pointer"
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600 mb-2">
                  Drag and drop files here, or click anywhere to browse
                </p>
                <div className="mt-4 inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background border border-input hover:bg-accent hover:text-accent-foreground h-10 py-2 px-4 pointer-events-none">
                  Browse Files
                </div>
              </label>
              <Input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
                accept=".pdf,.docx,.txt,.csv"
                ref={fileInputRef}
              />

              {/* Selected Files */}
              {selectedFiles.length > 0 && (
                <div className="mt-6 space-y-2">
                  <p className="text-sm font-medium mb-3">
                    Selected Files ({selectedFiles.length})
                  </p>
                  {selectedFiles.map((file, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <File className="w-4 h-4 text-gray-400" />
                        <div>
                          <p className="text-sm font-medium">{file.name}</p>
                          <p className="text-xs text-gray-600">
                            {(file.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeFile(index)}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              {/* Upload Progress */}
              {isUploading && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium">Uploading...</p>
                    <p className="text-sm text-gray-600">{uploadProgress}%</p>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}

              {/* Success Message */}
              {uploadComplete && (
                <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-green-900">
                        Vectorized Successfully
                      </p>
                      <p className="text-sm text-green-700 mt-1">
                        Your documents have been processed and indexed. They are now
                        ready for AI-powered search.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Options Panel */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Processing Options</CardTitle>
              <CardDescription>Configure how documents are indexed</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>Embedding Model</Label>
                <Select value={embeddingModel} onValueChange={setEmbeddingModel}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI Ada-002</SelectItem>
                    <SelectItem value="cohere">Cohere Embed</SelectItem>
                    <SelectItem value="sentence">Sentence Transformers</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600">
                  Model used to generate embeddings
                </p>
              </div>

              <div className="space-y-2">
                <Label>Chunking Strategy</Label>
                <Select value={chunkingStrategy} onValueChange={setChunkingStrategy}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fixed">Fixed Size</SelectItem>
                    <SelectItem value="paragraph">Paragraph-based</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600">
                  {chunkingStrategy === "paragraph" 
                    ? "Splits text by double newlines (\n\n) to preserve paragraph context." 
                    : "Splits text into fixed token sizes regardless of content structure."}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Chunk Size: {chunkSize[0]} tokens</Label>
                <Slider
                  value={chunkSize}
                  onValueChange={setChunkSize}
                  min={128}
                  max={2048}
                  step={128}
                />
                <p className="text-xs text-gray-600">
                  Size of text chunks for processing
                </p>
              </div>

              <div className="space-y-2">
                <Label>Chunk Overlap: {chunkOverlap[0]} tokens</Label>
                <Slider
                  value={chunkOverlap}
                  onValueChange={setChunkOverlap}
                  min={0}
                  max={512}
                  step={10}
                />
                <p className="text-xs text-gray-600">
                  Overlap between chunks to maintain context
                </p>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto Re-index</Label>
                  <p className="text-xs text-gray-600">
                    Automatically update embeddings
                  </p>
                </div>
                <Switch checked={autoIndex} onCheckedChange={setAutoIndex} />
              </div>

              <div className="pt-4 border-t border-gray-200">
                <div className="bg-blue-50 rounded-lg p-3">
                  <div className="flex gap-2">
                    <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-xs text-blue-900 font-medium mb-1">
                        Processing Time
                      </p>
                      <p className="text-xs text-blue-700">
                        Estimated: 2-5 minutes per document
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Button
            className="w-full"
            size="lg"
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || isUploading || uploadComplete}
          >
            {uploadComplete ? "Upload Complete" : "Upload & Process"}
          </Button>

          {uploadComplete && (
            <Button
              variant="outline"
              className="w-full"
              onClick={() => navigate("/dashboard/knowledge-base")}
            >
              View Knowledge Base
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
