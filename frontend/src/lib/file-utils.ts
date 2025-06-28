// frontend/src/lib/file-utils.ts
/**
 * File Processing Utilities
 * Handles file validation, folder traversal, and processing
 */

// Supported file extensions (40+ formats)
export const SUPPORTED_EXTENSIONS = [
  // Documents
  'pdf', 'docx', 'doc', 'txt', 'epub', 'html', 'htm', 'md', 'markdown', 'rtf',
  
  // Spreadsheets and data
  'xlsx', 'csv', 'json', 'yaml', 'yml', 'xml', 'toml', 'ini',
  
  // Presentations
  'pptx',
  
  // Code files
  'py', 'js', 'jsx', 'ts', 'tsx', 'java', 'cpp', 'cc', 'cxx', 'c', 'h', 'hpp',
  'go', 'rs', 'rb', 'php', 'swift', 'kt', 'cs', 'r', 'scala', 'sh', 'bash', 'zsh', 'fish'
];

// File size limits
const MAX_FILE_SIZE_MB = 100;
const MAX_BATCH_SIZE_MB = 500;
const MAX_BATCH_FILES = 100;
const MAX_FOLDER_DEPTH = 10;

// File validation result interface
export interface FileValidationResult {
  isValid: boolean;
  error?: string;
}

/**
 * Validate a single file
 */
export const validateFile = (file: File): FileValidationResult => {
  // Check file extension
  const extension = getFileExtension(file.name);
  if (!extension || !SUPPORTED_EXTENSIONS.includes(extension)) {
    return {
      isValid: false,
      error: `Unsupported file type: .${extension || 'unknown'}`
    };
  }
  
  // Check file size
  const sizeMB = file.size / (1024 * 1024);
  if (sizeMB > MAX_FILE_SIZE_MB) {
    return {
      isValid: false,
      error: `File too large: ${sizeMB.toFixed(1)}MB (max: ${MAX_FILE_SIZE_MB}MB)`
    };
  }
  
  // Check for empty files
  if (file.size === 0) {
    return {
      isValid: false,
      error: 'File is empty'
    };
  }
  
  return { isValid: true };
};

/**
 * Get file extension (lowercase)
 */
export const getFileExtension = (filename: string): string | null => {
  const lastDot = filename.lastIndexOf('.');
  if (lastDot === -1 || lastDot === filename.length - 1) {
    return null;
  }
  return filename.slice(lastDot + 1).toLowerCase();
};

/**
 * Format file size for display
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

/**
 * Process FileList into File array with validation
 */
export const processFileList = async (fileList: FileList): Promise<File[]> => {
  const files: File[] = [];
  
  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    
    // Skip hidden files and system files
    if (isHiddenFile(file.name)) {
      continue;
    }
    
    files.push(file);
  }
  
  return files;
};

/**
 * Check if file should be hidden/skipped
 */
const isHiddenFile = (filename: string): boolean => {
  const hiddenPrefixes = ['.DS_Store', '.', '__MACOSX', 'Thumbs.db', 'desktop.ini'];
  return hiddenPrefixes.some(prefix => filename.startsWith(prefix));
};

/**
 * Recursive folder traversal using FileSystemEntry API
 * Returns all files found in the directory tree
 */
export const traverseFileTree = async (entry: FileSystemEntry, depth = 0): Promise<File[]> => {
  // Prevent infinite recursion
  if (depth > MAX_FOLDER_DEPTH) {
    console.warn(`Maximum folder depth (${MAX_FOLDER_DEPTH}) exceeded`);
    return [];
  }
  
  return new Promise((resolve, reject) => {
    if (entry.isFile) {
      // Handle file entry
      const fileEntry = entry as FileSystemFileEntry;
      fileEntry.file(
        (file) => {
          // Skip hidden files
          if (isHiddenFile(file.name)) {
            resolve([]);
          } else {
            resolve([file]);
          }
        },
        (error) => {
          console.warn(`Error reading file ${entry.name}:`, error);
          resolve([]); // Continue processing other files
        }
      );
    } else if (entry.isDirectory) {
      // Handle directory entry
      const directoryEntry = entry as FileSystemDirectoryEntry;
      const reader = directoryEntry.createReader();
      
      const allFiles: File[] = [];
      
      const readEntries = () => {
        reader.readEntries(
          async (entries) => {
            if (entries.length === 0) {
              // No more entries, resolve with accumulated files
              resolve(allFiles);
              return;
            }
            
            try {
              // Process all entries in this batch
              const promises = entries.map(childEntry => 
                traverseFileTree(childEntry, depth + 1)
              );
              
              const results = await Promise.all(promises);
              
              // Flatten and add to accumulated files
              for (const fileList of results) {
                allFiles.push(...fileList);
              }
              
              // Read next batch
              readEntries();
            } catch (error) {
              console.warn(`Error processing directory ${entry.name}:`, error);
              resolve(allFiles); // Return what we have so far
            }
          },
          (error) => {
            console.warn(`Error reading directory ${entry.name}:`, error);
            resolve(allFiles); // Return what we have so far
          }
        );
      };
      
      readEntries();
    } else {
      // Unknown entry type
      resolve([]);
    }
  });
};

/**
 * Validate batch of files
 */
export const validateBatch = (files: File[]): { valid: File[]; invalid: File[]; errors: string[] } => {
  const valid: File[] = [];
  const invalid: File[] = [];
  const errors: string[] = [];
  
  // Check batch size
  if (files.length > MAX_BATCH_FILES) {
    errors.push(`Too many files: ${files.length} (max: ${MAX_BATCH_FILES})`);
    return { valid, invalid, errors };
  }
  
  // Check total batch size
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  const totalSizeMB = totalSize / (1024 * 1024);
  
  if (totalSizeMB > MAX_BATCH_SIZE_MB) {
    errors.push(`Batch too large: ${totalSizeMB.toFixed(1)}MB (max: ${MAX_BATCH_SIZE_MB}MB)`);
    return { valid, invalid, errors };
  }
  
  // Validate individual files
  for (const file of files) {
    const validation = validateFile(file);
    if (validation.isValid) {
      valid.push(file);
    } else {
      invalid.push(file);
      errors.push(`${file.name}: ${validation.error}`);
    }
  }
  
  return { valid, invalid, errors };
};

/**
 * Extract files from dropped items (handles both files and folders)
 */
export const extractFilesFromDropItems = async (items: DataTransferItemList): Promise<File[]> => {
  const allFiles: File[] = [];
  
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    
    if (item.kind === 'file') {
      const entry = item.webkitGetAsEntry?.();
      if (entry) {
        const files = await traverseFileTree(entry);
        allFiles.push(...files);
      } else {
        // Fallback for browsers without webkitGetAsEntry
        const file = item.getAsFile();
        if (file && !isHiddenFile(file.name)) {
          allFiles.push(file);
        }
      }
    }
  }
  
  return allFiles;
};

/**
 * Check if browser supports the FileSystemEntry API
 */
export const supportsFileSystemAccess = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  try {
    const dt = new DataTransfer();
    const item = dt.items[0];
    return item && typeof item.webkitGetAsEntry === 'function';
  } catch {
    return false;
  }
};

/**
 * Debug utility to log file processing information
 */
export const debugFileInfo = (files: File[], context = 'File processing'): void => {
  if (process.env.NODE_ENV === 'development') {
    console.group(`[File Utils] ${context}`);
    console.log(`Total files: ${files.length}`);
    console.log(`Total size: ${formatFileSize(files.reduce((sum, f) => sum + f.size, 0))}`);
    
    const extensions = files.map(f => getFileExtension(f.name)).filter(Boolean);
    const uniqueExtensions = [...new Set(extensions)];
    console.log(`File types: ${uniqueExtensions.join(', ')}`);
    
    if (files.length <= 10) {
      console.table(files.map(f => ({
        name: f.name,
        size: formatFileSize(f.size),
        type: getFileExtension(f.name)
      })));
    }
    console.groupEnd();
  }
};