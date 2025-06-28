// frontend/src/lib/feature-flags.ts
/**
 * Feature Flag System
 * Production-safe feature toggles with environment-based configuration
 */

// Environment variables (with safe defaults)
const ENABLE_BATCH = process.env.NEXT_PUBLIC_ENABLE_BATCH === 'true';
const ENABLE_FOLDER_DROP = process.env.NEXT_PUBLIC_ENABLE_FOLDER_DROP === 'true';
const DEBUG_MODE = process.env.NEXT_PUBLIC_DEBUG_MODE === 'true';
const ENVIRONMENT = process.env.NEXT_PUBLIC_ENVIRONMENT || 'development';

/**
 * Check if batch processing is enabled
 * Requires both environment flag and browser capability
 */
export const isBatchEnabled = (): boolean => {
  // Production safety: require explicit enabling
  if (ENVIRONMENT === 'production' && !ENABLE_BATCH) {
    return false;
  }
  
  return ENABLE_BATCH;
};

/**
 * Check if folder drop functionality is enabled
 * Requires both environment flag and browser FileSystemEntry API support
 */
export const isFolderDropEnabled = (): boolean => {
  // Production safety: require explicit enabling
  if (ENVIRONMENT === 'production' && !ENABLE_FOLDER_DROP) {
    return false;
  }
  
  // Check browser capability
  if (!hasFolderDropSupport()) {
    return false;
  }
  
  return ENABLE_FOLDER_DROP;
};

/**
 * Check if browser supports folder drop (FileSystemEntry API)
 */
export const hasFolderDropSupport = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  // Check for DataTransferItem.webkitGetAsEntry support
  try {
    const dt = new DataTransfer();
    const item = dt.items[0];
    return item && typeof item.webkitGetAsEntry === 'function';
  } catch {
    // If DataTransfer is not available, check for webkitdirectory
    const input = document.createElement('input');
    return 'webkitdirectory' in input;
  }
};

/**
 * Check if browser supports webkitdirectory attribute
 */
export const hasWebkitDirectorySupport = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  const input = document.createElement('input');
  return 'webkitdirectory' in input;
};

/**
 * Debug logging (only in development)
 */
export const debugLog = (message: string, ...args: any[]): void => {
  if (DEBUG_MODE || ENVIRONMENT === 'development') {
    console.log(`[Feature Flags] ${message}`, ...args);
  }
};

/**
 * Get feature status for debugging
 */
export const getFeatureStatus = () => {
  return {
    batch: isBatchEnabled(),
    folderDrop: isFolderDropEnabled(),
    browserSupport: {
      webkitDirectory: hasWebkitDirectorySupport(),
      fileSystemEntry: hasFolderDropSupport(),
    },
    environment: ENVIRONMENT,
    flags: {
      ENABLE_BATCH,
      ENABLE_FOLDER_DROP,
      DEBUG_MODE,
    },
  };
};

// Development logging
if (typeof window !== 'undefined' && (DEBUG_MODE || ENVIRONMENT === 'development')) {
  debugLog('Feature flags initialized:', getFeatureStatus());
}