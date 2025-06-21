// frontend/src/types/types.ts
// Enhanced type definitions for robust API response handling

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

/**
 * Enhanced API chunk format (from enhanced processing)
 */
export interface EnhancedChunk {
  text: string;
  token_count: number;
  chunk_index: number;
  metadata?: Record<string, any>;
}

/**
 * Basic API response format (fallback processing)
 */
export interface BasicApiResponse {
  message: string;
  filename: string;
  chunks?: number;
  total_tokens?: number;
  preview?: string[];
  error?: string;
  status?: string;
  processing_time?: number;
}

/**
 * Enhanced API response format
 */
export interface EnhancedApiResponse {
  job_id: string;
  total_chunks: number;
  total_tokens: number;
  processing_time: number;
  status: string;
  enhanced: boolean;
  chunks: EnhancedChunk[];
  file_info?: Record<string, any>;
  metadata?: Record<string, any>;
  filename?: string;
}

/**
 * Union type for all possible API responses
 */
export type ApiResponse = BasicApiResponse | EnhancedApiResponse;

// =============================================================================
// NORMALIZED INTERNAL TYPES
// =============================================================================

/**
 * Normalized chunk format for internal use
 */
export interface NormalizedChunk {
  id: number;
  text: string;
  tokens: number;
  metadata: Record<string, any>;
}

/**
 * Normalized processing result for consistent frontend usage
 */
export interface ProcessingResult {
  // Core data
  filename: string;
  chunks: number;
  total_tokens: number;
  average_tokens_per_chunk: number;
  processing_time?: number;
  
  // Normalized preview data
  preview: string[];
  previewChunks: NormalizedChunk[];
  
  // Status and metadata
  status: 'completed' | 'error' | 'processing';
  enhanced: boolean;
  error?: string;
  
  // Additional metadata
  metadata: {
    job_id?: string;
    processed_at: string;
    file_info?: Record<string, any>;
    api_metadata?: Record<string, any>;
  };
}

// =============================================================================
// APPLICATION STATE TYPES
// =============================================================================

export type ProcessingStep = 'upload' | 'processing' | 'completed' | 'error';

export interface FileValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  normalizedFile?: File;
}

export interface UploadState {
  step: ProcessingStep;
  progress: number;
  selectedFiles: File[];
  result: ProcessingResult | null;
  error: string | null;
  showFileDetails: boolean;
}

// =============================================================================
// ERROR HANDLING TYPES
// =============================================================================

export interface ProcessingError {
  type: 'network' | 'validation' | 'processing' | 'rendering' | 'unknown';
  message: string;
  details?: Record<string, any>;
  recoverable: boolean;
  suggestions: string[];
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: Record<string, any>;
  errorId: string;
}

// =============================================================================
// UTILITY TYPES
// =============================================================================

export interface ApiConfig {
  baseUrl: string;
  timeout: number;
  maxFileSize: number;
  allowedExtensions: string[];
  defaultTokenizer: string;
  defaultMaxTokens: number;
}

export interface DeviceInfo {
  isMobile: boolean;
  isTablet: boolean;
  userAgent: string;
  supportsFileApi: boolean;
  maxFileSize: number;
}
