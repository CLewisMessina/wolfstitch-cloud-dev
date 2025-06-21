// frontend/src/utils/apiDataNormalizer.ts
// Data normalization layer to handle different API response formats

import { 
  ApiResponse, 
  BasicApiResponse, 
  EnhancedApiResponse, 
  ProcessingResult, 
  NormalizedChunk,
  ProcessingError 
} from '@/types/types';

// =============================================================================
// TYPE GUARDS
// =============================================================================

/**
 * Check if response is enhanced format
 */
function isEnhancedResponse(response: ApiResponse): response is EnhancedApiResponse {
  return 'enhanced' in response && 'chunks' in response && Array.isArray(response.chunks);
}

/**
 * Check if response is basic format
 */
function isBasicResponse(response: ApiResponse): response is BasicApiResponse {
  return 'message' in response && 'filename' in response;
}

/**
 * Validate that response has minimum required fields
 */
function hasMinimumFields(response: any): boolean {
  return response && (
    (response.filename || response.file_info?.filename) ||
    (response.chunks !== undefined || response.total_chunks !== undefined)
  );
}

// =============================================================================
// NORMALIZATION FUNCTIONS
// =============================================================================

/**
 * Normalize enhanced API response chunks to standard format
 */
function normalizeEnhancedChunks(chunks: any[]): { normalizedChunks: NormalizedChunk[]; preview: string[] } {
  if (!Array.isArray(chunks)) {
    console.warn('Enhanced chunks is not an array:', chunks);
    return { normalizedChunks: [], preview: [] };
  }

  const normalizedChunks: NormalizedChunk[] = [];
  const preview: string[] = [];

  chunks.forEach((chunk, index) => {
    try {
      // Handle different chunk formats
      let text: string;
      let tokens: number;
      let metadata: Record<string, any> = {};

      if (typeof chunk === 'string') {
        // Chunk is already a string
        text = chunk;
        tokens = Math.ceil(chunk.length / 4); // Rough token estimate
      } else if (chunk && typeof chunk === 'object') {
        // Chunk is an object - extract text
        text = chunk.text || chunk.content || String(chunk);
        tokens = chunk.token_count || chunk.tokens || Math.ceil(text.length / 4);
        metadata = {
          chunk_index: chunk.chunk_index ?? index,
          original_token_count: chunk.token_count,
          ...chunk.metadata
        };
      } else {
        // Fallback for unexpected formats
        console.warn('Unexpected chunk format:', chunk);
        text = String(chunk);
        tokens = Math.ceil(text.length / 4);
      }

      // Ensure text is a string and not empty
      if (typeof text !== 'string' || text.trim().length === 0) {
        console.warn('Invalid text in chunk:', chunk);
        return; // Skip this chunk
      }

      const normalizedChunk: NormalizedChunk = {
        id: index,
        text: text.trim(),
        tokens,
        metadata
      };

      normalizedChunks.push(normalizedChunk);
      preview.push(text.trim());

    } catch (error) {
      console.error('Error normalizing chunk at index', index, ':', error);
      // Continue processing other chunks
    }
  });

  return { normalizedChunks, preview };
}

/**
 * Normalize basic API response preview to standard format
 */
function normalizeBasicPreview(preview: any): { normalizedChunks: NormalizedChunk[]; preview: string[] } {
  if (!Array.isArray(preview)) {
    console.warn('Basic preview is not an array:', preview);
    return { normalizedChunks: [], preview: [] };
  }

  const normalizedChunks: NormalizedChunk[] = [];
  const normalizedPreview: string[] = [];

  preview.forEach((item, index) => {
    try {
      const text = typeof item === 'string' ? item : String(item);
      
      if (text.trim().length === 0) {
        return; // Skip empty chunks
      }

      const tokens = Math.ceil(text.length / 4); // Rough token estimate

      normalizedChunks.push({
        id: index,
        text: text.trim(),
        tokens,
        metadata: { source: 'basic_processing' }
      });

      normalizedPreview.push(text.trim());

    } catch (error) {
      console.error('Error normalizing basic preview item at index', index, ':', error);
    }
  });

  return { normalizedChunks, preview: normalizedPreview };
}

/**
 * Extract filename from different response formats
 */
function extractFilename(response: ApiResponse): string {
  if (isBasicResponse(response)) {
    return response.filename || 'unknown-file';
  }
  
  if (isEnhancedResponse(response)) {
    return response.filename || 
           response.file_info?.filename || 
           response.file_info?.name || 
           'processed-file';
  }
  
  return 'unknown-file';
}

/**
 * Calculate processing statistics
 */
function calculateStats(chunks: NormalizedChunk[], totalTokens?: number) {
  const chunkCount = chunks.length;
  const calculatedTokens = chunks.reduce((sum, chunk) => sum + chunk.tokens, 0);
  const finalTokens = totalTokens || calculatedTokens;
  
  return {
    chunks: chunkCount,
    total_tokens: finalTokens,
    average_tokens_per_chunk: chunkCount > 0 ? Math.round(finalTokens / chunkCount) : 0
  };
}

// =============================================================================
// MAIN NORMALIZATION FUNCTION
// =============================================================================

/**
 * Normalize any API response to consistent ProcessingResult format
 * Handles both enhanced and basic API responses with robust error handling
 */
export function normalizeApiResponse(response: any): ProcessingResult {
  console.log('Normalizing API response:', response);

  try {
    // Validate minimum required fields
    if (!hasMinimumFields(response)) {
      throw new Error('Response missing required fields');
    }

    let normalizedChunks: NormalizedChunk[] = [];
    let preview: string[] = [];
    let enhanced = false;
    let processingTime: number | undefined;

    // Handle enhanced response format
    if (isEnhancedResponse(response)) {
      console.log('Processing enhanced API response');
      enhanced = true;
      processingTime = response.processing_time;
      
      const result = normalizeEnhancedChunks(response.chunks);
      normalizedChunks = result.normalizedChunks;
      preview = result.preview;
    }
    // Handle basic response format
    else if (isBasicResponse(response) && response.preview) {
      console.log('Processing basic API response');
      processingTime = response.processing_time;
      
      const result = normalizeBasicPreview(response.preview);
      normalizedChunks = result.normalizedChunks;
      preview = result.preview;
    }
    // Handle unexpected formats
    else {
      console.warn('Unexpected API response format, attempting to extract data');
      
      // Try to find chunk-like data in any property
      const possibleChunks = response.chunks || response.preview || response.data || [];
      if (Array.isArray(possibleChunks) && possibleChunks.length > 0) {
        const result = normalizeEnhancedChunks(possibleChunks);
        normalizedChunks = result.normalizedChunks;
        preview = result.preview;
      }
    }

    // Extract filename
    const filename = extractFilename(response);

    // Calculate statistics
    const stats = calculateStats(normalizedChunks, response.total_tokens);

    // Build normalized result
    const normalizedResult: ProcessingResult = {
      filename,
      chunks: stats.chunks,
      total_tokens: stats.total_tokens,
      average_tokens_per_chunk: stats.average_tokens_per_chunk,
      processing_time: processingTime,
      
      preview,
      previewChunks: normalizedChunks,
      
      status: 'completed',
      enhanced,
      
      metadata: {
        job_id: response.job_id,
        processed_at: new Date().toISOString(),
        file_info: response.file_info,
        api_metadata: response.metadata
      }
    };

    console.log('Successfully normalized API response:', normalizedResult);
    return normalizedResult;

  } catch (error) {
    console.error('Error normalizing API response:', error);
    
    // Return error result with fallback data
    return {
      filename: extractFilename(response) || 'error-file',
      chunks: 0,
      total_tokens: 0,
      average_tokens_per_chunk: 0,
      
      preview: [],
      previewChunks: [],
      
      status: 'error',
      enhanced: false,
      error: error instanceof Error ? error.message : 'Unknown normalization error',
      
      metadata: {
        processed_at: new Date().toISOString(),
        error_details: error instanceof Error ? error.stack : String(error)
      }
    };
  }
}

// =============================================================================
// ERROR HANDLING UTILITIES
// =============================================================================

/**
 * Create standardized processing error
 */
export function createProcessingError(
  type: ProcessingError['type'],
  message: string,
  details?: Record<string, any>
): ProcessingError {
  const suggestions: string[] = [];
  
  switch (type) {
    case 'network':
      suggestions.push('Check your internet connection', 'Try uploading again');
      break;
    case 'validation':
      suggestions.push('Check file format and size', 'Try a different file');
      break;
    case 'processing':
      suggestions.push('Try a smaller file', 'Contact support if problem persists');
      break;
    case 'rendering':
      suggestions.push('Refresh the page', 'Try uploading again');
      break;
    default:
      suggestions.push('Refresh the page and try again');
  }
  
  return {
    type,
    message,
    details,
    recoverable: type !== 'validation',
    suggestions
  };
}
