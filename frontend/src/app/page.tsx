'use client';

import React, { useState, useRef } from 'react';
import { 
  Upload, 
  FileText, 
  Download, 
  CheckCircle, 
  Eye,
  Zap,
  Activity,
  AlertCircle,
  RefreshCw
} from 'lucide-react';

// Fixed Types for API responses
interface ChunkPreview {
  text: string;
  tokens: number;
  chunk_index?: number;
  word_count?: number;
}

interface FullChunk {
  text: string;
  chunk_id: number;
  token_count: number;
  word_count: number;
  chunk_index: number;
}

interface ProcessingResult {
  message?: string;
  filename: string;
  chunks?: number;
  total_chunks?: number;
  total_tokens?: number;
  average_chunk_size?: number;
  preview?: ChunkPreview[];
  data?: FullChunk[];  // Full chunks when requested
  error?: string;
  status?: string;
  job_id?: string;
  processing_time?: number;
  file_info?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  full_chunks_included?: boolean;
}

const WolfstitchApp = () => {
  // State management
  const [processingStep, setProcessingStep] = useState<'upload' | 'processing' | 'completed' | 'error'>('upload');
  const [progress, setProgress] = useState(0);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  
  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Configuration - Using environment variables
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.wolfstitch.dev';
  const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'Wolfstitch';

  // Enhanced file processing function
  const processFiles = async (files: File[], downloadImmediately: boolean = false) => {
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
      
      // Use different endpoint if downloading immediately
      const endpoint = downloadImmediately 
        ? '/api/v1/process-and-download' 
        : '/api/v1/quick-process';
      
      // Add query param for full chunks if downloading
      const url = downloadImmediately 
        ? `${API_BASE_URL}${endpoint}?return_full_chunks=true`
        : `${API_BASE_URL}${endpoint}`;

      console.log(`Processing file with API: ${url}`);
      console.log('FormData contents:', {
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type || 'application/octet-stream'
      });

      const response = await fetch(url, {
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
      
      // If we got full chunks and should download immediately
      if (downloadImmediately && result.data) {
        downloadFullResults(result);
        // Don't update the main result to avoid confusion
        if (!processingResult) {
          setProcessingResult(result);
        }
      } else {
        setProcessingResult(result);
      }
      
      if (!downloadImmediately) {
        setTimeout(() => {
          setProcessingStep('completed');
        }, 500);
      }

      console.log('Processing completed successfully:', result);

    } catch (error) {
      console.error('Processing error:', error);
      setError(error instanceof Error ? error.message : 'Unknown error occurred');
      setProcessingStep('error');
    } finally {
      setIsDownloading(false);
    }
  };

  // Download full results with complete text
  const downloadFullResults = (result: ProcessingResult) => {
    if (!result.data || !Array.isArray(result.data)) {
      console.error('No full chunk data available');
      alert('Full chunk data not available. The file may need to be reprocessed.');
      return;
    }

    // Create JSONL content with FULL text
    const jsonlContent = result.data.map((chunk: FullChunk) => 
      JSON.stringify({
        text: chunk.text,  // Full text, not truncated!
        chunk_id: chunk.chunk_id,
        tokens: chunk.token_count,
        word_count: chunk.word_count,
        metadata: {
          filename: result.filename,
          processed_at: new Date().toISOString(),
          chunk_index: chunk.chunk_index,
          job_id: result.job_id
        }
      })
    ).join('\n');

    // Create and download file
    const blob = new Blob([jsonlContent], { type: 'application/jsonl' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${result.filename.replace(/\.[^/.]+$/, '')}_processed_full.jsonl`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    console.log('Full download completed:', link.download);
  };

  // Download preview only (original functionality)
  const downloadPreview = () => {
    if (!processingResult) return;

    const jsonlContent = processingResult.preview?.map((chunk, index) => 
      JSON.stringify({
        text: typeof chunk === 'string' ? chunk : chunk.text,
        chunk_id: index + 1,
        tokens: typeof chunk === 'string' 
          ? Math.floor((processingResult.total_tokens || 0) / (processingResult.chunks || 1))
          : chunk.tokens,
        metadata: {
          filename: processingResult.filename,
          processed_at: new Date().toISOString(),
          type: 'preview'
        }
      })
    ).join('\n') || '';

    const blob = new Blob([jsonlContent], { type: 'application/jsonl' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${processingResult.filename.replace(/\.[^/.]+$/, '')}_preview.jsonl`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    console.log('Preview download completed:', link.download);
  };

  // Main download function - reprocesses to get full chunks
  const downloadResults = async () => {
    if (!processingResult || !selectedFiles.length) return;

    try {
      setIsDownloading(true);
      console.log('Re-processing file to get full chunks for download...');
      
      // Re-process the file with full chunks flag
      await processFiles(selectedFiles, true);
      
    } catch (error) {
      console.error('Download error:', error);
      alert('Failed to download full results. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };

  // File selection handlers
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
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
    setIsDownloading(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Circular progress component
  const CircularProgress = ({ percentage }: { percentage: number }) => {
    const radius = 50;
    const strokeWidth = 8;
    const normalizedRadius = radius - strokeWidth * 2;
    const circumference = normalizedRadius * 2 * Math.PI;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <svg
        height={radius * 2}
        width={radius * 2}
        className="transform -rotate-90"
      >
        <circle
          stroke="#374151"
          fill="transparent"
          strokeWidth={strokeWidth}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
        />
        <circle
          stroke="url(#gradient)"
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference + ' ' + circumference}
          style={{ strokeDashoffset }}
          r={normalizedRadius}
          cx={radius}
          cy={radius}
          className="transition-all duration-300 ease-in-out"
        />
        <defs>
          <linearGradient id="gradient">
            <stop offset="0%" stopColor="#FF6B47" />
            <stop offset="100%" stopColor="#4ECDC4" />
          </linearGradient>
        </defs>
      </svg>
    );
  };

  return (
    <div className="min-h-screen bg-[#0B0F1A] text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-[rgba(11,15,26,0.8)] border-b border-gray-800">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="w-10 h-10 bg-gradient-to-br from-[#FF6B47] to-[#E85555] rounded-xl flex items-center justify-center shadow-lg">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-[#FF6B47] to-[#4ECDC4] bg-clip-text text-transparent">
                  {APP_NAME}
                </h1>
                <p className="text-xs text-gray-400">Intelligent Document Processing</p>
              </div>
            </div>
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-2">
                <Activity className="w-4 h-4 text-[#4ECDC4]" />
                <span className="text-sm text-gray-300">v2.0</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-12 max-w-4xl">
        {/* Upload Section */}
        {processingStep === 'upload' && (
          <section>
            <div className="text-center mb-12 space-y-4">
              <h2 className="text-4xl font-bold">
                Transform Your Documents into
                <span className="block bg-gradient-to-r from-[#FF6B47] to-[#4ECDC4] bg-clip-text text-transparent">
                  AI-Ready Chunks
                </span>
              </h2>
              <p className="text-gray-300 text-lg max-w-2xl mx-auto">
                Upload any document and watch as Wolfstitch intelligently processes, cleans, and chunks your content for optimal AI consumption.
              </p>
            </div>

            {/* Upload Area */}
            <div className="mb-8">
              <div
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="relative group"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  accept=".pdf,.doc,.docx,.txt,.md,.py,.js,.jsx,.ts,.tsx,.json,.csv,.html,.epub,.pptx"
                />
                
                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-gray-600 rounded-2xl p-12 text-center cursor-pointer transition-all duration-300 hover:border-[#4ECDC4] hover:bg-[rgba(78,205,196,0.05)] group-hover:shadow-lg group-hover:shadow-[rgba(78,205,196,0.1)]"
                >
                  <Upload className="w-16 h-16 mx-auto mb-4 text-gray-400 group-hover:text-[#4ECDC4] transition-colors" />
                  <h3 className="text-xl font-semibold mb-2">
                    Drop your files here
                  </h3>
                  <p className="text-gray-400 mb-4">
                    or click to browse
                  </p>
                  <p className="text-sm text-gray-500">
                    Supports PDF, DOCX, TXT, MD, Code files, and more (up to 100MB)
                  </p>
                </div>
              </div>
            </div>

            {/* Features Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-xl p-6 border border-gray-700 hover:border-[#FF6B47] transition-colors">
                <div className="w-12 h-12 bg-[rgba(255,107,71,0.2)] rounded-lg flex items-center justify-center mb-4">
                  <FileText className="w-6 h-6 text-[#FF6B47]" />
                </div>
                <h4 className="font-semibold mb-2">Smart Parsing</h4>
                <p className="text-sm text-gray-400">
                  Advanced extraction for 40+ file formats with layout preservation
                </p>
              </div>
              
              <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-xl p-6 border border-gray-700 hover:border-[#4ECDC4] transition-colors">
                <div className="w-12 h-12 bg-[rgba(78,205,196,0.2)] rounded-lg flex items-center justify-center mb-4">
                  <Zap className="w-6 h-6 text-[#4ECDC4]" />
                </div>
                <h4 className="font-semibold mb-2">Intelligent Chunking</h4>
                <p className="text-sm text-gray-400">
                  Context-aware splitting optimized for AI token limits
                </p>
              </div>
              
              <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-xl p-6 border border-gray-700 hover:border-[#FF6B47] transition-colors">
                <div className="w-12 h-12 bg-[rgba(255,107,71,0.2)] rounded-lg flex items-center justify-center mb-4">
                  <Download className="w-6 h-6 text-[#FF6B47]" />
                </div>
                <h4 className="font-semibold mb-2">Ready to Use</h4>
                <p className="text-sm text-gray-400">
                  Export as JSONL with metadata for immediate AI integration
                </p>
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
                    {processingResult.total_chunks || processingResult.chunks || 0}
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
                    {processingResult.average_chunk_size || 0}
                  </div>
                  <div className="text-sm text-gray-300">Avg Tokens/Chunk</div>
                </div>
              </div>

              {/* Preview Section */}
              {processingResult.preview && processingResult.preview.length > 0 && (
                <div className="bg-gray-800/50 rounded-xl p-6 mb-8 border border-gray-600">
                  <h4 className="font-semibold text-white mb-4 flex items-center">
                    <Eye className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                    Preview (First {Math.min(3, processingResult.preview.length)} Chunks)
                  </h4>
                  <div className="space-y-4">
                    {processingResult.preview.slice(0, 3).map((chunk, index) => (
                      <div key={index} className="bg-gray-900 rounded-lg border border-gray-700 p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-gray-400">Chunk {index + 1}</span>
                          <span className="text-xs text-[#4ECDC4]">
                            {typeof chunk === 'string' 
                              ? `~${Math.floor((processingResult.total_tokens || 0) / (processingResult.chunks || 1))} tokens`
                              : `${chunk.tokens} tokens`}
                          </span>
                        </div>
                        <div className="font-mono text-sm text-gray-300 leading-relaxed">
                          {typeof chunk === 'string' ? chunk : chunk.text}
                        </div>
                      </div>
                    ))}
                  </div>
                  {processingResult.preview.length > 3 && (
                    <p className="text-center text-sm text-gray-400 mt-4">
                      ... and {processingResult.preview.length - 3} more chunks
                    </p>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                {/* Download Full Results Button */}
                <button
                  onClick={downloadResults}
                  disabled={isDownloading}
                  className="inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-[#4ECDC4] to-[#3FBAB2] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(78,205,196,0.3)] transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isDownloading ? (
                    <>
                      <RefreshCw className="w-5 h-5 mr-2 animate-spin" />
                      Processing Full Export...
                    </>
                  ) : (
                    <>
                      <Download className="w-5 h-5 mr-2" />
                      Download Full Results
                    </>
                  )}
                </button>

                {/* Download Preview Button */}
                <button
                  onClick={downloadPreview}
                  className="inline-flex items-center justify-center px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-semibold transition-all duration-300"
                >
                  <Eye className="w-5 h-5 mr-2" />
                  Download Preview Only
                </button>

                {/* Process Another Button */}
                <button
                  onClick={resetApp}
                  className="inline-flex items-center justify-center px-6 py-3 bg-[rgba(255,255,255,0.1)] hover:bg-[rgba(255,255,255,0.15)] text-white rounded-xl font-semibold border border-gray-600 hover:border-gray-500 transition-all duration-300"
                >
                  <Upload className="w-5 h-5 mr-2" />
                  Process Another File
                </button>
              </div>

              {/* Processing Info */}
              {processingResult.processing_time && (
                <div className="text-center text-sm text-gray-400 mt-4">
                  Processed in {processingResult.processing_time.toFixed(2)} seconds
                </div>
              )}
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto py-6 text-center text-sm text-gray-400">
        <p>
          {APP_NAME} Cloud • Intelligent Document Processing
        </p>
      </footer>
    </div>
  );
};

export default WolfstitchApp;