//  src\app\page.tsx
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
  FolderOpen
} from 'lucide-react';

// Import feature flags and file utilities
import { isBatchEnabled, isFolderDropEnabled } from '@/lib/feature-flags';
import { 
  traverseFileTree, 
  processFileList, 
  validateFile, 
  formatFileSize,
  SUPPORTED_EXTENSIONS 
} from '@/lib/file-utils';

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
console.log('Batch enabled:', isBatchEnabled());
console.log('Folder drop enabled:', isFolderDropEnabled());

export default function FileProcessor() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [processingStep, setProcessingStep] = useState<ProcessingStep>('upload');
  const [progress, setProgress] = useState(0);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showFileDetails, setShowFileDetails] = useState(false);
  const [isProcessingFolder, setIsProcessingFolder] = useState(false);
  const [folderName, setFolderName] = useState<string>('');
  const [fileValidationErrors, setFileValidationErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Circular progress component (from production version)
  const CircularProgress = ({ percentage, size = 140 }: { percentage: number; size?: number }) => {
    const radius = (size - 12) / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div className="relative inline-flex items-center justify-center">
        <svg width={size} height={size} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="rgba(255, 255, 255, 0.1)"
            strokeWidth="6"
            fill="transparent"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            stroke="url(#gradient)"
            strokeWidth="6"
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-500 ease-in-out"
          />
          <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#FF6B47" />
              <stop offset="100%" stopColor="#4ECDC4" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">{Math.round(percentage)}%</span>
        </div>
      </div>
    );
  };

  // Enhanced file processing function
  const processFiles = async (files: File[]) => {
    if (!files || files.length === 0) return;
    
    setProcessingStep('processing');
    setProgress(0);
    setError(null);
    setProcessingResult(null);

    try {
      // Handle batch processing if enabled and multiple files
      if (isBatchEnabled() && files.length > 1) {
        await processBatch(files);
      } else {
        // Single file processing (existing logic)
        await processSingleFile(files[0]);
      }
    } catch (error) {
      console.error('Processing error:', error);
      setError(error instanceof Error ? error.message : 'Processing failed');
      setProcessingStep('error');
    }
  };

  // Single file processing (existing logic)
  const processSingleFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tokenizer', 'gpt-4');
    formData.append('max_tokens', '1000');
    formData.append('overlap_tokens', '100');

    // Progress simulation for single file
    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(prev + Math.random() * 15, 85));
    }, 500);

    try {
      const response = await fetch(`${API_URL}/api/v1/quick-process`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const result: ProcessingResult = await response.json();
      setProcessingResult(result);
      setProcessingStep('complete');
      setProgress(100);
      
    } catch (error) {
      clearInterval(progressInterval);
      throw error;
    }
  };

  // New batch processing function
  const processBatch = async (files: File[]) => {
    const formData = new FormData();
    
    // Add all files to form data
    files.forEach((file, index) => {
      formData.append(`files`, file);
    });
    
    formData.append('tokenizer', 'gpt-4');
    formData.append('max_tokens', '1000');
    formData.append('overlap_tokens', '100');

    // Progress simulation for batch
    const progressInterval = setInterval(() => {
      setProgress(prev => Math.min(prev + Math.random() * 10, 85));
    }, 1000);

    try {
      const response = await fetch(`${API_URL}/api/v1/batch-process`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Batch processing failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const result: ProcessingResult = await response.json();
      setProcessingResult(result);
      setProcessingStep('complete');
      setProgress(100);
      
    } catch (error) {
      clearInterval(progressInterval);
      throw error;
    }
  };

  // Download results
  const downloadResults = async () => {
    if (!processingResult) return;

    try {
      setError(null);
      
      if (processingResult.job_id && isBatchEnabled()) {
        // Download batch results
        const response = await fetch(`${API_URL}/api/v1/batch/${processingResult.job_id}/download`);
        
        if (!response.ok) {
          throw new Error(`Download failed: ${response.status} ${response.statusText}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `batch_${processingResult.job_id}_processed.jsonl`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
      } else {
        // Single file download (existing logic)
        const chunks = processingResult.chunks || processingResult.preview || [];
        const jsonlContent = chunks.map(chunk => JSON.stringify({
          text: chunk.text,
          tokens: chunk.token_count || chunk.tokens || 0,
          metadata: {
            chunk_index: chunk.chunk_index,
            filename: processingResult.filename,
            processing_time: processingResult.processing_time,
          }
        })).join('\n');

        const blob = new Blob([jsonlContent], { type: 'application/jsonl' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = processingResult.filename.replace(/\.[^/.]+$/, '') + '_processed.jsonl';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      
      setProcessingStep('complete');
      setProgress(100);
      console.log('Download initiated successfully');
      
    } catch (error) {
      console.error('Download error:', error);
      setError(error instanceof Error ? error.message : 'Download failed');
      setProcessingStep('error');
    }
  };

  // Enhanced file selection handler with folder support
  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const input = event.target;
    const files = input.files;
    
    if (!files || files.length === 0) return;

    try {
      setFileValidationErrors([]);
      
      // Check if this is a folder selection
      const isFolder = input.webkitdirectory;
      setIsProcessingFolder(isFolder);
      
      if (isFolder) {
        // Extract folder name from first file path
        const firstFile = files[0];
        const pathParts = firstFile.webkitRelativePath?.split('/') || [];
        setFolderName(pathParts[0] || 'Unknown Folder');
      }
      
      // Process and validate files
      const processedFiles = await processFileList(files);
      
      // Validate each file
      const validFiles: File[] = [];
      const errors: string[] = [];
      
      for (const file of processedFiles) {
        const validation = validateFile(file);
        if (validation.isValid) {
          validFiles.push(file);
        } else {
          errors.push(`${file.name}: ${validation.error}`);
        }
      }
      
      if (errors.length > 0) {
        setFileValidationErrors(errors);
      }
      
      if (validFiles.length > 0) {
        setSelectedFiles(validFiles);
        console.log(`Selected ${validFiles.length} valid files${isFolder ? ' from folder' : ''}`);
        processFiles(validFiles);
      } else {
        setError('No valid files selected. Please check file formats and sizes.');
      }
      
    } catch (error) {
      console.error('File selection error:', error);
      setError(error instanceof Error ? error.message : 'Failed to process selected files');
    }
  };

  // Enhanced drag and drop handler with folder support
  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    
    if (!isFolderDropEnabled()) {
      // Fallback to simple file handling
      const files = Array.from(event.dataTransfer.files);
      setSelectedFiles(files);
      if (files.length > 0) {
        processFiles(files);
      }
      return;
    }

    try {
      setFileValidationErrors([]);
      const items = Array.from(event.dataTransfer.items);
      
      // Check if we have directory entries
      const hasDirectories = items.some(item => 
        item.webkitGetAsEntry && item.webkitGetAsEntry()?.isDirectory
      );
      
      setIsProcessingFolder(hasDirectories);
      
      if (hasDirectories) {
        // Process folders using FileSystemEntry API
        const allFiles: File[] = [];
        
        for (const item of items) {
          if (item.webkitGetAsEntry) {
            const entry = item.webkitGetAsEntry();
            if (entry) {
              const files = await traverseFileTree(entry);
              allFiles.push(...files);
            }
          }
        }
        
        if (allFiles.length > 0) {
          // Extract folder name from first file
          const firstFile = allFiles[0];
          const pathParts = firstFile.webkitRelativePath?.split('/') || [];
          setFolderName(pathParts[0] || 'Dropped Folder');
          
          // Validate files
          const validFiles: File[] = [];
          const errors: string[] = [];
          
          for (const file of allFiles) {
            const validation = validateFile(file);
            if (validation.isValid) {
              validFiles.push(file);
            } else {
              errors.push(`${file.name}: ${validation.error}`);
            }
          }
          
          if (errors.length > 0) {
            setFileValidationErrors(errors);
          }
          
          if (validFiles.length > 0) {
            setSelectedFiles(validFiles);
            processFiles(validFiles);
          } else {
            setError('No valid files found in dropped folders.');
          }
        }
      } else {
        // Handle individual files
        const files = Array.from(event.dataTransfer.files);
        setSelectedFiles(files);
        if (files.length > 0) {
          processFiles(files);
        }
      }
      
    } catch (error) {
      console.error('Drop handling error:', error);
      setError(error instanceof Error ? error.message : 'Failed to process dropped files');
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
    setIsProcessingFolder(false);
    setFolderName('');
    setFileValidationErrors([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
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
            Professional-grade document processing with intelligent chunking, 40+ file formats, and {isBatchEnabled() ? 'batch processing for entire folders' : 'beautiful export options'}
          </p>
          {ENVIRONMENT === 'development' && (
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 mx-auto max-w-md">
              <p className="text-yellow-300 text-sm">
                🚧 Development Mode - Batch: {isBatchEnabled() ? 'ON' : 'OFF'} | Folder Drop: {isFolderDropEnabled() ? 'ON' : 'OFF'}
              </p>
            </div>
          )}
        </section>

        {/* Upload Section - Enhanced styling with folder support */}
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
                {...(isFolderDropEnabled() ? { webkitdirectory: true } : {})}
                onChange={handleFileSelect}
                className="hidden"
                accept={SUPPORTED_EXTENSIONS.map(ext => `.${ext}`).join(',')}
              />
              <div className="space-y-6">
                <div className="mx-auto w-20 h-20 bg-gradient-to-br from-[#FF6B47] to-[#E85555] rounded-full flex items-center justify-center shadow-xl">
                  {isFolderDropEnabled() ? (
                    <FolderOpen className="w-10 h-10 text-white" />
                  ) : (
                    <Upload className="w-10 h-10 text-white" />
                  )}
                </div>
                <div>
                  <p className="text-2xl font-bold text-white mb-2">
                    {isFolderDropEnabled() ? 'Drop files or folders here' : 'Drop files here or click to browse'}
                  </p>
                  <p className="text-gray-300">
                    PDF, DOCX, TXT, code files, presentations{isFolderDropEnabled() ? ', or entire folders' : ''}
                  </p>
                  {isBatchEnabled() && (
                    <p className="text-sm text-[#4ECDC4] mt-2">
                      ✨ Batch processing enabled - process multiple files at once
                    </p>
                  )}
                </div>
                <div className="space-y-4">
                  <button className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105">
                    {isFolderDropEnabled() ? (
                      <>
                        <FolderOpen className="w-5 h-5 mr-2" />
                        Choose Files or Folder
                      </>
                    ) : (
                      <>
                        <Upload className="w-5 h-5 mr-2" />
                        Choose Files
                      </>
                    )}
                  </button>
                  <p className="text-sm text-gray-400">
                    or drag and drop your documents{isFolderDropEnabled() ? ' or folders' : ''} here
                  </p>
                  {isBatchEnabled() && (
                    <p className="text-xs text-gray-500">
                      Max {100} files per batch, {100}MB per file
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Validation Errors Display */}
            {fileValidationErrors.length > 0 && (
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                <div className="flex items-center mb-2">
                  <AlertCircle className="w-5 h-5 text-yellow-400 mr-2" />
                  <h4 className="text-yellow-300 font-medium">File Validation Warnings</h4>
                </div>
                <div className="text-sm text-yellow-200 space-y-1">
                  {fileValidationErrors.map((error, index) => (
                    <p key={index}>• {error}</p>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {/* Processing Section */}
        {processingStep === 'processing' && (
          <section className="text-center space-y-8">
            <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-8">
              <CircularProgress percentage={progress} />
              <div className="mt-6 space-y-2">
                <h3 className="text-2xl font-bold text-white">
                  {isProcessingFolder ? `Processing ${folderName}` : 'Processing Document'}
                </h3>
                <p className="text-gray-300">
                  {selectedFiles.length > 1 
                    ? `Processing ${selectedFiles.length} files...` 
                    : 'Analyzing content and generating chunks...'
                  }
                </p>
                <div className="w-full bg-gray-700 rounded-full h-2 max-w-md mx-auto">
                  <div 
                    className="bg-gradient-to-r from-[#FF6B47] to-[#4ECDC4] h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Error Section */}
        {processingStep === 'error' && (
          <section className="text-center space-y-6">
            <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-8">
              <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
              <h3 className="text-2xl font-bold text-white mb-2">Processing Failed</h3>
              <p className="text-red-300 mb-6">{error}</p>
              <button
                onClick={resetApp}
                className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105"
              >
                <Upload className="w-5 h-5 mr-2" />
                Try Again
              </button>
            </div>
          </section>
        )}

        {/* Results Section */}
        {processingStep === 'complete' && processingResult && (
          <section className="space-y-6">
            <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-8 text-center">
              <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
              <h3 className="text-2xl font-bold text-white mb-2">
                {selectedFiles.length > 1 ? 'Batch Processing Complete!' : 'Processing Complete!'}
              </h3>
              
              {/* Enhanced results display for batch processing */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 my-8">
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-600">
                  <div className="text-2xl font-bold text-[#4ECDC4]">
                    {processingResult.total_chunks || (processingResult.chunks?.length) || 0}
                  </div>
                  <div className="text-gray-300 text-sm">Total Chunks</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-600">
                  <div className="text-2xl font-bold text-[#FF6B47]">
                    {processingResult.total_tokens || 0}
                  </div>
                  <div className="text-gray-300 text-sm">Total Tokens</div>
                </div>
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-600">
                  <div className="text-2xl font-bold text-green-400">
                    {selectedFiles.length}
                  </div>
                  <div className="text-gray-300 text-sm">{selectedFiles.length === 1 ? 'File' : 'Files'} Processed</div>
                </div>
              </div>

              {/* Preview section for single files */}
              {!isBatchEnabled() && processingResult.chunks && processingResult.chunks.length > 0 && (
                <div className="text-left">
                  <h4 className="text-lg font-semibold text-white mb-4 flex items-center">
                    <Eye className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                    Content Preview
                  </h4>
                  <div className="space-y-4 max-h-64 overflow-y-auto">
                    {processingResult.chunks.slice(0, 3).map((chunk, index) => (
                      <div key={index} className="bg-gray-800/50 rounded-lg p-4 border border-gray-600">
                        <div className="text-gray-300 text-sm mb-2 line-clamp-3">
                          {chunk.text.substring(0, 200)}...
                        </div>
                        <div className="flex justify-between text-xs text-gray-400">
                          <span>Chunk {chunk.chunk_index ? chunk.chunk_index + 1 : index + 1}</span>
                          <span>{chunk.token_count || chunk.tokens || 0} tokens</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 justify-center mt-8">
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
                  {isProcessingFolder ? (
                    <>
                      <FolderOpen className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                      {folderName} ({selectedFiles.length} files)
                    </>
                  ) : (
                    <>
                      <Folder className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                      Selected Files ({selectedFiles.length})
                    </>
                  )}
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
              
              {/* File list summary */}
              <div className="mb-4 p-3 bg-gray-800/50 rounded-lg border border-gray-600">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Total Files:</span>
                    <span className="text-white ml-2 font-medium">{selectedFiles.length}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Total Size:</span>
                    <span className="text-white ml-2 font-medium">
                      {formatFileSize(selectedFiles.reduce((sum, file) => sum + file.size, 0))}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">Avg Size:</span>
                    <span className="text-white ml-2 font-medium">
                      {formatFileSize(selectedFiles.reduce((sum, file) => sum + file.size, 0) / selectedFiles.length)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-400">Status:</span>
                    <span className="text-green-400 ml-2 font-medium">
                      {processingStep === 'complete' ? 'Processed' : 'Ready'}
                    </span>
                  </div>
                </div>
              </div>
              
              {showFileDetails && (
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {selectedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-600 hover:bg-gray-800/70 transition-colors">
                      <div className="flex items-center space-x-3 flex-1 min-w-0">
                        {getFileIcon(file.name)}
                        <div className="flex-1 min-w-0">
                          <span className="font-medium text-white block truncate">{file.name}</span>
                          {isProcessingFolder && file.webkitRelativePath && (
                            <span className="text-xs text-gray-400 block truncate">
                              {file.webkitRelativePath}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-3 text-sm text-gray-400">
                        <span>{formatFileSize(file.size)}</span>
                        {processingStep === 'complete' && (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {/* Feature Status Footer (Development Only) */}
        {ENVIRONMENT === 'development' && (
          <footer className="text-center py-8 border-t border-gray-700 mt-16">
            <div className="space-y-2">
              <h4 className="text-lg font-semibold text-white">Development Feature Status</h4>
              <div className="flex flex-wrap justify-center gap-4 text-sm">
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${isBatchEnabled() ? 'bg-green-400' : 'bg-red-400'}`}></div>
                  <span className="text-gray-300">Batch Processing</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className={`w-3 h-3 rounded-full ${isFolderDropEnabled() ? 'bg-green-400' : 'bg-red-400'}`}></div>
                  <span className="text-gray-300">Folder Drop</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 rounded-full bg-green-400"></div>
                  <span className="text-gray-300">Single File Processing</span>
                </div>
              </div>
              <p className="text-xs text-gray-500 max-w-md mx-auto">
                Feature flags control which capabilities are enabled. 
                Folder support requires modern browser with FileSystemEntry API.
              </p>
            </div>
          </footer>
        )}
      </div>
    </div>
  );
}