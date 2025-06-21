// frontend/src/utils/fileValidator.ts
// Enhanced file validation for desktop and mobile compatibility

import { FileValidationResult, DeviceInfo } from '@/types/types';

// =============================================================================
// CONFIGURATION
// =============================================================================

const VALIDATION_CONFIG = {
  // File size limits (in bytes)
  MAX_FILE_SIZE_ANONYMOUS: 100 * 1024 * 1024, // 100MB for anonymous
  MAX_FILE_SIZE_MOBILE: 50 * 1024 * 1024,     // 50MB for mobile (more conservative)
  
  // Allowed extensions (flexible for mobile)
  ALLOWED_EXTENSIONS: [
    // Documents
    'pdf', 'docx', 'doc', 'txt', 'rtf', 'odt',
    // Web formats
    'html', 'htm', 'md', 'markdown',
    // Spreadsheets
    'xlsx', 'xls', 'csv', 'ods',
    // Presentations
    'pptx', 'ppt', 'odp',
    // Code files
    'js', 'ts', 'py', 'java', 'cpp', 'c', 'cs', 'php', 'rb', 'go', 'rust', 'swift',
    // Data formats
    'json', 'xml', 'yaml', 'yml',
    // E-books
    'epub', 'mobi',
    // Archives (for mobile compatibility)
    'zip', 'rar'
  ],
  
  // MIME types that mobile devices might use
  MOBILE_MIME_MAPPINGS: {
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
    'application/msword': 'doc',
    'application/vnd.ms-excel': 'xls',
    'application/vnd.ms-powerpoint': 'ppt',
    'text/plain': 'txt',
    'text/markdown': 'md',
    'text/html': 'html',
    'application/json': 'json',
    'application/xml': 'xml',
    'text/xml': 'xml',
    'text/csv': 'csv',
    'application/pdf': 'pdf',
    'application/epub+zip': 'epub'
  }
};

// =============================================================================
// DEVICE DETECTION
// =============================================================================

/**
 * Detect device capabilities and limitations
 */
export function detectDevice(): DeviceInfo {
  const userAgent = navigator.userAgent || '';
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
  const isTablet = /iPad|Android(?=.*\bMobile\b)/i.test(userAgent);
  
  return {
    isMobile,
    isTablet,
    userAgent,
    supportsFileApi: typeof File !== 'undefined' && typeof FileReader !== 'undefined',
    maxFileSize: isMobile ? VALIDATION_CONFIG.MAX_FILE_SIZE_MOBILE : VALIDATION_CONFIG.MAX_FILE_SIZE_ANONYMOUS
  };
}

// =============================================================================
// FILE VALIDATION FUNCTIONS
// =============================================================================

/**
 * Extract file extension with mobile compatibility
 */
function extractFileExtension(file: File): string {
  // Primary: use filename extension
  if (file.name && file.name.includes('.')) {
    const extension = file.name.split('.').pop()?.toLowerCase();
    if (extension && VALIDATION_CONFIG.ALLOWED_EXTENSIONS.includes(extension)) {
      return extension;
    }
  }
  
  // Fallback: use MIME type mapping (important for mobile)
  if (file.type && VALIDATION_CONFIG.MOBILE_MIME_MAPPINGS[file.type]) {
    return VALIDATION_CONFIG.MOBILE_MIME_MAPPINGS[file.type];
  }
  
  // Last resort: try to guess from MIME type
  if (file.type) {
    const mimeType = file.type.toLowerCase();
    
    if (mimeType.startsWith('text/')) {
      return 'txt';
    } else if (mimeType.includes('pdf')) {
      return 'pdf';
    } else if (mimeType.includes('word') || mimeType.includes('document')) {
      return 'docx';
    } else if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) {
      return 'xlsx';
    } else if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) {
      return 'pptx';
    }
  }
  
  return '';
}

/**
 * Validate file size with device-specific limits
 */
function validateFileSize(file: File, deviceInfo: DeviceInfo): { isValid: boolean; errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  // Check if file size is available
  if (file.size === undefined || file.size === 0) {
    if (deviceInfo.isMobile) {
      warnings.push('File size could not be determined (common on mobile devices)');
    } else {
      errors.push('File appears to be empty or corrupted');
    }
    return { isValid: deviceInfo.isMobile, errors, warnings };
  }
  
  // Check against device-specific limits
  const maxSize = deviceInfo.maxFileSize;
  const fileSizeMB = file.size / (1024 * 1024);
  
  if (file.size > maxSize) {
    const maxSizeMB = maxSize / (1024 * 1024);
    errors.push(`File too large: ${fileSizeMB.toFixed(1)}MB. Maximum allowed: ${maxSizeMB}MB`);
    return { isValid: false, errors, warnings };
  }
  
  // Warnings for large files
  if (fileSizeMB > 25 && deviceInfo.isMobile) {
    warnings.push('Large file detected. Processing may take longer on mobile devices.');
  }
  
  return { isValid: true, errors, warnings };
}

/**
 * Validate file type and extension
 */
function validateFileType(file: File, deviceInfo: DeviceInfo): { isValid: boolean; errors: string[]; warnings: string[]; extension: string } {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  const extension = extractFileExtension(file);
  
  if (!extension) {
    if (deviceInfo.isMobile) {
      // More lenient for mobile - try to proceed if it looks like a document
      if (file.type && (
        file.type.includes('text') ||
        file.type.includes('document') ||
        file.type.includes('pdf') ||
        file.type.includes('application')
      )) {
        warnings.push('File type could not be determined from extension, but MIME type suggests it may be processable');
        return { isValid: true, errors, warnings, extension: 'unknown' };
      }
    }
    
    errors.push('Unsupported file type. Please use: PDF, DOCX, TXT, MD, or other supported formats.');
    return { isValid: false, errors, warnings, extension: '' };
  }
  
  if (!VALIDATION_CONFIG.ALLOWED_EXTENSIONS.includes(extension)) {
    errors.push(`File type '.${extension}' is not supported. Supported types: ${VALIDATION_CONFIG.ALLOWED_EXTENSIONS.join(', ')}`);
    return { isValid: false, errors, warnings, extension };
  }
  
  // Mobile-specific warnings
  if (deviceInfo.isMobile) {
    if (['zip', 'rar'].includes(extension)) {
      warnings.push('Archive files may not be fully supported on mobile devices');
    }
    if (['xlsx', 'pptx', 'docx'].includes(extension)) {
      warnings.push('Complex document processing may take longer on mobile devices');
    }
  }
  
  return { isValid: true, errors, warnings, extension };
}

/**
 * Validate file name
 */
function validateFileName(file: File): { isValid: boolean; errors: string[]; warnings: string[] } {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  if (!file.name || file.name.trim().length === 0) {
    errors.push('File must have a valid name');
    return { isValid: false, errors, warnings };
  }
  
  // Check for problematic characters
  const problematicChars = /[<>:"/\\|?*\x00-\x1f]/;
  if (problematicChars.test(file.name)) {
    warnings.push('Filename contains special characters that may cause issues');
  }
  
  // Check name length
  if (file.name.length > 255) {
    errors.push('Filename too long (maximum 255 characters)');
    return { isValid: false, errors, warnings };
  }
  
  return { isValid: true, errors, warnings };
}

/**
 * Create normalized file with corrected properties
 */
function normalizeFile(file: File, extension: string): File {
  // For mobile compatibility, ensure proper filename
  let normalizedName = file.name;
  
  // Add extension if missing
  if (extension && extension !== 'unknown' && !normalizedName.toLowerCase().endsWith(`.${extension}`)) {
    normalizedName = `${normalizedName}.${extension}`;
  }
  
  // Create new file with normalized properties if needed
  if (normalizedName !== file.name) {
    try {
      return new File([file], normalizedName, {
        type: file.type,
        lastModified: file.lastModified
      });
    } catch (error) {
      console.warn('Could not create normalized file:', error);
      return file;
    }
  }
  
  return file;
}

// =============================================================================
// MAIN VALIDATION FUNCTION
// =============================================================================

/**
 * Comprehensive file validation with mobile device support
 */
export function validateFile(file: File): FileValidationResult {
  console.log('Validating file:', file.name, file.size, file.type);
  
  const deviceInfo = detectDevice();
  console.log('Device info:', deviceInfo);
  
  const allErrors: string[] = [];
  const allWarnings: string[] = [];
  
  try {
    // Validate file name
    const nameValidation = validateFileName(file);
    allErrors.push(...nameValidation.errors);
    allWarnings.push(...nameValidation.warnings);
    
    if (!nameValidation.isValid) {
      return { isValid: false, errors: allErrors, warnings: allWarnings };
    }
    
    // Validate file type
    const typeValidation = validateFileType(file, deviceInfo);
    allErrors.push(...typeValidation.errors);
    allWarnings.push(...typeValidation.warnings);
    
    if (!typeValidation.isValid) {
      return { isValid: false, errors: allErrors, warnings: allWarnings };
    }
    
    // Validate file size
    const sizeValidation = validateFileSize(file, deviceInfo);
    allErrors.push(...sizeValidation.errors);
    allWarnings.push(...sizeValidation.warnings);
    
    if (!sizeValidation.isValid) {
      return { isValid: false, errors: allErrors, warnings: allWarnings };
    }
    
    // Create normalized file
    const normalizedFile = normalizeFile(file, typeValidation.extension);
    
    console.log('File validation successful:', {
      originalName: file.name,
      normalizedName: normalizedFile.name,
      extension: typeValidation.extension,
      size: file.size,
      warnings: allWarnings
    });
    
    return {
      isValid: true,
      errors: allErrors,
      warnings: allWarnings,
      normalizedFile
    };
    
  } catch (error) {
    console.error('File validation error:', error);
    allErrors.push(`Validation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    
    return {
      isValid: false,
      errors: allErrors,
      warnings: allWarnings
    };
  }
}

/**
 * Quick validation for multiple files
 */
export function validateFiles(files: File[]): { validFiles: File[]; errors: string[]; warnings: string[] } {
  const validFiles: File[] = [];
  const allErrors: string[] = [];
  const allWarnings: string[] = [];
  
  files.forEach((file, index) => {
    const validation = validateFile(file);
    
    if (validation.isValid && validation.normalizedFile) {
      validFiles.push(validation.normalizedFile);
    } else {
      allErrors.push(`File ${index + 1} (${file.name}): ${validation.errors.join(', ')}`);
    }
    
    allWarnings.push(...validation.warnings);
  });
  
  return { validFiles, errors: allErrors, warnings: allWarnings };
}
