/**
 * Configuration utilities for the application
 */

/**
 * Get the base backend URL from environment variables or use default
 */
function getBaseUrl(): string {
  // Check if we're in browser or server
  if (typeof window !== 'undefined') {
    // Browser environment
    return process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:4000';
  }
  
  // Server environment
  return process.env.NEXT_PUBLIC_BACKEND_URL || process.env.BACKEND_URL || 'http://localhost:4000';
}

/**
 * Get the full API endpoint URL
 */
export function getApiUrl(path: string): string {
  const baseUrl = getBaseUrl();
  const cleanPath = path.startsWith('/') ? path : `/${path}`;
  return `${baseUrl}${cleanPath}`;
}

/**
 * Get the full API endpoint URL (alias for backward compatibility)
 */
export function getApiEndpoint(path: string): string {
  return getApiUrl(path);
}
