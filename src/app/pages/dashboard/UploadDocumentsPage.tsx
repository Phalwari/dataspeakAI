import { useState, useRef, useEffect } from "react";
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
  Clock,
  RotateCcw,
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
import { Badge } from "../../components/ui/badge";

interface FileUploadState {
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  uploadProgress: number;  // 0-100 HTTP upload
  processingProgress: number;  // 0-100 backend processing
  documentId: number | null;
  totalPages: number;
  pagesProcessed: number;
  visualPages: number;
  errorMessage: string | null;
}

export function UploadDocumentsPage() {
  const navigate = useNavigate();
  const [files, setFiles] = useState<FileUploadState[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  
  const [chunkSize, setChunkSize] = useState([512]);
  const [chunkOverlap, setChunkOverlap] = useState([50]);
  const [autoIndex, setAutoIndex] = useState(true);
  const [chunkingStrategy, setChunkingStrategy] = useState("paragraph");
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = (newFiles: File[]) => {
    const fileStates: FileUploadState[] = newFiles.map(file => ({
      file,
      status: 'pending',
      uploadProgress: 0,
      processingProgress: 0,
      documentId: null,
      totalPages: 0,
      pagesProcessed: 0,
      visualPages: 0,
      errorMessage: null,
    }));
    setFiles(prev => [...prev, ...fileStates]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadSingleFile = (fileState: FileUploadState, fileIndex: number, token: string): Promise<void> => {
    return new Promise((resolve) => {
      setFiles(prev => prev.map((f, i) => i === fileIndex ? {
        ...f,
        status: 'uploading',
        uploadProgress: 0,
        processingProgress: 0,
        errorMessage: null,
      } : f));

      const formData = new FormData();
      formData.append("file", fileState.file);
      formData.append("chunk_size", chunkSize[0].toString());
      formData.append("chunk_overlap", chunkOverlap[0].toString());
      formData.append("chunking_strategy", chunkingStrategy);

      const xhr = new XMLHttpRequest();

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          setFiles(prev => prev.map((f, i) => i === fileIndex ? {
            ...f,
            uploadProgress: percent,
          } : f));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const res = JSON.parse(xhr.responseText);
            const docId = res.id;
            const backendProgress = Math.round((res.progress || 0) * 100);
            setFiles(prev => prev.map((f, i) => i === fileIndex ? {
              ...f,
              status: res.status === 'Completed' ? 'completed' : res.status === 'Failed' ? 'failed' : 'processing',
              uploadProgress: 100,
              processingProgress: backendProgress,
              documentId: docId,
              totalPages: res.total_pages || 0,
              pagesProcessed: res.pages_processed || 0,
              visualPages: res.visual_pages || 0,
              errorMessage: res.error_message || null,
            } : f));
          } catch {
            setFiles(prev => prev.map((f, i) => i === fileIndex ? {
              ...f,
              status: 'failed',
              errorMessage: 'Failed to parse upload response',
            } : f));
          }
        } else {
          let errStr = 'Upload failed';
          try {
            const res = JSON.parse(xhr.responseText);
            errStr = res.detail || errStr;
          } catch {}
          setFiles(prev => prev.map((f, i) => i === fileIndex ? {
            ...f,
            status: 'failed',
            errorMessage: errStr,
          } : f));
        }
        resolve();
      };

      xhr.onerror = () => {
        setFiles(prev => prev.map((f, i) => i === fileIndex ? {
          ...f,
          status: 'failed',
          errorMessage: 'Network error during upload',
        } : f));
        resolve();
      };

      xhr.open("POST", `${API_BASE_URL}/api/documents/upload`);
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.send(formData);
    });
  };

  // Poll GET /api/documents every 3 seconds for documents in 'processing' status
  useEffect(() => {
    const hasProcessing = files.some(f => f.status === 'processing');
    if (!hasProcessing) return;

    const token = localStorage.getItem("token");
    if (!token) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/documents`, {
          headers: { "Authorization": `Bearer ${token}` }
        });
        if (response.ok) {
          const docs: any[] = await response.json();
          setFiles(prev => prev.map(fileState => {
            if (fileState.status !== 'processing' || !fileState.documentId) return fileState;

            const doc = docs.find((d: any) => d.id === fileState.documentId);
            if (!doc) return fileState;

            const backendProgress = Math.round((doc.progress || 0) * 100);
            let newStatus: FileUploadState['status'] = 'processing';
            if (doc.status === 'Completed') {
              newStatus = 'completed';
            } else if (doc.status === 'Failed') {
              newStatus = 'failed';
            }

            return {
              ...fileState,
              status: newStatus,
              processingProgress: backendProgress,
              totalPages: doc.total_pages || fileState.totalPages,
              pagesProcessed: doc.pages_processed || fileState.pagesProcessed,
              visualPages: doc.visual_pages || fileState.visualPages,
              errorMessage: doc.error_message || fileState.errorMessage,
            };
          }));
        }
      } catch (err) {
        console.error("Polling documents failed:", err);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [files]);

  const handleUploadAll = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;
    setIsUploading(true);

    for (let i = 0; i < files.length; i++) {
      if (files[i].status === 'completed') continue;
      await uploadSingleFile(files[i], i, token);
    }
    setIsUploading(false);
  };

  const handleRetry = async (index: number) => {
    const token = localStorage.getItem("token");
    if (!token) return;
    await uploadSingleFile(files[index], index, token);
  };

  const allCompleted = files.length > 0 && files.every(f => f.status === 'completed');
  const hasFilesToUpload = files.some(f => f.status === 'pending' || f.status === 'failed');

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
                Upload PDF, DOCX, XLSX, PPTX, CSV, HTML, MD, or TXT files (max 25MB each)
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
                accept=".pdf,.docx,.xlsx,.xls,.pptx,.ppt,.csv,.html,.htm,.md,.txt"
                ref={fileInputRef}
              />

              {/* Selected Files & Per-file Progress */}
              {files.length > 0 && (
                <div className="mt-6 space-y-4">
                  <p className="text-sm font-medium mb-3">
                    Selected Files ({files.length})
                  </p>
                  {files.map((fileState, index) => (
                    <div
                      key={index}
                      className="p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <File className="w-5 h-5 text-blue-600 flex-shrink-0" />
                          <div>
                            <p className="text-sm font-medium text-gray-900">{fileState.file.name}</p>
                            <p className="text-xs text-gray-500">
                              {(fileState.file.size / (1024 * 1024)).toFixed(2)} MB
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {fileState.status === 'completed' && (
                            <Badge variant="default" className="bg-green-600 text-white gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Completed
                            </Badge>
                          )}
                          {fileState.status === 'failed' && (
                            <Badge variant="destructive" className="gap-1">
                              <AlertCircle className="w-3.5 h-3.5" />
                              Failed
                            </Badge>
                          )}
                          {fileState.status === 'processing' && (
                            <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 border-yellow-200 gap-1">
                              <Clock className="w-3.5 h-3.5 animate-spin text-yellow-600" />
                              Processing
                            </Badge>
                          )}
                          {fileState.status === 'uploading' && (
                            <Badge variant="secondary" className="bg-blue-100 text-blue-800 border-blue-200 gap-1">
                              <Upload className="w-3.5 h-3.5 animate-pulse text-blue-600" />
                              Uploading
                            </Badge>
                          )}
                          {fileState.status === 'pending' && (
                            <Badge variant="outline" className="text-gray-600">Pending</Badge>
                          )}
                          {!isUploading && fileState.status !== 'uploading' && fileState.status !== 'processing' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeFile(index)}
                            >
                              <X className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>

                      {/* VLM Vision Badge */}
                      {fileState.visualPages > 0 && (
                        <div>
                          <Badge variant="secondary" className="bg-purple-50 text-purple-700 border-purple-200 gap-1 text-xs">
                            🔍 {fileState.visualPages} pages sent to AI vision
                          </Badge>
                        </div>
                      )}

                      {/* Dual Progress Bars */}
                      {(fileState.status === 'uploading' || fileState.status === 'processing' || fileState.status === 'completed' || fileState.uploadProgress > 0) && (
                        <div className="space-y-2 pt-1">
                          {/* Upload Progress (Blue) */}
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-gray-600 font-medium">Upload Progress</span>
                              <span className="text-blue-600 font-semibold">{fileState.uploadProgress}%</span>
                            </div>
                            <Progress value={fileState.uploadProgress} className="h-2 bg-blue-100 [&>[data-slot=progress-indicator]]:bg-blue-600" />
                          </div>

                          {/* Processing Progress (Green) */}
                          {(fileState.status === 'processing' || fileState.status === 'completed' || fileState.processingProgress > 0) && (
                            <div>
                              <div className="flex justify-between text-xs mb-1">
                                <span className="text-gray-600 font-medium">
                                  Backend Processing
                                  {fileState.totalPages > 0 && (
                                    <span className="ml-2 text-gray-500 font-normal">
                                      ({fileState.pagesProcessed} / {fileState.totalPages} pages)
                                    </span>
                                  )}
                                </span>
                                <span className="text-green-600 font-semibold">{fileState.processingProgress}%</span>
                              </div>
                              <Progress value={fileState.processingProgress} className="h-2 bg-green-100 [&>[data-slot=progress-indicator]]:bg-green-600" />
                            </div>
                          )}
                        </div>
                      )}

                      {/* Error Message & Retry Button */}
                      {fileState.status === 'failed' && (
                        <div className="flex items-center justify-between p-3 bg-red-50 border border-red-200 rounded-md mt-2">
                          <div className="flex items-center gap-2 text-red-700 text-xs">
                            <AlertCircle className="w-4 h-4 flex-shrink-0" />
                            <span>{fileState.errorMessage || "An error occurred during processing."}</span>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-200 text-red-700 hover:bg-red-100 h-8 text-xs gap-1"
                            onClick={() => handleRetry(index)}
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            Retry
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Overall Success Message */}
              {allCompleted && (
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
                <div className="p-2.5 bg-gray-50 border border-gray-200 rounded-md text-sm text-gray-700 font-medium">
                  Sentence Transformers (all-MiniLM-L6-v2)
                </div>
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
                    <SelectItem value="line">Line-based</SelectItem>
                    <SelectItem value="sentence">Sentence-based</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-gray-600">
                  {chunkingStrategy === "paragraph" 
                    ? "Splits text by double newlines (\\n\\n) to preserve paragraph context." 
                    : chunkingStrategy === "line"
                    ? "Splits text by single newlines (\\n) to preserve line context."
                    : chunkingStrategy === "sentence"
                    ? "Splits text by punctuation (. ? !) to preserve sentence context."
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
            onClick={handleUploadAll}
            disabled={files.length === 0 || isUploading || (!hasFilesToUpload && allCompleted)}
          >
            {allCompleted ? "Upload Complete" : isUploading ? "Uploading & Processing..." : "Upload & Process"}
          </Button>

          {allCompleted && (
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
