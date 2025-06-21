// frontend/src/app/page.tsx
// Enhanced main page component with robust error handling and mobile support - Fixed TypeScript Issues

'use client';

import React, { useState, useRef, useCallback } from 'react';
import { 
  Upload, 
  File, 
  Code, 
  FileText, 
  Download, 
  CheckCircle, 
  Eye,
  Zap,
  Activity,
  AlertCircle,
  RefreshCw,
  Wifi,
  WifiOff
} from 'lucide-react';

// Import our enhanced utilities
import { ProcessingResult, ProcessingError, UploadState } from '@/types/types';
import { validateFile, validateFiles, detectDevice } from '@/utils/fileValidator';
import { processFile, checkApiHealth } from '@/utils/apiClient';
import ErrorBoundary from '@/components/ErrorBoundary';

const WolfstitchApp = () => {
  // Enhanced state management
  const [uploadState, setUploadState] = useState<UploadState>({
    step: 'upload',
    progress: 0,
    selectedFiles: [],
    result: null,
    error: null,
    showFileDetails: false
  });
  
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [deviceInfo] = useState(() => detectDevice());
  
  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Configuration
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.wolfstitch.dev';
  const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || 'Wolfstitch';
  const ENVIRONMENT = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';

  // =============================================================================
  // API STATUS MONITORING
  // =============================================================================

  React.useEffect(() => {
    const checkStatus = async () => {
      try {
        const isOnline = await checkApiHealth();
        setApiStatus(isOnline ? 'online' : 'offline');
      } catch {
        setApiStatus('offline');
      }
    };
    
    checkStatus();
    
    // Check every 30 seconds
    const interval = setInterval(checkStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  // =============================================================================
  // FILE PROCESSING
  // =============================================================================

  const processFiles = useCallback(async (files: File[]) => {
    if (files.length === 0) return;

    console.log('Starting file processing for', files.length, 'files');

    setUploadState(prev => ({
      ...prev,
      error: null,
      step: 'processing',
      progress: 0
    }));

    try {
      // Validate files first
      const validation = validateFiles(files);
      
      if (validation.errors.length > 0) {
        throw new Error(`File validation failed: ${validation.errors.join('; ')}`);
      }
      
      if (validation.warnings.length > 0) {
        console.warn('File validation warnings:', validation.warnings);
      }
      
      const validFiles = validation.validFiles;
      if (validFiles.length === 0) {
        throw new Error('No valid files to process');
      }

      // Process the first valid file
      const fileToProcess = validFiles[0];
      console.log('Processing file:', fileToProcess.name);

      const result = await processFile(fileToProcess, {
        tokenizer: 'word-estimate',
        maxTokens: 1024,
        onProgress: (progress) => {
          setUploadState(prev => ({ ...prev, progress }));
        }
      });

      console.log('Processing completed successfully:', result);

      setUploadState(prev => ({
        ...prev,
        progress: 100,
        result,
        step: 'completed'
      }));

    } catch (error) {
      console.error('Processing error:', error);
      
      let errorMessage = 'Unknown error occurred';
      
      if (error && typeof error === 'object' && 'message' in error) {
        errorMessage = (error as ProcessingError).message;
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }

      setUploadState(prev => ({
        ...prev,
        error: errorMessage,
        step: 'error',
        progress: 0
      }));
    }
  }, []);

  // =============================================================================
  // FILE DOWNLOAD
  // =============================================================================

  const downloadResults = useCallback(() => {
    const { result } = uploadState;
    if (!result) return;

    try {
      // Create JSONL content from normalized preview data
      const jsonlContent = result.previewChunks.map((chunk) => 
        JSON.stringify({
          text: chunk.text,
          chunk_id: chunk.id,
          tokens: chunk.tokens,
          metadata: {
            filename: result.filename,
            processed_at: result.metadata.processed_at,
            ...chunk.metadata
          }
        })
      ).join('\n');

      // Create and download file
      const blob = new Blob([jsonlContent], { type: 'application/jsonl' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${result.filename.replace(/\.[^/.]+$/, '')}_processed.jsonl`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      
      console.log('Download initiated:', link.download);
    } catch (error) {
      console.error('Download failed:', error);
      setUploadState(prev => ({
        ...prev,
        error: 'Failed to generate download file. Please try processing again.'
      }));
    }
  }, [uploadState.result]);

  // =============================================================================
  // FILE SELECTION HANDLERS
  // =============================================================================

  const handleFileSelect = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setUploadState(prev => ({ ...prev, selectedFiles: files }));
    
    if (files.length > 0) {
      processFiles(files);
    }
  }, [processFiles]);

  const handleDrop = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const files = Array.from(event.dataTransfer.files);
    setUploadState(prev => ({ ...prev, selectedFiles: files }));
    
    if (files.length > 0) {
      processFiles(files);
    }
  }, [processFiles]);

  const handleDragOver = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  }, []);

  // =============================================================================
  // UI ACTIONS
  // =============================================================================

  const resetApp = useCallback(() => {
    setUploadState({
      step: 'upload',
      progress: 0,
      selectedFiles: [],
      result: null,
      error: null,
      showFileDetails: false
    });
    
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, []);

  // =============================================================================
  // UTILITY FUNCTIONS
  // =============================================================================

  const getFileIcon = useCallback((fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    switch (extension) {
      case 'pdf': return <FileText className="w-8 h-8 text-red-400" />;
      case 'docx':
      case 'doc': return <FileText className="w-8 h-8 text-blue-400" />;
      case 'txt':
      case 'md': return <FileText className="w-8 h-8 text-gray-400" />;
      case 'py':
      case 'js':
      case 'ts': return <Code className="w-8 h-8 text-green-400" />;
      default: return <File className="w-8 h-8 text-gray-400" />;
    }
  }, []);

  // =============================================================================
  // RENDER FUNCTIONS
  // =============================================================================

  const renderApiStatus = () => (
    <div className="fixed top-4 right-4 z-50">
      <div className={`flex items-center px-3 py-1 rounded-full text-sm ${
        apiStatus === 'online' 
          ? 'bg-green-500/20 text-green-300 border border-green-500/30' 
          : apiStatus === 'offline'
          ? 'bg-red-500/20 text-red-300 border border-red-500/30'
          : 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
      }`}>
        {apiStatus === 'online' && <Wifi className="w-4 h-4 mr-1" />}
        {apiStatus === 'offline' && <WifiOff className="w-4 h-4 mr-1" />}
        {apiStatus === 'checking' && <Activity className="w-4 h-4 mr-1 animate-spin" />}
        <span className="capitalize">{apiStatus}</span>
      </div>
    </div>
  );

  const renderDeviceInfo = () => (
    deviceInfo.isMobile && (
      <div className="text-center mb-4">
        <p className="text-sm text-gray-400">
          📱 Mobile optimized • Max file size: {Math.round(deviceInfo.maxFileSize / (1024 * 1024))}MB
        </p>
      </div>
    )
  );

  const renderUploadInterface = () => (
    <div className="space-y-8">
      {renderDeviceInfo()}
      
      <div
        className="relative border-2 border-dashed border-gray-600 rounded-3xl p-12 text-center hover:border-[#4ECDC4] transition-all duration-300 cursor-pointer bg-[rgba(255,255,255,0.02)] backdrop-blur-sm hover:bg-[rgba(255,255,255,0.05)] shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] hover:shadow-[0_20px_40px_rgba(78,205,196,0.2)]"
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
              Maximum file size: {Math.round(deviceInfo.maxFileSize / (1024 * 1024))}MB • 40+ supported formats
            </p>
          </div>
        </div>
      </div>
    </div>
  );

  const renderProcessingInterface = () => (
    <div className="space-y-8">
      <div className="text-center space-y-4">
        <div className="mx-auto w-20 h-20 bg-gradient-to-br from-[#4ECDC4] to-[#44B8B5] rounded-full flex items-center justify-center shadow-xl">
          <Zap className="w-10 h-10 text-white animate-pulse" />
        </div>
        <div>
          <h3 className="text-2xl font-bold text-white mb-2">Processing Your File</h3>
          <p className="text-gray-300">
            Extracting text and creating AI-ready chunks...
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="bg-gray-800 rounded-full h-3 overflow-hidden shadow-inner">
        <div 
          className="h-full bg-gradient-to-r from-[#4ECDC4] to-[#44B8B5] transition-all duration-300 ease-out rounded-full shadow-lg"
          style={{ width: `${uploadState.progress}%` }}
        />
      </div>
      
      <div className="text-center">
        <p className="text-2xl font-bold text-[#4ECDC4] mb-1">{Math.round(uploadState.progress)}%</p>
        <p className="text-sm text-gray-400">
          {uploadState.progress < 30 ? 'Analyzing file structure...' :
           uploadState.progress < 60 ? 'Extracting text content...' :
           uploadState.progress < 90 ? 'Creating chunks and counting tokens...' :
           'Finalizing results...'}
        </p>
      </div>
    </div>
  );

  const renderErrorInterface = () => (
    <div className="space-y-8">
      <div className="text-center space-y-4">
        <div className="mx-auto w-20 h-20 bg-gradient-to-br from-red-500 to-red-600 rounded-full flex items-center justify-center shadow-xl">
          <AlertCircle className="w-10 h-10 text-white" />
        </div>
        <div>
          <h3 className="text-2xl font-bold text-white mb-2">Processing Failed</h3>
          <p className="text-gray-300">
            We encountered an issue while processing your file
          </p>
        </div>
      </div>

      {/* Error Details */}
      <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-6">
        <p className="text-red-300 text-center">{uploadState.error}</p>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-4 justify-center">
        <button
          onClick={resetApp}
          className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#4ECDC4] to-[#44B8B5] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(78,205,196,0.3)] transition-all duration-300 transform hover:scale-105"
        >
          <RefreshCw className="w-5 h-5 mr-2" />
          Try Again
        </button>
        
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-gray-600 to-gray-700 text-white rounded-xl font-semibold hover:shadow-lg transition-all duration-300 transform hover:scale-105"
        >
          <RefreshCw className="w-5 h-5 mr-2" />
          Reload Page
        </button>
      </div>
    </div>
  );

  const renderCompletedInterface = () => {
    const { result } = uploadState;
    if (!result) return null;

    return (
      <div className="space-y-8">
        <div className="text-center space-y-4">
          <div className="mx-auto w-20 h-20 bg-gradient-to-br from-green-500 to-green-600 rounded-full flex items-center justify-center shadow-xl">
            <CheckCircle className="w-10 h-10 text-white" />
          </div>
          <div>
            <h3 className="text-2xl font-bold text-white mb-2">
              Processing Complete!
            </h3>
            <p className="text-gray-300">
              Your document has been successfully processed and chunked
            </p>
          </div>
        </div>

        {/* Results Summary */}
        <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div className="text-center">
              <div className="text-3xl font-bold text-[#FF6B47] mb-1">
                {result.chunks}
              </div>
              <div className="text-sm text-gray-300">Chunks Created</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-[#4ECDC4] mb-1">
                {result.total_tokens.toLocaleString()}
              </div>
              <div className="text-sm text-gray-300">Total Tokens</div>
            </div>
            <div className="text-center">
              <div className="text-3xl font-bold text-white mb-1">
                {result.average_tokens_per_chunk}
              </div>
              <div className="text-sm text-gray-300">Avg Tokens/Chunk</div>
            </div>
          </div>

          {/* Preview */}
          {result.preview && result.preview.length > 0 && (
            <div className="bg-gray-800/50 rounded-xl p-6 mb-8 border border-gray-600">
              <h4 className="font-semibold text-white mb-4 flex items-center">
                <Eye className="w-5 h-5 mr-2 text-[#4ECDC4]" />
                Preview (First Chunks)
              </h4>
              <div className="space-y-4">
                {result.preview.slice(0, 3).map((chunk, index) => (
                  <div key={index} className="bg-gray-900 rounded-lg border border-gray-700 p-4">
                    <div className="font-mono text-sm text-gray-300 leading-relaxed">
                      {chunk}
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                      Chunk {index + 1}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={downloadResults}
              className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-[#4ECDC4] to-[#44B8B5] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(78,205,196,0.3)] transition-all duration-300 transform hover:scale-105"
            >
              <Download className="w-5 h-5 mr-2" />
              Download JSONL
            </button>
            
            <button
              onClick={resetApp}
              className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105"
            >
              <Upload className="w-5 h-5 mr-2" />
              Process Another File
            </button>
          </div>
        </div>
      </div>
    );
  };

  // =============================================================================
  // MAIN RENDER
  // =============================================================================

  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error('App Error Boundary caught error:', error, errorInfo);
      }}
    >
      <div className="min-h-screen bg-gradient-to-br from-[#1a1b2e] via-[#16213e] to-[#0f172a] relative overflow-hidden">
        {/* Background Effects */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_40%,rgba(255,107,71,0.1),transparent_50%)] pointer-events-none" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_60%,rgba(78,205,196,0.1),transparent_50%)] pointer-events-none" />
        
        {renderApiStatus()}
        
        <div className="relative z-10 container mx-auto px-4 py-8">
          {/* Header */}
          <div className="text-center mb-16">
            <h1 className="text-6xl font-bold bg-gradient-to-r from-[#FF6B47] via-[#4ECDC4] to-[#FF6B47] bg-clip-text text-transparent mb-4">
              {APP_NAME}
            </h1>
            <p className="text-xl text-gray-300 max-w-2xl mx-auto leading-relaxed">
              Transform your documents into AI-training datasets. Upload any file, get back perfectly chunked, tokenized data ready for machine learning.
            </p>
            {uploadState.result?.enhanced && (
              <div className="mt-4 inline-flex items-center px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-sm border border-green-500/30">
                <Zap className="w-4 h-4 mr-1" />
                Enhanced Processing
              </div>
            )}
          </div>

          {/* Main Content */}
          <div className="max-w-4xl mx-auto">
            {uploadState.step === 'upload' && renderUploadInterface()}
            {uploadState.step === 'processing' && renderProcessingInterface()}
            {uploadState.step === 'error' && renderErrorInterface()}
            {uploadState.step === 'completed' && renderCompletedInterface()}
          </div>

          {/* Footer */}
          <div className="text-center mt-16 text-gray-400 text-sm">
            <p>
              Made with ❤️ by Chris Lewis-Messina • 
              {deviceInfo.isMobile ? ' Mobile Optimized' : ' Desktop'} • 
              API: {apiStatus}
            </p>
            {ENVIRONMENT === 'development' && (
              <p className="mt-2 text-xs">
                Development Mode • API: {API_BASE_URL}
              </p>
            )}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default WolfstitchApp;