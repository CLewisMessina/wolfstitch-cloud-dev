// frontend/types/global.d.ts
/**
 * TypeScript global definitions for folder drop functionality
 * Extends HTML interfaces to support webkitdirectory and related APIs
 */

// Extend HTMLInputElement to support webkitdirectory
interface HTMLInputElement {
  webkitdirectory?: boolean;
  directory?: boolean;
}

// FileSystemEntry API interfaces for drag/drop folder handling
interface FileSystemEntry {
  readonly isFile: boolean;
  readonly isDirectory: boolean;
  readonly name: string;
  readonly fullPath: string;
}

interface FileSystemFileEntry extends FileSystemEntry {
  readonly isFile: true;
  readonly isDirectory: false;
  file(successCallback: (file: File) => void, errorCallback?: (error: Error) => void): void;
}

interface FileSystemDirectoryEntry extends FileSystemEntry {
  readonly isFile: false;
  readonly isDirectory: true;
  createReader(): FileSystemDirectoryReader;
}

interface FileSystemDirectoryReader {
  readEntries(
    successCallback: (entries: FileSystemEntry[]) => void,
    errorCallback?: (error: Error) => void
  ): void;
}

// Extend DataTransferItem to support webkitGetAsEntry
interface DataTransferItem {
  webkitGetAsEntry?: () => FileSystemEntry | null;
}

// Global feature flags for batch processing
declare global {
  interface Window {
    // Feature flags
    BATCH_PROCESSING_ENABLED?: boolean;
    
    // Debug helpers for development
    __WOLFSTITCH_DEBUG__?: {
      logFileTraversal?: boolean;
      logBatchProgress?: boolean;
      simulateSlowNetwork?: boolean;
    };
  }
}

// Export empty object to make this a module
export {};