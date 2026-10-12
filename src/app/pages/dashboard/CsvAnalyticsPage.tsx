import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { 
  FileSpreadsheet,
  TrendingUp, Sparkles, Brain, Check, BarChart2, Database,
  Upload as UploadIcon, Cloud, Trash2, Loader2,
  Table
} from 'lucide-react';
import { API_BASE_URL } from '../../config/api';
const API_URL = `${API_BASE_URL}/api`;
import { toast } from 'sonner';
// local auth via token
import { useAnalytics } from '../../context/AnalyticsContext';
import DataSpeakDashboard from '../../components/templates/ECommerceTemplate';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit: { opacity: 0, y: -10 }
};

export function CsvAnalyticsPage() {
  const token = localStorage.getItem('token') || localStorage.getItem('access_token') || '';
  const {
    selectedDatasetId, setSelectedDatasetId,
    rawData, setRawData,
    mlData, setMlData,
    filename, setFilename,
    resetAnalytics
  } = useAnalytics();

  const [datasets, setDatasets] = useState<any[]>([]);
  
  // Workflow & Upload states
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [autoGenerateStep, setAutoGenerateStep] = useState<string | null>(null); // 'analyzing' | null
  const [agAnalysisStep, setAgAnalysisStep] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDatasets = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/files/datasets`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDatasets(data);
      }
    } catch (e) {
      console.error(e);
    }
  }, [token]);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const handleSelectDataset = async (ds: any, forceRefresh = false) => {
    // If same dataset is already loaded in context and no forced refresh, display instantly
    if (!forceRefresh && selectedDatasetId === ds.id && mlData) {
      return;
    }

    setSelectedDatasetId(ds.id);
    setFilename(ds.name);
    setLoading(true);
    const startTime = Date.now();
    
    try {
      // Run both requests in parallel for speed
      const mlUrl = forceRefresh
        ? `${API_URL}/file-insights/ml-analysis/${ds.id}?refresh=true`
        : `${API_URL}/file-insights/ml-analysis/${ds.id}`;

      const [rowsRes, mlRes] = await Promise.all([
        fetch(`${API_URL}/files/${ds.id}/data?limit=500`, {
          headers: { Authorization: `Bearer ${token}` }
        }).catch(() => null),
        fetch(mlUrl, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      // ML data is required — rows are optional (used for filter interactivity)
      if (mlRes.ok) {
        const ml = await mlRes.json();
        setMlData(ml);

        // Load raw rows if available (enables live filter recomputation)
        if (rowsRes && rowsRes.ok) {
          const rows = await rowsRes.json();
          setRawData(Array.isArray(rows) ? rows : []);
        } else {
          // Fallback: use sample_rows from the pipeline profile
          setRawData(ml?.df_stats?.sample_rows || []);
        }

        const elapsed = Date.now() - startTime;
        if (elapsed < 1000) {
          setAutoGenerateStep(null); // Instant render for cached responses
        } else {
          triggerAnalysisFlow();
        }
      } else {
        console.error('Failed to load ML insights — status:', mlRes.status);
      }
    } catch (err) {
      console.error('Error fetching dataset rows / ML insights:', err);
    } finally {
      setLoading(false);
    }
  };


  const triggerAnalysisFlow = () => {
    setAutoGenerateStep('analyzing');
    setAgAnalysisStep(0);
    
    const interval = setInterval(() => {
      setAgAnalysisStep(prev => {
        if (prev >= 3) {
          clearInterval(interval);
          setTimeout(() => {
            setAutoGenerateStep(null); // finish analysis
          }, 600);
          return 4;
        }
        return prev + 1;
      });
    }, 900);
  };

  // Drag & Drop / File Upload handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  const uploadFile = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      toast.error("Please upload a valid CSV or Excel dataset (.csv, .xlsx).");
      return;
    }

    setUploading(true);
    setUploadProgress(10);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_URL}/files/upload-dataset`, true);
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          const pct = Math.round((e.loaded / e.total) * 100);
          setUploadProgress(pct);
        }
      };

      xhr.onload = async () => {
        if (xhr.status === 200 || xhr.status === 201) {
          const uploadedDs = JSON.parse(xhr.responseText);
          await fetchDatasets();
          // Force refresh=true for newly uploaded files to bypass any stale cached analysis
          handleSelectDataset(uploadedDs, true);
        } else {
          toast.error("Failed to upload dataset.");
        }
        setUploading(false);
        setUploadProgress(0);
      };

      xhr.onerror = () => {
        toast.error("Upload network error.");
        setUploading(false);
        setUploadProgress(0);
      };

      xhr.send(formData);
    } catch (err) {
      console.error(err);
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteDataset = async (e: React.MouseEvent, id: any) => {
    e.stopPropagation(); // prevent select action
    if (!window.confirm("Are you sure you want to delete this dataset?")) return;

    try {
      const res = await fetch(`${API_URL}/files/datasets/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        fetchDatasets();
        if (selectedDatasetId === id) {
          setSelectedDatasetId('');
          setRawData([]);
          setMlData(null);
          setFilename('');
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div style={{ flex: 1, minHeight: '100%', background: 'var(--bg)', color: 'var(--text-primary)', padding: '24px 32px', transition: 'background-color 0.3s ease, color 0.3s ease' }}>
      
      {/* Dynamic CSS styles for the upload panel */}
      <style dangerouslySetInnerHTML={{ __html: `
        .analytics-title {
          font-size: 26px;
          font-weight: 800;
          color: var(--text-primary);
          margin: 0;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .analytics-sub {
          font-size: 13px;
          color: var(--text-secondary);
          margin-top: 4px;
          margin-bottom: 24px;
        }
        .dataset-grid {
          display: grid;
          grid-template-columns: 1.2fr 1fr;
          gap: 24px;
          align-items: start;
        }
        @media (max-width: 900px) {
          .dataset-grid {
            grid-template-columns: 1fr;
          }
        }
        .section-card {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 16px;
          padding: 24px;
          min-height: 400px;
          box-shadow: var(--shadow-card);
          transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        }
        .section-title {
          font-size: 16px;
          font-weight: 700;
          color: var(--text-primary);
          margin: 0 0 16px 0;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .dataset-item {
          background: var(--card-elevated);
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 16px;
          margin-bottom: 12px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: space-between;
          transition: all 0.2s ease;
        }
        .dataset-item:hover {
          background: var(--hover-bg);
          border-color: var(--primary);
          transform: translateY(-2px);
          box-shadow: var(--shadow-md);
        }
        .dataset-name {
          font-size: 13.5px;
          font-weight: 600;
          color: var(--text-primary);
          margin: 0;
        }
        .dataset-meta {
          font-size: 11px;
          color: var(--text-secondary);
          display: block;
          margin-top: 2px;
        }
        .dropzone {
          border: 2px dashed var(--border);
          border-radius: 16px;
          background: var(--card-elevated);
          padding: 40px 20px;
          text-align: center;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 300px;
        }
        .dropzone:hover {
          border-color: var(--primary);
          background: var(--hover-bg);
        }
        .dropzone.active {
          border-color: var(--primary);
          background: rgba(108, 99, 255, 0.1);
        }
        .dropzone-title {
          font-size: 14px;
          font-weight: 700;
          color: var(--text-primary);
          margin: 0 0 4px 0;
        }
        .dropzone-sub {
          font-size: 12px;
          color: var(--text-secondary);
          margin: 0 0 16px 0;
        }
        .browse-pill {
          font-size: 11px;
          background: rgba(108, 99, 255, 0.12);
          color: var(--primary);
          padding: 6px 14px;
          border-radius: 8px;
          font-weight: 600;
          transition: all 0.2s ease;
        }
        .browse-pill:hover {
          background: var(--primary);
          color: #fff;
        }
      ` }} />

      {!selectedDatasetId ? (
        <motion.div 
          variants={pageVariants}
          initial="initial"
          animate="animate"
          exit="exit"
        >
          <h1 className="analytics-title">
            <BarChart2 size={26} color="var(--primary)" />
            DataSpeakAI Analytics Hub
          </h1>
          <p className="analytics-sub">
            Upload any CSV/Excel file or select an existing dataset to run dynamic ML models and interactive dashboards.
          </p>

          <div className="dataset-grid">
            
            {/* Left Column: List of Datasets */}
            <div className="section-card">
              <h2 className="section-title">
                <Database size={18} color="#00c2cb" />
                Select Existing Dataset ({datasets.length})
              </h2>

              {datasets.length === 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '220px', color: 'var(--text-secondary)' }}>
                  <FileSpreadsheet size={40} style={{ marginBottom: '12px', opacity: 0.5 }} />
                  <p style={{ fontSize: '13px', margin: 0 }}>No datasets found. Upload one on the right to start.</p>
                </div>
              ) : (
                <div style={{ maxHeight: '360px', overflowY: 'auto', paddingRight: '4px' }}>
                  {datasets.map(ds => (
                    <div 
                      key={ds.id} 
                      className="dataset-item"
                      onClick={() => handleSelectDataset(ds)}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(0,194,203,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <Table size={18} color="#00c2cb" />
                        </div>
                        <div>
                          <p className="dataset-name">{ds.name}</p>
                          <span className="dataset-meta">
                            {ds.file_size ? `${(ds.file_size / 1024).toFixed(0)} KB` : 'Auto Size'} · {(ds.created_at || '').split('T')[0]}
                          </span>
                        </div>
                      </div>
                      <button 
                        onClick={(e) => handleDeleteDataset(e, ds.id)}
                        style={{ background: 'transparent', border: 'none', cursor: 'pointer', padding: '6px' }}
                        title="Delete dataset"
                      >
                        <Trash2 size={15} color="#e24b4a" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Right Column: Upload Box */}
            <div className="section-card">
              <h2 className="section-title">
                <UploadIcon size={18} color="var(--primary)" />
                Upload New Dataset
              </h2>

              <div 
                className={`dropzone ${isDragging ? 'active' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  onChange={handleFileChange} 
                  style={{ display: 'none' }}
                  accept=".csv,.xlsx,.xls"
                />
                
                {uploading ? (
                  <div style={{ textAlign: 'center' }}>
                    <Loader2 size={36} color="var(--primary)" className="animate-spin" style={{ margin: '0 auto 16px' }} />
                    <p style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', margin: '0 0 8px 0' }}>
                      Uploading Dataset... {uploadProgress}%
                    </p>
                    <div style={{ width: '200px', height: '6px', background: 'var(--border)', borderRadius: '99px', overflow: 'hidden', margin: '0 auto' }}>
                      <div style={{ width: `${uploadProgress}%`, height: '100%', background: 'var(--primary)', transition: 'width 0.1s ease' }} />
                    </div>
                  </div>
                ) : (
                  <>
                    <Cloud size={40} color="var(--primary)" style={{ marginBottom: '16px' }} />
                    <p className="dropzone-title">
                      Drag & Drop CSV / Excel File
                    </p>
                    <p className="dropzone-sub">
                      Supports spreadsheet formats up to 25MB
                    </p>
                    <span className="browse-pill">
                      Browse Files
                    </span>
                  </>
                )}
              </div>
            </div>

          </div>
        </motion.div>
      ) : loading ? (
        <div style={{
          minHeight: '480px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)'
        }}>
          <div style={{ width: '40px', height: '40px', border: '3px solid rgba(108,71,255,0.15)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }} />
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', margin: 0 }}>Initiating AI AutoML engines...</p>
        </div>
      ) : autoGenerateStep === 'analyzing' ? (
        <div style={{ minHeight: '480px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg)' }}>
          <div style={{ width: '100%', maxWidth: '480px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: '16px', padding: '32px', boxShadow: 'var(--shadow-card)' }}>
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <div style={{ width: '48px', height: '48px', background: 'linear-gradient(135deg,#6c47ff,#00c2cb)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', boxShadow: '0 4px 14px rgba(108,71,255,0.3)' }}>
                <Brain size={24} color="#fff" />
              </div>
              <h3 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 6px' }}>AI is Analyzing Your Data</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: 0 }}>Running full ML pipeline & feature selections...</p>
            </div>

            {[
              { icon: FileSpreadsheet, label: 'Reading dataset rows...' },
              { icon: Brain, label: 'Detecting data fields & problem type...' },
              { icon: TrendingUp, label: 'Training ML models & selecting best model...' },
              { icon: Sparkles, label: 'Generating insights & interactive dashboard...' }
            ].map((s, idx) => {
              const isDone = agAnalysisStep > idx;
              const isActive = agAnalysisStep === idx;
              const Icon = s.icon;
              return (
                <div key={idx} style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  background: isActive ? 'rgba(108,71,255,0.08)' : isDone ? 'rgba(16,185,129,0.08)' : 'var(--card-elevated)',
                  border: `1px solid ${isActive ? 'rgba(108,71,255,0.25)' : isDone ? 'rgba(16,185,129,0.2)' : 'var(--border)'}`,
                  marginBottom: '8px',
                  transition: 'all 0.3s ease'
                }}>
                  <div style={{
                    width: '32px',
                    height: '32px',
                    borderRadius: '8px',
                    background: isActive ? 'rgba(108,71,255,0.15)' : isDone ? 'rgba(16,185,129,0.15)' : 'var(--hover-bg)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    {isDone ? <Check size={16} color="#10B981" /> : <Icon size={16} color={isActive ? 'var(--primary)' : 'var(--text-secondary)'} />}
                  </div>
                  <span style={{ fontSize: '13.5px', fontWeight: 600, color: isActive ? 'var(--primary)' : isDone ? '#10B981' : 'var(--text-secondary)' }}>
                    {s.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div style={{ width: '100%', height: '100%' }}>
          <DataSpeakDashboard
            templateName={filename || "Analytics Dashboard"}
            usingSampleData={false}
            mlData={mlData}
            data={rawData}
            onRefresh={() => {
              // Force fresh analysis bypassing cache
              if (selectedDatasetId && filename) {
                handleSelectDataset({ id: selectedDatasetId, name: filename }, true);
              }
            }}
            onBack={() => {
              resetAnalytics();
            }}
          />
        </div>
      )}

    </div>
  );
}
