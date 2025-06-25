// src\app\page.tsx
'use client';

import React, { useState, useRef } from 'react';
import { 
  Upload, 
  File, 
  Folder, 
  Code, 
  FileText, 
  Download, 
  CheckCircle, 
  Eye,
  ChevronDown,
  Zap,
  Activity,
  AlertCircle,
  Loader2
} from 'lucide-react';

// Fixed Types for API responses - matching actual API response structure
interface ChunkPreview {
  text: string;
  tokens?: number;
  token_count?: number;  // API returns token_count
  chunk_index?: number;
}

interface ProcessingResult {
  message?: string;
  filename: string;
  chunks?: ChunkPreview[];  // API returns chunks array
  preview?: ChunkPreview[];  // For backward compatibility
  total_chunks?: number;
  total_tokens?: number;
  average_chunk_size?: number;
  error?: string;
  status?: string;
  job_id?: string;
  enhanced?: boolean;
  processing_time?: number;
  file_info?: {
    filename?: string;
    size?: number;
    format?: string;
    [key: string]: unknown;  // Allow additional properties
  };
  metadata?: {
    [key: string]: unknown;  // Allow any metadata properties
  };
}

type ProcessingStep = 'upload' | 'processing' | 'complete' | 'error';

// Get API URL based on environment
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'Wolfstitch';
const ENVIRONMENT = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';

console.log('API URL:', API_URL);

export default function FileProcessor() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [processingStep, setProcessingStep] = useState<ProcessingStep>('upload');
  const [progress, setProgress] = useState(0);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFileDetails, setShowFileDetails] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Circular progress component (from production version)
  const CircularProgress = ({ percentage, size = 140 }: { percentage: number; size?: number }) => (
    <div className="relative inline-flex items-center justify-center">
      <svg
        className="transform -rotate-90"
        width={size}
        height={size}
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 8}
          stroke="currentColor"
          strokeWidth="6"
          fill="transparent"
          className="text-gray-700"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size / 2 - 8}
          stroke="currentColor"
          strokeWidth="6"
          fill="transparent"
          strokeDasharray={`${2 * Math.PI * (size / 2 - 8)}`}
          strokeDashoffset={`${2 * Math.PI * (size / 2 - 8) * (1 - percentage / 100)}`}
          className="text-[#FF6B47] transition-all duration-500 ease-out"
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-3xl font-bold text-white">
          {Math.round(percentage)}%
        </span>
        <span className="text-xs text-gray-300 mt-1">
          {percentage < 30 && "Parsing"}
          {percentage >= 30 && percentage < 70 && "Cleaning"}
          {percentage >= 70 && "Chunking"}
        </span>
      </div>
    </div>
  );

  // Process files - either for preview or full download (enhanced from dev version)
  const processFiles = async (files: File[], isFullProcessing: boolean = false) => {
    if (files.length === 0) return;

    const file = files[0]; // Process first file for now
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tokenizer', 'gpt-4');
    formData.append('max_tokens', '1000');
    formData.append('chunk_method', 'paragraph');
    formData.append('preserve_structure', 'true');
    
    if (isFullProcessing) {
      formData.append('export_format', 'jsonl');
    }

    try {
      setProcessingStep('processing');
      setProgress(10);
      setError(null);

      // Choose endpoint based on processing type
      const endpoint = isFullProcessing ? '/api/v1/process-full' : '/api/v1/quick-process';
      
      // Animate progress (from production version)
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 15;
        });
      }, 200);

      console.log(`Processing file with API: ${API_URL}`);
      console.log('FormData contents:', {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type || 'application/octet-stream'  // Mobile fix
      });
      
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
        mode: 'cors',
      });

      clearInterval(progressInterval);

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Processing failed');
      }

      if (isFullProcessing) {
        // Handle full processing with job tracking
        return data.job_id;
      } else {
        // Handle quick preview
        setProgress(100);
        setProcessingResult(data);
        setTimeout(() => {
          setProcessingStep('complete');
        }, 500);
      }
    } catch (error) {
      console.error('Processing error:', error);
      setError(error instanceof Error ? error.message : 'Unknown error occurred');
      setProcessingStep('error');
    }
  };

  // Download functionality with full processing (enhanced from dev version)
  const downloadResults = async () => {
    if (!selectedFiles[0]) return;
    
    try {
      setProcessingStep('processing');
      setProgress(0);
      setError(null);
      
      // Call the full processing endpoint
      const jobId = await processFiles(selectedFiles, true);
      
      console.log('Full processing started:', jobId);
      
      // Poll for job status
      let jobComplete = false;
      let downloadUrl = null;
      
      while (!jobComplete) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // Poll every second
        
        const statusResponse = await fetch(`${API_URL}/api/v1/jobs/${jobId}/status`);
        if (!statusResponse.ok) {
          throw new Error('Failed to check job status');
        }
        
        const status = await statusResponse.json();
        
        // Update progress
        setProgress(status.progress || 0);
        
        if (status.status === 'completed') {
          jobComplete = true;
          downloadUrl = status.download_url;
          console.log('Processing completed:', status);
        } else if (status.status === 'failed') {
          throw new Error(status.error || 'Processing failed');
        }
      }
      
      if (downloadUrl) {
        // Download the file
        console.log('Downloading from:', downloadUrl);
        
        // For development, construct full URL if needed
        const fullDownloadUrl = downloadUrl.startsWith('http') 
          ? downloadUrl 
          : `${API_URL}${downloadUrl}`;
        
        // Create a temporary anchor element to trigger download
        const link = document.createElement('a');
        link.href = fullDownloadUrl;
        link.download = selectedFiles[0].name.replace(/\.[^/.]+$/, '') + '_processed.jsonl';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        setProcessingStep('complete');
        setProgress(100);
        console.log('Download initiated successfully');
      }
      
    } catch (error) {
      console.error('Download error:', error);
      setError(error instanceof Error ? error.message : 'Download failed');
      setProcessingStep('error');
    }
  };

  // File selection handlers (enhanced with mobile debugging)
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    // Mobile fix: Log file details for debugging
    files.forEach(file => {
      console.log('Selected file details:', {
        name: file.name,
        size: file.size,
        type: file.type || 'unknown',
        lastModified: file.lastModified
      });
    });
    setSelectedFiles(files);
    if (files.length > 0) {
      processFiles(files);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const files = Array.from(event.dataTransfer.files);
    setSelectedFiles(files);
    if (files.length > 0) {
      processFiles(files);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  // Reset to initial state
  const resetApp = () => {
    setProcessingStep('upload');
    setProgress(0);
    setSelectedFiles([]);
    setProcessingResult(null);
    setError(null);
    setShowFileDetails(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Get file icon based on extension (enhanced from production)
  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'pdf': return <FileText className="w-5 h-5 text-red-400" />;
      case 'docx': case 'doc': return <FileText className="w-5 h-5 text-blue-400" />;
      case 'pptx': case 'ppt': return <FileText className="w-5 h-5 text-orange-400" />;
      case 'xlsx': case 'xls': return <FileText className="w-5 h-5 text-green-400" />;
      case 'txt': case 'md': case 'markdown': return <FileText className="w-5 h-5 text-gray-400" />;
      case 'py': case 'js': case 'ts': case 'json': return <Code className="w-5 h-5 text-purple-400" />;
      default: return <File className="w-5 h-5 text-gray-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#1a1a2e] via-[#16213e] to-[#0f1419]">
      {/* Header - Enhanced from production version */}
      <header className="bg-[rgba(26,26,46,0.8)] border-b border-gray-700 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-[#FF6B47] to-[#E85555] rounded-lg flex items-center justify-center shadow-lg">
              <div className="w-6 h-6 border-2 border-white rounded transform rotate-12 opacity-90"></div>
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">{APP_NAME}</h1>
              <p className="text-xs text-gray-400">AI Dataset Platform</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-[#4ECDC4]" />
              <span className="text-sm text-gray-300">
                {ENVIRONMENT === 'production' ? 'Production Ready' : 'Development Mode'}
              </span>
            </div>
            <div className="w-2 h-2 bg-[#4ECDC4] rounded-full animate-pulse"></div>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        
        {/* Hero Section - Enhanced from production */}
        <section className="text-center space-y-4 py-8">
          <h2 className="text-4xl font-bold text-white mb-2">
            Transform Documents into 
            <span className="bg-gradient-to-r from-[#FF6B47] to-[#4ECDC4] bg-clip-text text-transparent"> AI-Ready Datasets</span>
          </h2>
          <p className="text-gray-300 text-lg max-w-2xl mx-auto">
            Professional-grade document processing with intelligent chunking, 40+ file formats, and beautiful export options
          </p>
          {ENVIRONMENT === 'development' && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 mx-auto max-w-md">
              <p className="text-yellow-300 text-sm">
                🚧 Development Mode - API: {API_URL}
              </p>
            </div>
          )}
        </section>

        {/* Upload Section - Enhanced styling from production */}
        {processingStep === 'upload' && (
          <section className="space-y-6">
            <div 
              className="relative border-2 border-dashed border-[#FF6B47] bg-[rgba(255,107,71,0.1)] hover:bg-[rgba(255,107,71,0.15)] rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer shadow-lg shadow-[rgba(255,107,71,0.2)]"
              onClick={() => fileInputRef.current?.click()}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept=".pdf,.docx,.txt,.md,.py,.js,.json,.csv,.pptx,.xlsx"
              />
              <div className="space-y-6">
                <div className="mx-auto w-20 h-20 bg-gradient-to-br from-[#FF6B47] to-[#E85555] rounded-full flex items-center justify-center shadow-xl">
                  <Upload className="w-10 h-10 text-white" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white mb-2">
                    Drop files here or click to browse
                  </p>
                  <p className="text-gray-300">
                    PDF, DOCX, TXT, code files, presentations, or entire folders
                  </p>
                </div>
                <div className="space-y-4">
                  <button className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105">
                    <Upload className="w-5 h-5 mr-2" />
                    Choose Files
                  </button>
                  <p className="text-sm text-gray-400">
                    or drag and drop your documents here
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Processing Section - Using production's circular progress with dev's enhanced processing */}
        {processingStep === 'processing' && (
          <section className="text-center space-y-8">
            <div className="flex flex-col items-center space-y-8">
              <CircularProgress percentage={progress} />
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-white">
                  Processing Your Document
                </h3>
                <p className="text-gray-300">
                  {progress < 20 && "Uploading file..."}
                  {progress >= 20 && progress < 70 && "Processing chunks..."}
                  {progress >= 70 && progress < 90 && "Generating export..."}
                  {progress >= 90 && "Finalizing download..."}
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Error Section - Enhanced from production styling */}
        {processingStep === 'error' && (
          <section className="text-center space-y-6">
            <div className="flex flex-col items-center space-y-6">
              <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center">
                <AlertCircle className="w-10 h-10 text-red-400" />
              </div>
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-white">
                  Processing Failed
                </h3>
                <p className="text-gray-300 max-w-md mx-auto">
                  {error || 'Something went wrong while processing your file. Please try again.'}
                </p>
              </div>
              <button
                onClick={resetApp}
                className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105"
              >
                Try Again
              </button>
            </div>
          </section>
        )}

        {/* Results Section - Enhanced with production styling and dev functionality */}
        {processingStep === 'complete' && processingResult && (
          <section className="space-y-6">
            <div className="text-center space-y-4">
              <div className="w-20 h-20 bg-[#4ECDC4]/20 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle className="w-10 h-10 text-[#4ECDC4]" />
              </div>
              <h3 className="text-2xl font-bold text-white">
                Processing Complete!
              </h3>
              <p className="text-gray-300">
                Your document has been successfully processed and chunked
              </p>
            </div>

            {/* Results Summary */}
            <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-[#FF6B47] mb-1">
                    {processingResult.total_chunks || 0}
                  </div>
                  <div className="text-sm text-gray-300">Chunks Created</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-[#4ECDC4] mb-1">
                    {processingResult.total_tokens?.toLocaleString() || '0'}
                  </div>
                  <div className="text-sm text-gray-300">Total Tokens</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-white mb-1">
                    {processingResult.total_tokens && processingResult.total_chunks 
                      ? Math.round(processingResult.total_tokens / processingResult.total_chunks)
                      : 0
                    }
                  </div>
                  <div className="text-sm text-gray-300">Avg Tokens/Chunk</div>
                </div>
              </div>

              {/* Preview Section - Enhanced with dev's better data handling */}
              {((processingResult.chunks && processingResult.chunks.length > 0) || 
                (processingResult.preview && processingResult.preview.length > 0)) && (
                <div className="bg-gray-800/50 rounded-xl p-6 mb-8 border border-gray-600">
                  <h4 className="font-semibold text-white mb-4 flex items-center">
                    <Eye className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                    Preview (First Chunks)
                  </h4>
                  <div className="space-y-4">
                    {(processingResult.chunks || processingResult.preview || []).slice(0, 3).map((chunk, index) => (
                      <div key={index} className="bg-gray-900 rounded-lg border border-gray-700 p-4">
                        <div className="font-mono text-sm text-gray-300 leading-relaxed line-clamp-3">
                          {chunk.text}
                        </div>
                        <div className="mt-2 text-xs text-gray-500 flex justify-between">
                          <span>Chunk {chunk.chunk_index !== undefined ? chunk.chunk_index + 1 : index + 1}</span>
                          <span>{chunk.token_count || chunk.tokens || 0} tokens</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <button
                  onClick={resetApp}
                  className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105"
                >
                  <Zap className="w-5 h-5 mr-2" />
                  Process More Files
                </button>
                <button 
                  onClick={downloadResults}
                  className="inline-flex items-center px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium transition-colors"
                >
                  <Download className="w-5 h-5 mr-2" />
                  Download Results
                </button>
              </div>
            </div>
          </section>
        )}

        {/* File Details Section - Enhanced with production styling */}
        {selectedFiles.length > 0 && processingStep !== 'upload' && (
          <section className="space-y-4">
            <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold text-white flex items-center">
                  <Folder className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                  Selected Files ({selectedFiles.length})
                </h3>
                <button 
                  onClick={() => setShowFileDetails(!showFileDetails)}
                  className="flex items-center px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded-lg transition-all duration-200 text-sm"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  {showFileDetails ? 'Hide' : 'Show'} Details
                  <ChevronDown className={`w-4 h-4 ml-2 transition-transform duration-200 ${showFileDetails ? 'rotate-180' : ''}`} />
                </button>
              </div>
              
              {showFileDetails && (
                <div className="space-y-2">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-600">
                      <div className="flex items-center space-x-3">
                        {getFileIcon(file.name)}
                        <span className="font-medium text-white">{file.name}</span>
                      </div>
                      <span className="text-sm text-gray-400">{formatFileSize(file.size)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}