// frontend/src/lib/feature-flags.ts
/**
 * Feature flag utilities for progressive feature rollout
 * Centralizes all feature flag logic for the application
 */

// Feature flag configuration interface
export interface FeatureFlags {
  batchProcessing: boolean;
  folderDrop: boolean;
  maxBatchSize: number;
  maxBatchSizeMB: number;
  debugMode: boolean;
}

// Get all feature flags from environment
export const getFeatureFlags = (): FeatureFlags => {
  return {
    batchProcessing: process.env.NEXT_PUBLIC_ENABLE_BATCH === 'true',
    folderDrop: process.env.NEXT_PUBLIC_ENABLE_FOLDER_DROP === 'true',
    maxBatchSize: parseInt(process.env.NEXT_PUBLIC_MAX_BATCH_SIZE || '100', 10),
    maxBatchSizeMB: parseInt(process.env.NEXT_PUBLIC_MAX_BATCH_SIZE_MB || '500', 10),
    debugMode: process.env.NEXT_PUBLIC_DEBUG_MODE === 'true'
  };
};

// Individual feature flag getters for convenience
// Default to false for production safety
export const isBatchEnabled = (): boolean => {
  // Only enable if explicitly set to true AND not in production with flag disabled
  const enabled = process.env.NEXT_PUBLIC_ENABLE_BATCH === 'true';
  const isProd = process.env.NEXT_PUBLIC_ENVIRONMENT === 'production';
  
  if (isProd && !enabled) {
    return false; // Production safety: require explicit enabling
  }
  
  return enabled;
};

export const isFolderDropEnabled = (): boolean => {
  // Only enable if explicitly set to true AND not in production with flag disabled  
  const enabled = process.env.NEXT_PUBLIC_ENABLE_FOLDER_DROP === 'true';
  const isProd = process.env.NEXT_PUBLIC_ENVIRONMENT === 'production';
  
  if (isProd && !enabled) {
    return false; // Production safety: require explicit enabling
  }
  
  return enabled;
};

export const isDebugMode = (): boolean => {
  return process.env.NEXT_PUBLIC_DEBUG_MODE === 'true';
};

export const getMaxBatchSize = (): number => {
  return parseInt(process.env.NEXT_PUBLIC_MAX_BATCH_SIZE || '100', 10);
};

export const getMaxBatchSizeMB = (): number => {
  return parseInt(process.env.NEXT_PUBLIC_MAX_BATCH_SIZE_MB || '500', 10);
};

// Runtime feature detection
export const checkBrowserSupport = () => {
  const support = {
    webkitdirectory: 'webkitdirectory' in document.createElement('input'),
    fileSystemAccess: 'showDirectoryPicker' in window,
    dragDropFolders: true, // Most modern browsers support this
    asyncIterators: typeof Symbol?.asyncIterator !== 'undefined'
  };

  return support;
};

// Feature flag debugging helper
export const logFeatureFlags = () => {
  if (!isDebugMode()) return;

  const flags = getFeatureFlags();
  const support = checkBrowserSupport();

  console.group('🏗️ Wolfstitch Feature Flags');
  console.table(flags);
  console.group('🌐 Browser Support');
  console.table(support);
  console.groupEnd();
  console.groupEnd();
};

// Initialize window global for debugging
if (typeof window !== 'undefined' && isDebugMode()) {
  window.__WOLFSTITCH_DEBUG__ = {
    logFileTraversal: true,
    logBatchProgress: true,
    simulateSlowNetwork: false
  };
}

export default {
  getFeatureFlags,
  isBatchEnabled,
  isFolderDropEnabled,
  isDebugMode,
  getMaxBatchSize,
  getMaxBatchSizeMB,
  checkBrowserSupport,
  logFeatureFlags
};