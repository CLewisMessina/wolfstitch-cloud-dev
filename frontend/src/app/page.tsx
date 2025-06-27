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
  
  // TASK 1.1: Enhanced file input refs for folder selection
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  // Circular progress component (from production version)
  const CircularProgress = ({ percentage, size = 140 }: { percentage: number; size?: number }) => {
    const circumference = 2 * Math.PI * (size / 2 - 10);
    const strokeDasharray = circumference;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
      <div className="relative inline-flex items-center justify-center">
        <svg width={size} height={size} className="transform -rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={size / 2 - 10}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            className="text-gray-700"
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={size / 2 - 10}
            stroke="currentColor"
            strokeWidth="8"
            fill="transparent"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            className="text-[#4ECDC4] transition-all duration-300 ease-in-out"
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-white">{Math.round(percentage)}%</span>
        </div>
      </div>
    );
  };

  // File type icon helper
  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (['pdf'].includes(ext || '')) return <FileText className="w-5 h-5 text-red-400" />;
    if (['docx', 'doc'].includes(ext || '')) return <FileText className="w-5 h-5 text-blue-400" />;
    if (['txt', 'md'].includes(ext || '')) return <FileText className="w-5 h-5 text-gray-400" />;
    if (['py', 'js', 'ts', 'jsx', 'tsx'].includes(ext || '')) return <Code className="w-5 h-5 text-green-400" />;
    if (['json', 'csv', 'xlsx'].includes(ext || '')) return <File className="w-5 h-5 text-yellow-400" />;
    return <File className="w-5 h-5 text-gray-400" />;
  };

  // Process files function
  const processFiles = async (files: File[]) => {
    if (files.length === 0) return;

    setError(null);
    setProcessingStep('processing');
    setProgress(0);

    try {
      // Determine if we should use batch or single file processing
      const shouldUseBatch = isBatchEnabled() && files.length > 1;
      
      if (shouldUseBatch) {
        // TODO: Implement batch processing in Day 2
        console.log('Batch processing would be used for', files.length, 'files');
        // For now, fall back to single file processing
        await processSingleFile(files[0]);
      } else {
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
    formData.append('chunk_method', 'paragraph');
    formData.append('preserve_structure', 'true');

    // Update progress during upload
    setProgress(25);

    const response = await fetch(`${API_URL}/api/v1/quick-process`, {
      method: 'POST',
      body: formData,
    });

    setProgress(75);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Processing failed: ${errorText}`);
    }

    const result = await response.json() as ProcessingResult;
    setProcessingResult(result);
    setProgress(100);
    setProcessingStep('complete');
  };

  // Download function
  const downloadResults = async () => {
    if (!processingResult) return;

    try {
      const jsonlContent = (processingResult.chunks || processingResult.preview || [])
        .map(chunk => JSON.stringify({
          text: chunk.text,
          tokens: chunk.token_count || chunk.tokens || 0,
          chunk_index: chunk.chunk_index
        }))
        .join('\n');

      const blob = new Blob([jsonlContent], { type: 'application/jsonl' });
      const url = URL.createObjectURL(blob);

      const link = document.createElement('a');
      link.href = url;
      link.download = processingResult.filename?.replace(/\.[^/.]+$/, '') + '_processed.jsonl';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setProcessingStep('complete');
      setProgress(100);
      console.log('Download initiated successfully');
      
    } catch (error) {
      console.error('Download error:', error);
      setError(error instanceof Error ? error.message : 'Download failed');
      setProcessingStep('error');
    }
  };

  // TASK 1.1.2: Enhanced file selection handler with folder support
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
        console.log(`Processing folder: ${pathParts[0]} with ${files.length} files`);
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
        console.warn('File validation errors:', errors);
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

  // Enhanced drag and drop handler (placeholder for Task 1.2)
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

    // TODO: Task 1.2 - Implement full folder drop support with FileSystemEntry API
    console.log('Enhanced folder drop handler - to be implemented in Task 1.2');
    
    // Temporary fallback
    const files = Array.from(event.dataTransfer.files);
    setSelectedFiles(files);
    if (files.length > 0) {
      processFiles(files);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  // TASK 1.1.3: Enhanced click handlers for file vs folder selection
  const handleFileButtonClick = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFolderButtonClick = () => {
    if (folderInputRef.current) {
      folderInputRef.current.click();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      
      {/* Header - Enhanced from production */}
      <header className="border-b border-gray-700 bg-gray-900/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-[#FF6B47] to-[#4ECDC4] rounded-lg flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-white">{APP_NAME}</h1>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-sm text-gray-400">
                {ENVIRONMENT === 'production' ? 'Production Ready' : 'Development Mode'}
              </span>
              <div className="w-2 h-2 bg-[#4ECDC4] rounded-full animate-pulse"></div>
            </div>
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
                🚧 Day 1 Development - Batch: {isBatchEnabled() ? 'ON' : 'OFF'} | Folder Drop: {isFolderDropEnabled() ? 'ON' : 'OFF'}
              </p>
            </div>
          )}
        </section>

        {/* TASK 1.1: Enhanced Upload Section with folder selection support */}
        {processingStep === 'upload' && (
          <section className="space-y-6">
            <div 
              className="relative border-2 border-dashed border-[#FF6B47] bg-[rgba(255,107,71,0.1)] hover:bg-[rgba(255,107,71,0.15)] rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer shadow-lg shadow-[rgba(255,107,71,0.2)]"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
            >
              {/* TASK 1.1.1: Enhanced file input elements */}
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept={SUPPORTED_EXTENSIONS.map(ext => `.${ext}`).join(',')}
              />
              
              {/* TASK 1.1.1: Separate folder input with webkitdirectory */}
              {isFolderDropEnabled() && (
                <input
                  ref={folderInputRef}
                  type="file"
                  multiple
                  webkitdirectory
                  onChange={handleFileSelect}
                  className="hidden"
                />
              )}
              
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
                
                {/* TASK 1.1.3: Enhanced button section with file/folder options */}
                <div className="space-y-4">
                  {isFolderDropEnabled() ? (
                    // Show separate buttons for files and folders
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                      <button 
                        onClick={handleFileButtonClick}
                        className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105"
                      >
                        <Upload className="w-5 h-5 mr-2" />
                        Select Files
                      </button>
                      <button 
                        onClick={handleFolderButtonClick}
                        className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#4ECDC4] to-[#45B7B8] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(78,205,196,0.3)] transition-all duration-300 transform hover:scale-105"
                      >
                        <FolderOpen className="w-5 h-5 mr-2" />
                        Select Folder
                      </button>
                    </div>
                  ) : (
                    // Single button for files only
                    <button 
                      onClick={handleFileButtonClick}
                      className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105"
                    >
                      <Upload className="w-5 h-5 mr-2" />
                      Choose Files
                    </button>
                  )}
                  
                  <p className="text-sm text-gray-400">
                    or drag and drop your documents{isFolderDropEnabled() ? ' or folders' : ''} above
                  </p>
                </div>
              </div>
            </div>

            {/* File validation errors display */}
            {fileValidationErrors.length > 0 && (
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                <div className="flex items-start space-x-3">
                  <AlertCircle className="w-5 h-5 text-yellow-400 mt-0.5" />
                  <div>
                    <h4 className="text-yellow-300 font-semibold mb-2">Some files were skipped:</h4>
                    <ul className="text-sm text-yellow-200 space-y-1">
                      {fileValidationErrors.map((error, index) => (
                        <li key={index} className="truncate">{error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </section>
        )}

        {/* Processing Section */}
        {processingStep === 'processing' && (
          <section className="text-center space-y-8 py-16">
            <CircularProgress percentage={progress} />
            <div className="space-y-2">
              <h3 className="text-2xl font-bold text-white">Processing Document{selectedFiles.length > 1 ? 's' : ''}</h3>
              <p className="text-gray-300">
                {isProcessingFolder ? `Processing ${selectedFiles.length} files from "${folderName}" folder...` : 
                 selectedFiles.length > 1 ? `Processing ${selectedFiles.length} files...` : 
                 'Analyzing content and generating chunks...'}
              </p>
            </div>
          </section>
        )}

        {/* Results Section */}
        {processingStep === 'complete' && processingResult && (
          <section className="space-y-8">
            <div className="text-center space-y-4">
              <div className="mx-auto w-16 h-16 bg-green-500 rounded-full flex items-center justify-center">
                <CheckCircle className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white">Processing Complete!</h3>
              <p className="text-gray-300">
                {isProcessingFolder ? `Successfully processed ${selectedFiles.length} files from "${folderName}" folder` : 
                 selectedFiles.length > 1 ? `Successfully processed ${selectedFiles.length} files` :
                 'Your document has been processed and is ready for download'}
              </p>
            </div>

            {/* Results Summary */}
            <div className="bg-gray-800/50 rounded-2xl p-8 border border-gray-700">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
                <div className="text-center">
                  <div className="text-3xl font-bold text-[#4ECDC4]">
                    {processingResult.total_chunks || (processingResult.chunks?.length || processingResult.preview?.length || 0)}
                  </div>
                  <div className="text-gray-400">Chunks</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-[#FF6B47]">
                    {processingResult.total_tokens || 'N/A'}
                  </div>
                  <div className="text-gray-400">Tokens</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-400">
                    {Math.round(processingResult.average_chunk_size || 0)}
                  </div>
                  <div className="text-gray-400">Avg Size</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-400">
                    {processingResult.processing_time ? `${processingResult.processing_time.toFixed(1)}s` : 'N/A'}
                  </div>
                  <div className="text-gray-400">Time</div>
                </div>
              </div>

              <div className="space-y-4">
                <button
                  onClick={downloadResults}
                  className="w-full inline-flex items-center justify-center px-6 py-4 bg-gradient-to-r from-[#4ECDC4] to-[#45B7B8] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(78,205,196,0.3)] transition-all duration-300 transform hover:scale-105"
                >
                  <Download className="w-5 h-5 mr-2" />
                  Download JSONL Results
                </button>
                
                <button
                  onClick={() => {
                    setSelectedFiles([]);
                    setProcessingResult(null);
                    setProcessingStep('upload');
                    setProgress(0);
                    setError(null);
                    setIsProcessingFolder(false);
                    setFolderName('');
                    setFileValidationErrors([]);
                  }}
                  className="w-full text-gray-400 hover:text-white transition-colors"
                >
                  Process Another Document
                </button>
              </div>
            </div>
          </section>
        )}

        {/* Error Section */}
        {processingStep === 'error' && (
          <section className="text-center space-y-8 py-16">
            <div className="mx-auto w-16 h-16 bg-red-500 rounded-full flex items-center justify-center">
              <AlertCircle className="w-8 h-8 text-white" />
            </div>
            <div className="space-y-2">
              <h3 className="text-2xl font-bold text-white">Processing Failed</h3>
              <p className="text-gray-300 max-w-md mx-auto">{error}</p>
            </div>
            <button
              onClick={() => {
                setProcessingStep('upload');
                setError(null);
                setProgress(0);
              }}
              className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300"
            >
              Try Again
            </button>
          </section>
        )}

        {/* Selected Files Display */}
        {selectedFiles.length > 0 && processingStep !== 'processing' && (
          <section className="space-y-4">
            <div className="bg-gray-800/50 rounded-2xl p-6 border border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">
                  {isProcessingFolder ? `Files from "${folderName}" folder` : 'Selected Files'}
                </h3>
                <button
                  onClick={() => setShowFileDetails(!showFileDetails)}
                  className="flex items-center space-x-2 text-gray-400 hover:text-white transition-colors"
                >
                  <span>{selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''}</span>
                  <ChevronDown className={`w-4 h-4 transition-transform ${showFileDetails ? 'rotate-180' : ''}`} />
                </button>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="text-2xl font-bold text-[#4ECDC4]">
                    {selectedFiles.length}
                  </div>
                  <div>
                    <div className="font-medium text-white">
                      {formatFileSize(selectedFiles.reduce((total, file) => total + file.size, 0))}
                    </div>
                    <div className="text-sm text-gray-400">Total size</div>
                  </div>
                </div>
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
}processingStep === 'complete' ? 'bg-green-400' : 'bg-gray-400'}`}></div>
                  <span className="text-gray-300">
                    {processingStep === 'complete' ? 'Processed' : 'Ready'}
                  </span>
                </div>
              </div>
              
              {showFileDetails && (
                <div className="space-y-2 max-h-64 overflow-y-auto mt-4">
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
                  <div className={`w-3 h-3 rounded-full ${