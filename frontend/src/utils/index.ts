// frontend/src/utils/index.ts
// Central exports for all utility functions

// Type definitions
export * from '../types/types';

// Core utilities
export { normalizeApiResponse, createProcessingError } from './apiDataNormalizer';
export { validateFile, validateFiles, detectDevice } from './fileValidator';
export { processFile, checkApiHealth, apiClient } from './apiClient';

// React components
export { default as ErrorBoundary } from '../components/ErrorBoundary';

// Utility functions
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export const getFileIcon = (fileName: string): string => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  
  const iconMap: Record<string, string> = {
    pdf: 'FileText',
    docx: 'FileText', 
    doc: 'FileText',
    txt: 'FileText',
    md: 'FileText',
    py: 'Code',
    js: 'Code',
    ts: 'Code',
    json: 'Code',
    csv: 'Table',
    xlsx: 'Table',
    pptx: 'Presentation'
  };
  
  return iconMap[extension || ''] || 'File';
};

export const generateDownloadFilename = (originalFilename: string, suffix = '_processed'): string => {
  const nameParts = originalFilename.split('.');
  const extension = nameParts.pop();
  const baseName = nameParts.join('.');
  
  return `${baseName}${suffix}.jsonl`;
};

export const createJsonlContent = (chunks: any[], metadata: any = {}): string => {
  return chunks.map((chunk, index) => 
    JSON.stringify({
      text: typeof chunk === 'string' ? chunk : chunk.text,
      chunk_id: index + 1,
      tokens: typeof chunk === 'object' && chunk.tokens ? chunk.tokens : Math.ceil((chunk.text || chunk).length / 4),
      metadata: {
        processed_at: new Date().toISOString(),
        ...metadata,
        ...(typeof chunk === 'object' ? chunk.metadata : {})
      }
    })
  ).join('\n');
};

// Development utilities
export const isDevelopment = (): boolean => {
  return process.env.NODE_ENV === 'development';
};

export const getApiConfig = () => ({
  baseUrl: process.env.NEXT_PUBLIC_API_URL || 'https://api.wolfstitch.dev',
  environment: process.env.NEXT_PUBLIC_ENVIRONMENT || 'development'
});

// Error logging utility
export const logError = (error: any, context?: string) => {
  if (isDevelopment()) {
    console.error(`[${context || 'Unknown'}]`, error);
  }
  
  // In production, you could send to error tracking service here
  // Example: Sentry.captureException(error, { tags: { context } });
};

// Performance monitoring
export const measurePerformance = async <T>(
  operation: () => Promise<T>,
  label: string
): Promise<T> => {
  const start = performance.now();
  
  try {
    const result = await operation();
    const duration = performance.now() - start;
    
    if (isDevelopment()) {
      console.log(`[Performance] ${label}: ${duration.toFixed(2)}ms`);
    }
    
    return result;
  } catch (error) {
    const duration = performance.now() - start;
    logError(error, `${label} (failed after ${duration.toFixed(2)}ms)`);
    throw error;
  }
};
