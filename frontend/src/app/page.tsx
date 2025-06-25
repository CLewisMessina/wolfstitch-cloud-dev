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
  tokens: number;
}

interface ProcessingResult {
  message: string;
  filename: string;
  chunks?: number;
  total_chunks?: number;
  total_tokens?: number;
  average_chunk_size?: number;
  preview?: ChunkPreview[];  // Fixed: Changed from string[] to ChunkPreview[]
  error?: string;
  status?: string;
  job_id?: string;
}

type ProcessingStep = 'upload' | 'processing' | 'complete' | 'error';

// Get API URL based on environment
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
console.log('API URL:', API_URL);

export default function FileProcessor() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [processingStep, setProcessingStep] = useState<ProcessingStep>('upload');
  const [progress, setProgress] = useState(0);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFileDetails, setShowFileDetails] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Process files - either for preview or full download
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
      
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
      });

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
        setProcessingStep('complete');
      }
    } catch (error) {
      console.error('Processing error:', error);
      setError(error instanceof Error ? error.message : 'Unknown error occurred');
      setProcessingStep('error');
    }
  };

  // Download functionality with full processing
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

  // File selection handlers
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

  // Get file icon based on extension
  const getFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase() || '';
    const iconMap: { [key: string]: React.ReactNode } = {
      pdf: <FileText className="w-5 h-5" />,
      docx: <FileText className="w-5 h-5" />,
      doc: <FileText className="w-5 h-5" />,
      txt: <FileText className="w-5 h-5" />,
      md: <FileText className="w-5 h-5" />,
      js: <Code className="w-5 h-5" />,
      jsx: <Code className="w-5 h-5" />,
      ts: <Code className="w-5 h-5" />,
      tsx: <Code className="w-5 h-5" />,
      py: <Code className="w-5 h-5" />,
      json: <Code className="w-5 h-5" />,
      csv: <File className="w-5 h-5" />,
      xlsx: <File className="w-5 h-5" />,
      xls: <File className="w-5 h-5" />,
    };
    return iconMap[extension] || <File className="w-5 h-5" />;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-[#0D1117] to-gray-900 text-white">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <header className="mb-10 text-center">
          <div className="flex items-center justify-center mb-4">
            <Activity className="w-10 h-10 text-[#4ECDC4] mr-3" />
            <h1 className="text-5xl font-bold">
              Wolf<span className="text-[#FF6B47]">stitch</span>
            </h1>
          </div>
          <p className="text-gray-300 text-lg">
            Transform your documents into AI-ready datasets
          </p>
        </header>

        {/* Upload Section */}
        {processingStep === 'upload' && (
          <section className="mb-10">
            <div
              className="border-2 border-dashed border-gray-600 rounded-2xl p-16 text-center cursor-pointer hover:border-[#4ECDC4] transition-colors bg-[rgba(255,255,255,0.05)] backdrop-blur-sm shadow-xl hover:shadow-[rgba(78,205,196,0.2)]"
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
                    Supports 40+ formats • Up to 100MB per file
                  </p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Processing Section */}
        {processingStep === 'processing' && (
          <section className="mb-10">
            <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-8">
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
                  <p className="text-lg font-medium text-gray-900">
                    Processing your file...
                  </p>
                </div>
                
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div 
                    className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                
                <p className="text-sm text-gray-600">
                  {progress < 20 && "Uploading file..."}
                  {progress >= 20 && progress < 70 && "Processing chunks..."}
                  {progress >= 70 && progress < 90 && "Generating export..."}
                  {progress >= 90 && "Finalizing download..."}
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Error Section */}
        {processingStep === 'error' && (
          <section className="mb-10">
            <div className="bg-red-50 border border-red-300 rounded-2xl p-8">
              <div className="flex items-start space-x-3">
                <AlertCircle className="w-6 h-6 text-red-600 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-red-900">Processing Failed</h3>
                  <p className="text-red-700 mt-1">{error}</p>
                  <button
                    onClick={resetApp}
                    className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Results Section */}
        {processingStep === 'complete' && processingResult && (
          <section className="mb-10">
            <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-8">
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center">
                  <CheckCircle className="w-8 h-8 text-[#4ECDC4] mr-3" />
                  <h2 className="text-2xl font-bold text-white">Processing Complete</h2>
                </div>
                <span className="px-3 py-1 bg-[#4ECDC4] text-gray-900 rounded-full text-sm font-medium">
                  Success
                </span>
              </div>

              {/* Results Summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-800 rounded-xl p-4">
                  <p className="text-gray-400 text-sm">Total Chunks</p>
                  <p className="text-2xl font-bold text-white">
                    {processingResult.chunks || processingResult.total_chunks || 0}
                  </p>
                </div>
                <div className="bg-gray-800 rounded-xl p-4">
                  <p className="text-gray-400 text-sm">Total Tokens</p>
                  <p className="text-2xl font-bold text-white">
                    {processingResult.total_tokens || 0}
                  </p>
                </div>
                <div className="bg-gray-800 rounded-xl p-4">
                  <p className="text-gray-400 text-sm">Avg Chunk Size</p>
                  <p className="text-2xl font-bold text-white">
                    {processingResult.average_chunk_size || 
                     (processingResult.total_tokens && processingResult.chunks 
                       ? Math.round(processingResult.total_tokens / processingResult.chunks)
                       : 0)
                    }
                  </p>
                </div>
              </div>

              {/* Preview Section */}
              {processingResult.preview && processingResult.preview.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Preview</h3>
                  <div className="space-y-3">
                    {processingResult.preview.map((chunk, index) => (
                      <div key={index} className="bg-gray-800 rounded-lg p-4">
                        <div className="text-gray-300 text-sm line-clamp-3">
                          {typeof chunk === 'string' ? chunk : chunk.text}
                        </div>
                        <div className="mt-2 text-xs text-gray-500 flex justify-between">
                          <span>Chunk {index + 1}</span>
                          {typeof chunk !== 'string' && chunk.tokens && (
                            <span>{chunk.tokens} tokens</span>
                          )}
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

        {/* File Details Section */}
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
                <div className="space-y-3">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="flex items-center space-x-3 p-3 bg-gray-800 rounded-lg">
                      <div className="flex-shrink-0 text-[#4ECDC4]">
                        {getFileIcon(file.name)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">{file.name}</p>
                        <p className="text-xs text-gray-400">{formatFileSize(file.size)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {/* Footer */}
        <footer className="mt-16 text-center text-gray-400 text-sm">
          <p>Wolfstitch Cloud • Transform Data with Confidence</p>
        </footer>
      </div>
    </div>
  );
}