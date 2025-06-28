// frontend/src/lib/file-utils.ts
/**
 * File utilities for folder traversal and batch processing
 * Handles recursive directory reading and file filtering
 */

import { isDebugMode } from './feature-flags';

// Supported file extensions (matching backend configuration)
export const SUPPORTED_EXTENSIONS = [
  '.pdf', '.docx', '.txt', '.md', '.py', '.js', '.json', '.csv', 
  '.pptx', '.xlsx', '.html', '.htm', '.xml', '.rtf', '.odt', 
  '.epub', '.mobi', '.azw', '.azw3', '.fb2', '.lit', '.prc'
];

// File validation result interface
export interface FileValidationResult {
  isValid: boolean;
  reason?: string;
  size?: number;
  type?: string;
}

// File tree traversal result
export interface TraversalResult {
  files: File[];
  totalFiles: number;
  skippedFiles: number;
  errors: string[];
  totalSize: number;
}

/**
 * Validate a single file for processing
 */
export const validateFile = (file: File): FileValidationResult => {
  // Check file extension
  const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
  if (!SUPPORTED_EXTENSIONS.includes(extension)) {
    return {
      isValid: false,
      reason: `Unsupported file type: ${extension}`,
      size: file.size,
      type: file.type
    };
  }

  // Check file size (100MB limit)
  const maxSize = 100 * 1024 * 1024; // 100MB
  if (file.size > maxSize) {
    return {
      isValid: false,
      reason: `File too large: ${formatFileSize(file.size)} (max: 100MB)`,
      size: file.size,
      type: file.type
    };
  }

  // Check for hidden files (skip .DS_Store, .thumbs.db, etc.)
  if (file.name.startsWith('.') || file.name.toLowerCase().includes('thumbs.db')) {
    return {
      isValid: false,
      reason: 'Hidden or system file',
      size: file.size,
      type: file.type
    };
  }

  return {
    isValid: true,
    size: file.size,
    type: file.type
  };
};

/**
 * Format file size for human readability
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * Traverse file tree from DataTransferItems (for drag/drop)
 */
export const traverseFileTree = async (items: DataTransferItemList): Promise<TraversalResult> => {
  const result: TraversalResult = {
    files: [],
    totalFiles: 0,
    skippedFiles: 0,
    errors: [],
    totalSize: 0
  };

  const processEntry = async (entry: FileSystemEntry): Promise<void> => {
    if (entry.isFile) {
      const fileEntry = entry as FileSystemFileEntry;
      
      try {
        const file = await new Promise<File>((resolve, reject) => {
          fileEntry.file(resolve, reject);
        });

        result.totalFiles++;
        
        const validation = validateFile(file);
        if (validation.isValid) {
          result.files.push(file);
          result.totalSize += file.size;
          
          if (isDebugMode()) {
            console.log(`✅ Added file: ${file.name} (${formatFileSize(file.size)})`);
          }
        } else {
          result.skippedFiles++;
          
          if (isDebugMode()) {
            console.log(`⏭️ Skipped file: ${file.name} - ${validation.reason}`);
          }
        }
      } catch (error) {
        result.errors.push(`Failed to read file: ${entry.name}`);
        
        if (isDebugMode()) {
          console.error(`❌ Error reading file ${entry.name}:`, error);
        }
      }
    } else if (entry.isDirectory) {
      const dirEntry = entry as FileSystemDirectoryEntry;
      
      try {
        const entries = await readDirectory(dirEntry);
        
        // Process all entries in this directory
        for (const childEntry of entries) {
          await processEntry(childEntry);
        }
      } catch (error) {
        result.errors.push(`Failed to read directory: ${entry.name}`);
        
        if (isDebugMode()) {
          console.error(`❌ Error reading directory ${entry.name}:`, error);
        }
      }
    }
  };

  // Process all dropped items
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    
    if (item.kind === 'file') {
      const entry = item.webkitGetAsEntry?.();
      
      if (entry) {
        await processEntry(entry);
      } else {
        // Fallback for browsers without webkitGetAsEntry
        const file = item.getAsFile();
        if (file) {
          result.totalFiles++;
          
          const validation = validateFile(file);
          if (validation.isValid) {
            result.files.push(file);
            result.totalSize += file.size;
          } else {
            result.skippedFiles++;
          }
        }
      }
    }
  }

  if (isDebugMode()) {
    console.group('📁 Folder Traversal Complete');
    console.log(`Total files found: ${result.totalFiles}`);
    console.log(`Valid files: ${result.files.length}`);
    console.log(`Skipped files: ${result.skippedFiles}`);
    console.log(`Total size: ${formatFileSize(result.totalSize)}`);
    console.log(`Errors: ${result.errors.length}`);
    console.groupEnd();
  }

  return result;
};

/**
 * Read directory entries using FileSystemDirectoryReader
 */
const readDirectory = async (dirEntry: FileSystemDirectoryEntry): Promise<FileSystemEntry[]> => {
  return new Promise((resolve, reject) => {
    const reader = dirEntry.createReader();
    const entries: FileSystemEntry[] = [];

    const readEntries = () => {
      reader.readEntries((batch) => {
        if (batch.length === 0) {
          // No more entries
          resolve(entries);
        } else {
          // Add this batch and continue reading
          entries.push(...batch);
          readEntries();
        }
      }, reject);
    };

    readEntries();
  });
};

/**
 * Process FileList from input[webkitdirectory] or input[multiple]
 */
export const processFileList = (fileList: FileList): TraversalResult => {
  const result: TraversalResult = {
    files: [],
    totalFiles: fileList.length,
    skippedFiles: 0,
    errors: [],
    totalSize: 0
  };

  for (let i = 0; i < fileList.length; i++) {
    const file = fileList[i];
    
    const validation = validateFile(file);
    if (validation.isValid) {
      result.files.push(file);
      result.totalSize += file.size;
    } else {
      result.skippedFiles++;
      
      if (isDebugMode()) {
        console.log(`⏭️ Skipped file: ${file.name} - ${validation.reason}`);
      }
    }
  }

  if (isDebugMode()) {
    console.group('📄 File List Processing Complete');
    console.log(`Total files: ${result.totalFiles}`);
    console.log(`Valid files: ${result.files.length}`);
    console.log(`Skipped files: ${result.skippedFiles}`);
    console.log(`Total size: ${formatFileSize(result.totalSize)}`);
    console.groupEnd();
  }

  return result;
};

/**
 * Get file icon based on extension
 */
export const getFileIcon = (fileName: string): string => {
  const extension = fileName.split('.').pop()?.toLowerCase();
  
  switch (extension) {
    case 'pdf':
      return '📄';
    case 'docx':
    case 'doc':
      return '📝';
    case 'txt':
    case 'md':
      return '📋';
    case 'py':
    case 'js':
    case 'json':
      return '💻';
    case 'csv':
    case 'xlsx':
    case 'xls':
      return '📊';
    case 'pptx':
    case 'ppt':
      return '📊';
    case 'html':
    case 'htm':
      return '🌐';
    case 'xml':
      return '📋';
    case 'epub':
    case 'mobi':
      return '📚';
    default:
      return '📄';
  }
};

export default {
  validateFile,
  formatFileSize,
  traverseFileTree,
  processFileList,
  getFileIcon,
  SUPPORTED_EXTENSIONS
};