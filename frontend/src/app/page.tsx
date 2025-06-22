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
  AlertCircle
} from 'lucide-react';

// Types for API responses
interface ChunkObject {
  text: string;
  tokens?: number;
  token_count?: number;
}

interface ProcessingResult {
  message: string;
  filename: string;
  chunks?: number;
  total_tokens?: number;
  preview?: (string | ChunkObject)[];
  error?: string;
  status?: string;
}

const WolfstitchApp = () => {
  // State management
  const [processingStep, setProcessingStep] = useState<'upload' | 'processing' | 'completed' | 'error'>('upload');
  const [progress, setProgress] = useState(0);
  const [showFileDetails, setShowFileDetails] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Configuration - Now using environment variables
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.wolfstitch.dev';
  const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'Wolfstitch';
  const ENVIRONMENT = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';

  // File processing function
  const processFiles = async (files: File[]) => {
    if (files.length === 0) return;

    setError(null);
    setProcessingStep('processing');
    setProgress(0);

    try {
      // Animate progress
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 15;
        });
      }, 200);

      // Process the first file
      const file = files[0];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('tokenizer', 'word-estimate');
      formData.append('max_tokens', '1024');

      console.log(`Processing file with API: ${API_BASE_URL}`);
      console.log('FormData contents:', {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type
      });

      const fullURL = `${API_BASE_URL}/api/v1/quick-process`;
      console.log('Full API URL:', fullURL);

      const response = await fetch(fullURL, {
        method: 'POST',
        body: formData,
        mode: 'cors',
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API Error: ${response.status} - ${errorText}`);
      }

      const result: ProcessingResult = await response.json();
      
      setProgress(100);
      setProcessingResult(result);
      
      setTimeout(() => {
        setProcessingStep('completed');
      }, 500);

      console.log('Processing completed successfully:', result);

    } catch (error) {
      console.error('Processing error:', error);
      setError(error instanceof Error ? error.message : 'Unknown error occurred');
      setProcessingStep('error');
    }
  };

  // Enhanced download functionality that handles both string and object chunk formats
  const downloadResults = () => {
    if (!processingResult) return;

    try {
      // Safe chunk processing - Handle both formats
      const jsonlContent = processingResult.preview?.map((chunk, index) => {
        // Extract text and tokens safely
        let text: string;
        let tokens: number;
        
        if (typeof chunk === 'string') {
          text = chunk;
          tokens = Math.floor((processingResult.total_tokens || 131) / (processingResult.chunks || 1));
        } else if (typeof chunk === 'object' && chunk !== null) {
          const chunkObj = chunk as ChunkObject;
          text = chunkObj.text || String(chunk);
          tokens = chunkObj.tokens || chunkObj.token_count || Math.floor((processingResult.total_tokens || 131) / (processingResult.chunks || 1));
        } else {
          text = String(chunk);
          tokens = Math.floor((processingResult.total_tokens || 131) / (processingResult.chunks || 1));
        }
        
        return JSON.stringify({
          text: text,
          chunk_id: index + 1,
          tokens: tokens,
          metadata: {
            filename: processingResult.filename,
            processed_at: new Date().toISOString()
          }
        });
      }).join('\n') || '';

      // Create and download file
      const blob = new Blob([jsonlContent], { type: 'application/jsonl' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${processingResult.filename.replace(/\.[^/.]+$/, '')}_processed.jsonl`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      console.log('Download initiated:', link.download);
    } catch (error) {
      console.error('Download failed:', error);
      setError('Failed to generate download file. Please try processing again.');
    }
  };

  // File selection handlers
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
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

  // Circular progress component
  const CircularProgress = ({ percentage, size = 140 }: { percentage: number; size?: number }) => {
    const circumference = 2 * Math.PI * 45;
    const strokeDasharray = circumference;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div className="relative" style={{ width: size, height: size }}>
        <svg 
          className="transform -rotate-90" 
          style={{ width: size, height: size }}
          viewBox="0 0 100 100"
        >
          <circle
            cx="50"
            cy="50"
            r="45"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-gray-700"
          />
          <circle
            cx="50"
            cy="50"
            r="45"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            className="text-[#4ECDC4] transition-all duration-300 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">{Math.round(percentage)}%</span>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white relative overflow-hidden">
      {/* Background gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 opacity-80"></div>
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-[#FF6B47]/20 via-transparent to-[#4ECDC4]/20"></div>
      
      {/* Header */}
      <header className="relative z-10 border-b border-gray-800 bg-[rgba(0,0,0,0.3)] backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-br from-[#FF6B47] to-[#4ECDC4] rounded-lg flex items-center justify-center shadow-lg">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold">{APP_NAME}</h1>
              <p className="text-xs text-gray-400">AI Dataset Preparation</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-400">
                {ENVIRONMENT === 'production' ? 'Production Ready' : 'Development Mode'}
              </span>
            </div>
            <div className="w-2 h-2 bg-[#4ECDC4] rounded-full animate-pulse"></div>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
        
        {/* Hero Section */}
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
                🚧 Development Mode - API: {API_BASE_URL}
              </p>
            </div>
          )}
        </section>

        {/* Upload Section */}
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
                accept=".pdf,.docx,.txt,.md,.py,.js,.json,.csv,.pptx,.xlsx,.doc,.rtf,.html,.htm,.xml,.epub"
              />
              <div className="space-y-6">
                <div className="mx-auto w-20 h-20 bg-[#FF6B47] rounded-full flex items-center justify-center shadow-xl">
                  <Upload className="w-10 h-10 text-white" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-white mb-2">Upload Your Documents</h3>
                  <p className="text-gray-300">
                    Drag and drop files here or click to browse
                  </p>
                </div>
                <div className="space-y-4">
                  <button 
                    type="button"
                    className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105"
                  >
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

        {/* Processing Section */}
        {processingStep === 'processing' && (
          <section className="text-center space-y-8">
            <div className="flex flex-col items-center space-y-8">
              <CircularProgress percentage={progress} />
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-white">
                  Processing Your Document
                </h3>
                <p className="text-gray-300">
                  Parsing content, cleaning text, and creating intelligent chunks...
                </p>
              </div>
            </div>
          </section>
        )}

        {/* Error Section */}
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

        {/* Success Section */}
        {processingStep === 'completed' && processingResult && (
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
                    {processingResult.chunks || 0}
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
                    {Math.round((processingResult.total_tokens || 0) / (processingResult.chunks || 1))}
                  </div>
                  <div className="text-sm text-gray-300">Avg Tokens/Chunk</div>
                </div>
              </div>

              {/* Preview - FIXED VERSION */}
              {processingResult.preview && processingResult.preview.length > 0 && (
                <div className="bg-gray-800/50 rounded-xl p-6 mb-8 border border-gray-600">
                  <h4 className="font-semibold text-white mb-4 flex items-center">
                    <Eye className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                    Preview (First Chunks)
                  </h4>
                  <div className="space-y-4">
                    {processingResult.preview.slice(0, 3).map((chunk, index) => (
                      <div key={index} className="bg-gray-900 rounded-lg border border-gray-700 p-4">
                        <div className="font-mono text-sm text-gray-300 leading-relaxed">
                          {/* ✅ SAFE RENDERING - Handle both string and object formats */}
                          {typeof chunk === 'string' 
                            ? chunk 
                            : typeof chunk === 'object' && chunk !== null && 'text' in chunk
                              ? (chunk as ChunkObject).text
                              : String(chunk)
                          }
                        </div>
                        <div className="mt-2 text-xs text-gray-500">
                          Chunk {index + 1}
                          {/* ✅ SAFE TOKEN DISPLAY */}
                          {typeof chunk === 'object' && chunk !== null && ('tokens' in chunk || 'token_count' in chunk) && (
                            <span className="ml-2">• {(chunk as ChunkObject).tokens || (chunk as ChunkObject).token_count} tokens</span>
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
                  <Upload className="w-5 h-5 mr-2" />
                  Process Another File
                </button>
                
                <button
                  onClick={downloadResults}
                  className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#4ECDC4] to-[#44B8B5] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(78,205,196,0.3)] transition-all duration-300 transform hover:scale-105"
                >
                  <Download className="w-5 h-5 mr-2" />
                  Download JSONL
                </button>
              </div>
            </div>
          </section>
        )}

        {/* File Details Panel */}
        {selectedFiles.length > 0 && showFileDetails && (
          <section className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white flex items-center">
                <Folder className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                Selected Files ({selectedFiles.length})
              </h3>
              <button
                onClick={() => setShowFileDetails(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <ChevronDown className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-3">
              {selectedFiles.map((file, index) => (
                <div key={index} className="flex items-center space-x-3 p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                  {getFileIcon(file.name)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{file.name}</p>
                    <p className="text-xs text-gray-400">{formatFileSize(file.size)}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Features Section */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 py-8">
          <div className="text-center space-y-4 p-6 bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl border border-gray-700">
            <div className="w-12 h-12 bg-[#FF6B47]/20 rounded-full flex items-center justify-center mx-auto">
              <FileText className="w-6 h-6 text-[#FF6B47]" />
            </div>
            <h3 className="text-lg font-semibold text-white">40+ File Formats</h3>
            <p className="text-gray-300 text-sm">
              PDF, DOCX, TXT, code files, presentations, and more
            </p>
          </div>
          
          <div className="text-center space-y-4 p-6 bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl border border-gray-700">
            <div className="w-12 h-12 bg-[#4ECDC4]/20 rounded-full flex items-center justify-center mx-auto">
              <Zap className="w-6 h-6 text-[#4ECDC4]" />
            </div>
            <h3 className="text-lg font-semibold text-white">Lightning Fast</h3>
            <p className="text-gray-300 text-sm">
              Process documents in seconds with intelligent chunking
            </p>
          </div>
          
          <div className="text-center space-y-4 p-6 bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl border border-gray-700">
            <div className="w-12 h-12 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto">
              <Activity className="w-6 h-6 text-purple-400" />
            </div>
            <h3 className="text-lg font-semibold text-white">AI-Ready Output</h3>
            <p className="text-gray-300 text-sm">
              JSONL format optimized for machine learning pipelines
            </p>
          </div>
        </section>
      </div>
    </div>
  );
};

export default WolfstitchApp;