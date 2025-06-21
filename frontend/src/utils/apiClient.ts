// frontend/src/utils/apiClient.ts
// Enhanced API client with robust error handling and mobile compatibility - Fixed TypeScript Issues

import { ProcessingResult, ProcessingError, DeviceInfo } from '@/types/types';
import { normalizeApiResponse, createProcessingError } from './apiDataNormalizer';
import { detectDevice } from './fileValidator';

// =============================================================================
// CONFIGURATION
// =============================================================================

interface ApiConfig {
  baseUrl: string;
  timeout: number;
  retryAttempts: number;
  retryDelay: number;
}

const getApiConfig = (): ApiConfig => {
  const deviceInfo = detectDevice();
  
  return {
    baseUrl: process.env.NEXT_PUBLIC_API_URL || 'https://api.wolfstitch.dev',
    timeout: deviceInfo.isMobile ? 120000 : 60000, // Longer timeout for mobile
    retryAttempts: 3,
    retryDelay: 1000
  };
};

// =============================================================================
// ERROR HANDLING
// =============================================================================

/**
 * Parse API error response
 */
async function parseApiError(response: Response): Promise<ProcessingError> {
  let errorMessage = `API Error: ${response.status}`;
  const details: Record<string, unknown> = {
    status: response.status,
    statusText: response.statusText,
    url: response.url
  };
  
  try {
    const contentType = response.headers.get('content-type');
    
    if (contentType?.includes('application/json')) {
      const errorData = await response.json() as Record<string, unknown>;
      errorMessage = String(errorData.detail || errorData.message) || errorMessage;
      details.apiError = errorData;
    } else {
      const errorText = await response.text();
      if (errorText) {
        errorMessage = errorText.substring(0, 200); // Limit error message length
        details.responseText = errorText;
      }
    }
  } catch (parseError) {
    console.warn('Could not parse error response:', parseError);
    details.parseError = parseError instanceof Error ? parseError.message : String(parseError);
  }
  
  // Determine error type based on status code
  const type: ProcessingError['type'] = 
    response.status >= 400 && response.status < 500
      ? response.status === 413 ? 'validation' : 'validation'
      : response.status >= 500
        ? 'processing'
        : 'network';
  
  return createProcessingError(type, errorMessage, details);
}

/**
 * Handle network errors
 */
function handleNetworkError(error: Error): ProcessingError {
  console.error('Network error:', error);
  
  let message = 'Network error occurred';
  const type: ProcessingError['type'] = 'network';
  
  if (error.name === 'AbortError') {
    message = 'Request timed out. Please try again.';
  } else if (error.message.includes('fetch')) {
    message = 'Could not connect to server. Please check your internet connection.';
  } else if (error.message.includes('CORS')) {
    message = 'Cross-origin request blocked. Please try again.';
  }
  
  return createProcessingError(type, message, {
    originalError: error.message,
    errorName: error.name,
    stack: error.stack
  });
}

// =============================================================================
// RETRY LOGIC
// =============================================================================

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Retry function with exponential backoff
 */
async function withRetry<T>(
  operation: () => Promise<T>,
  maxAttempts: number,
  baseDelay: number,
  shouldRetry: (error: unknown) => boolean = () => true
): Promise<T> {
  let lastError: unknown;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      
      console.warn(`Attempt ${attempt}/${maxAttempts} failed:`, error);
      
      // Don't retry on final attempt or if error is not retryable
      if (attempt === maxAttempts || !shouldRetry(error)) {
        break;
      }
      
      // Exponential backoff with jitter
      const delay = baseDelay * Math.pow(2, attempt - 1) + Math.random() * 1000;
      console.log(`Retrying in ${delay.toFixed(0)}ms...`);
      await sleep(delay);
    }
  }
  
  throw lastError;
}

/**
 * Determine if error should be retried
 */
function shouldRetryError(error: unknown): boolean {
  const errorObj = error as Record<string, unknown>;
  
  // Don't retry client errors (4xx) except for specific cases
  if (errorObj?.status && typeof errorObj.status === 'number' && errorObj.status >= 400 && errorObj.status < 500) {
    // Retry rate limiting and timeouts
    return errorObj.status === 429 || errorObj.status === 408;
  }
  
  // Retry server errors (5xx) and network errors
  if ((errorObj?.status && typeof errorObj.status === 'number' && errorObj.status >= 500) || 
      errorObj?.name === 'TypeError' || errorObj?.name === 'NetworkError') {
    return true;
  }
  
  // Retry timeout errors
  if (errorObj?.name === 'AbortError') {
    return true;
  }
  
  return false;
}

// =============================================================================
// MAIN API CLIENT
// =============================================================================

export class ApiClient {
  private config: ApiConfig;
  private deviceInfo: DeviceInfo;
  
  constructor() {
    this.config = getApiConfig();
    this.deviceInfo = detectDevice();
    
    console.log('ApiClient initialized:', {
      baseUrl: this.config.baseUrl,
      deviceInfo: this.deviceInfo
    });
  }
  
  /**
   * Create fetch request with timeout and device-specific headers
   */
  private async fetchWithTimeout(
    url: string,
    options: RequestInit,
    timeoutMs: number
  ): Promise<Response> {
    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    
    try {
      // Add device-specific headers
      const headers: Record<string, string> = {
        ...(options.headers as Record<string, string> || {}),
      };
      
      // Add device information for backend optimization
      if (this.deviceInfo.isMobile) {
        headers['X-Device-Type'] = 'mobile';
      }
      
      if (this.deviceInfo.userAgent) {
        headers['X-User-Agent'] = this.deviceInfo.userAgent;
      }
      
      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal,
        mode: 'cors' // Ensure CORS is handled properly
      });
      
      clearTimeout(timeoutId);
      return response;
      
    } catch (error) {
      clearTimeout(timeoutId);
      throw error;
    }
  }
  
  /**
   * Process file with enhanced error handling and retry logic
   */
  async processFile(
    file: File,
    options: {
      tokenizer?: string;
      maxTokens?: number;
      onProgress?: (progress: number) => void;
    } = {}
  ): Promise<ProcessingResult> {
    const { tokenizer = 'word-estimate', maxTokens = 1024, onProgress } = options;
    
    console.log('Processing file:', {
      name: file.name,
      size: file.size,
      type: file.type,
      tokenizer,
      maxTokens,
      deviceInfo: this.deviceInfo
    });
    
    // Simulate progress for user feedback
    let progressInterval: NodeJS.Timeout | null = null;
    if (onProgress) {
      let currentProgress = 0;
      progressInterval = setInterval(() => {
        currentProgress = Math.min(currentProgress + Math.random() * 15, 90);
        onProgress(currentProgress);
      }, 200);
    }
    
    try {
      const result = await withRetry(
        async () => {
          // Prepare form data
          const formData = new FormData();
          formData.append('file', file);
          formData.append('tokenizer', tokenizer);
          formData.append('max_tokens', maxTokens.toString());
          
          // Log form data for debugging
          console.log('FormData contents:', {
            fileName: file.name,
            fileSize: file.size,
            fileType: file.type,
            tokenizer,
            maxTokens
          });
          
          const fullURL = `${this.config.baseUrl}/api/v1/quick-process`;
          console.log('API URL:', fullURL);
          
          // Make request with timeout
          const response = await this.fetchWithTimeout(
            fullURL,
            {
              method: 'POST',
              body: formData
            },
            this.config.timeout
          );
          
          // Handle non-2xx responses
          if (!response.ok) {
            throw await parseApiError(response);
          }
          
          // Parse response
          const responseData = await response.json() as Record<string, unknown>;
          console.log('Raw API response:', responseData);
          
          // Normalize response data
          const normalizedResult = normalizeApiResponse(responseData);
          console.log('Normalized result:', normalizedResult);
          
          return normalizedResult;
        },
        this.config.retryAttempts,
        this.config.retryDelay,
        shouldRetryError
      );
      
      // Complete progress
      if (onProgress) {
        onProgress(100);
      }
      
      return result;
      
    } catch (error) {
      console.error('File processing failed:', error);
      
      // Handle different error types
      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw createProcessingError('network', 'Request timed out. Please try again with a smaller file or better internet connection.');
        } else if (error.message.includes('fetch')) {
          throw handleNetworkError(error);
        }
      }
      
      // If it's already a ProcessingError, re-throw it
      if (error && typeof error === 'object' && 'type' in error) {
        throw error;
      }
      
      // Unknown error
      throw createProcessingError('unknown', `Processing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      
    } finally {
      // Clean up progress interval
      if (progressInterval) {
        clearInterval(progressInterval);
      }
    }
  }
  
  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<{ status: string; timestamp: number }> {
    try {
      const response = await this.fetchWithTimeout(
        `${this.config.baseUrl}/health`,
        { method: 'GET' },
        10000 // Short timeout for health check
      );
      
      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }
      
      return await response.json() as { status: string; timestamp: number };
      
    } catch (error) {
      console.error('Health check failed:', error);
      throw createProcessingError('network', 'Could not connect to processing service');
    }
  }
}

// =============================================================================
// SINGLETON INSTANCE
// =============================================================================

export const apiClient = new ApiClient();

// =============================================================================
// CONVENIENCE FUNCTIONS
// =============================================================================

/**
 * Process file with simplified interface
 */
export async function processFile(
  file: File,
  options?: {
    tokenizer?: string;
    maxTokens?: number;
    onProgress?: (progress: number) => void;
  }
): Promise<ProcessingResult> {
  return apiClient.processFile(file, options);
}

/**
 * Check API health
 */
export async function checkApiHealth(): Promise<boolean> {
  try {
    await apiClient.healthCheck();
    return true;
  } catch {
    return false;
  }
}