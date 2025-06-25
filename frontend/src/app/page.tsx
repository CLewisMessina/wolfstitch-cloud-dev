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
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-blue-900 to-gray-900">
      <div className="max-w-5xl mx-auto px-4 py-12">
        {/* Header */}
        <header className="text-center mb-12">
          <div className="flex items-center justify-center mb-4">
            <Activity className="w-8 h-8 text-teal-400 mr-2" />
            <h1 className="text-4xl font-bold text-white">
              Wolf<span className="text-orange-500">stitch</span>
            </h1>
          </div>
          <p className="text-gray-300 text-lg">
            Transform your documents into AI-ready datasets
          </p>
        </header>

        {/* Main content area */}
        <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-8">
          {/* Upload Section */}
          {processingStep === 'upload' && (
            <div>
              <h2 className="text-3xl font-bold text-center mb-2 text-white">
                Transform Documents into <span className="text-orange-500">AI-Ready</span> Datasets
              </h2>
              <p className="text-center text-gray-400 mb-8">
                Professional-grade document processing with intelligent chunking, 40+ file formats, and beautiful export options
              </p>
              
              <div
                className="border-2 border-dashed border-orange-500/50 rounded-xl p-12 text-center cursor-pointer hover:border-orange-500 transition-colors bg-gray-700/30"
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
                <div className="space-y-4">
                  <div className="mx-auto w-16 h-16 bg-orange-500 rounded-full flex items-center justify-center">
                    <Upload className="w-8 h-8 text-white" />
                  </div>
                  <div>
                    <p className="text-xl font-semibold text-white mb-1">
                      Drop files here or click to browse
                    </p>
                    <p className="text-gray-400 text-sm">
                      PDF, DOCX, TXT, code files, presentations, or entire folders
                    </p>
                  </div>
                  <button className="px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition-colors inline-flex items-center">
                    <Upload className="w-4 h-4 mr-2" />
                    Choose Files
                  </button>
                  <p className="text-xs text-gray-500">
                    or drag and drop your documents here
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Processing Section */}
          {processingStep === 'processing' && (
            <div className="text-center py-12">
              <div className="inline-flex items-center space-x-3 mb-6">
                <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
                <p className="text-xl font-medium text-white">
                  Processing your file...
                </p>
              </div>
              
              <div className="max-w-md mx-auto">
                <div className="w-full bg-gray-700 rounded-full h-3">
                  <div 
                    className="bg-orange-500 h-3 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                
                <p className="text-sm text-gray-400 mt-3">
                  {progress < 20 && "Uploading file..."}
                  {progress >= 20 && progress < 70 && "Processing chunks..."}
                  {progress >= 70 && progress < 90 && "Generating export..."}
                  {progress >= 90 && "Finalizing download..."}
                </p>
              </div>
            </div>
          )}

          {/* Error Section */}
          {processingStep === 'error' && (
            <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6">
              <div className="flex items-start space-x-3">
                <AlertCircle className="w-6 h-6 text-red-500 mt-0.5" />
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-red-400">Processing Failed</h3>
                  <p className="text-red-300 mt-1">{error}</p>
                  <button
                    onClick={resetApp}
                    className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Results Section */}
          {processingStep === 'complete' && processingResult && (
            <div>
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center">
                  <CheckCircle className="w-8 h-8 text-teal-400 mr-3" />
                  <h2 className="text-2xl font-bold text-white">Processing Complete</h2>
                </div>
                <span className="px-3 py-1 bg-teal-500 text-white rounded-full text-sm font-medium">
                  Success
                </span>
              </div>

              {/* Results Summary */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Total Chunks</p>
                  <p className="text-2xl font-bold text-white">
                    {processingResult.total_chunks || 0}
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Total Tokens</p>
                  <p className="text-2xl font-bold text-white">
                    {processingResult.total_tokens || 0}
                  </p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4">
                  <p className="text-gray-400 text-sm">Avg Chunk Size</p>
                  <p className="text-2xl font-bold text-white">
                    {processingResult.total_tokens && processingResult.total_chunks 
                      ? Math.round(processingResult.total_tokens / processingResult.total_chunks)
                      : 0
                    }
                  </p>
                </div>
              </div>

              {/* Preview Section */}
              {((processingResult.chunks && processingResult.chunks.length > 0) || 
                (processingResult.preview && processingResult.preview.length > 0)) && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-white mb-3">Preview</h3>
                  <div className="space-y-3">
                    {(processingResult.chunks || processingResult.preview || []).map((chunk, index) => (
                      <div key={index} className="bg-gray-700/50 rounded-lg p-4">
                        <div className="text-gray-300 text-sm line-clamp-3">
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
                  className="px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-semibold transition-colors inline-flex items-center justify-center"
                >
                  <Zap className="w-5 h-5 mr-2" />
                  Process More Files
                </button>
                <button 
                  onClick={downloadResults}
                  className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors inline-flex items-center justify-center"
                >
                  <Download className="w-5 h-5 mr-2" />
                  Download Results
                </button>
              </div>
            </div>
          )}
        </div>

        {/* File Details Section */}
        {selectedFiles.length > 0 && processingStep !== 'upload' && (
          <div className="mt-6 bg-gray-800/50 backdrop-blur rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white flex items-center">
                <Folder className="w-5 h-5 mr-2 text-teal-400" />
                Selected Files ({selectedFiles.length})
              </h3>
              <button 
                onClick={() => setShowFileDetails(!showFileDetails)}
                className="flex items-center px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white rounded-lg transition-all duration-200 text-sm"
              >
                <Eye className="w-4 h-4 mr-1.5" />
                {showFileDetails ? 'Hide' : 'Show'} Details
                <ChevronDown className={`w-4 h-4 ml-1.5 transition-transform duration-200 ${showFileDetails ? 'rotate-180' : ''}`} />
              </button>
            </div>
            
            {showFileDetails && (
              <div className="space-y-2">
                {selectedFiles.map((file, index) => (
                  <div key={index} className="flex items-center space-x-3 p-3 bg-gray-700/50 rounded-lg">
                    <div className="flex-shrink-0 text-teal-400">
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
        )}

        {/* Footer */}
        <footer className="mt-12 text-center text-gray-500 text-sm">
          <p>Wolfstitch Cloud • Transform Data with Confidence</p>
        </footer>
      </div>
    </div>
  );
}