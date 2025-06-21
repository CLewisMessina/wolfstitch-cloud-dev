// frontend/src/components/ErrorBoundary.tsx
// React Error Boundary for handling React error #31 and other rendering errors - Fixed TypeScript Issues

'use client';

import React, { Component, ReactNode } from 'react';
import { AlertCircle, RefreshCw, Bug, FileX } from 'lucide-react';
import { ErrorBoundaryState } from '@/types/types';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackComponent?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    
    this.state = {
      hasError: false,
      errorId: this.generateErrorId()
    };
  }

  private generateErrorId(): string {
    return `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorId: `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error details for debugging
    console.error('ErrorBoundary caught an error:', error);
    console.error('Error info:', errorInfo);
    
    // Store error details for display
    this.setState({
      error,
      errorInfo: {
        componentStack: errorInfo.componentStack,
        errorBoundary: this.constructor.name,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent
      }
    });
    
    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
    
    // Log specific error types for analytics
    this.logErrorType(error);
  }

  private logErrorType(error: Error) {
    const errorMessage = error.message || '';
    
    if (errorMessage.includes('Minified React error #31')) {
      console.error('React Error #31 detected: Objects are not valid as React child');
      console.error('This usually means API response data is not properly normalized before rendering');
    } else if (errorMessage.includes('Cannot read property') || errorMessage.includes('Cannot read properties')) {
      console.error('Property access error detected - likely data structure issue');
    } else if (errorMessage.includes('fetch')) {
      console.error('Network/API error detected');
    } else if (errorMessage.includes('JSON')) {
      console.error('JSON parsing error detected');
    }
  }

  private getErrorTypeFromMessage(errorMessage: string): string {
    if (errorMessage.includes('Minified React error #31')) {
      return 'React Rendering Error';
    } else if (errorMessage.includes('Cannot read property') || errorMessage.includes('Cannot read properties')) {
      return 'Data Structure Error';
    } else if (errorMessage.includes('fetch') || errorMessage.includes('network')) {
      return 'Network Error';
    } else if (errorMessage.includes('JSON')) {
      return 'Data Parsing Error';
    } else {
      return 'Unknown Error';
    }
  }

  private getErrorDescription(error: Error): string {
    const errorMessage = error.message || '';
    
    if (errorMessage.includes('Minified React error #31')) {
      return 'The app tried to display data in an unexpected format. This usually happens when file processing returns data that needs to be converted before display.';
    } else if (errorMessage.includes('Cannot read property') || errorMessage.includes('Cannot read properties')) {
      return 'The app tried to access data that wasn\'t available or was in an unexpected format.';
    } else if (errorMessage.includes('fetch')) {
      return 'There was a problem communicating with the server during file processing.';
    } else if (errorMessage.includes('JSON')) {
      return 'The server response couldn\'t be processed correctly.';
    } else {
      return 'An unexpected error occurred during file processing or display.';
    }
  }

  private getSuggestions(error: Error): string[] {
    const errorMessage = error.message || '';
    
    if (errorMessage.includes('Minified React error #31')) {
      return [
        'Try uploading your file again',
        'If the problem persists, try a different file format',
        'Check that your file isn\'t corrupted'
      ];
    } else if (errorMessage.includes('Cannot read property') || errorMessage.includes('Cannot read properties')) {
      return [
        'Refresh the page and try again',
        'Try uploading a different file',
        'Clear your browser cache and reload'
      ];
    } else if (errorMessage.includes('fetch')) {
      return [
        'Check your internet connection',
        'Try again in a few moments',
        'If on mobile, try switching between WiFi and cellular data'
      ];
    } else {
      return [
        'Refresh the page and try again',
        'Try a different file',
        'Contact support if the problem continues'
      ];
    }
  }

  private handleRetry = () => {
    this.setState({
      hasError: false,
      error: undefined,
      errorInfo: undefined,
      errorId: this.generateErrorId()
    });
  };

  private handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback component if provided
      if (this.props.fallbackComponent) {
        return this.props.fallbackComponent;
      }

      // Default error UI
      const errorType = this.getErrorTypeFromMessage(this.state.error?.message || '');
      const errorDescription = this.getErrorDescription(this.state.error!);
      const suggestions = this.getSuggestions(this.state.error!);

      return (
        <div className="min-h-screen bg-gradient-to-br from-[#1a1b2e] via-[#16213e] to-[#0f172a] flex items-center justify-center p-4">
          <div className="max-w-md w-full">
            {/* Error Icon */}
            <div className="text-center mb-8">
              <div className="mx-auto w-20 h-20 bg-gradient-to-br from-red-500 to-red-600 rounded-full flex items-center justify-center shadow-xl mb-4">
                <AlertCircle className="w-10 h-10 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-white mb-2">
                Something went wrong
              </h1>
              <p className="text-gray-300 text-sm">
                Error ID: {this.state.errorId}
              </p>
            </div>

            {/* Error Details Card */}
            <div className="bg-[rgba(255,255,255,0.05)] backdrop-blur-sm rounded-2xl shadow-xl border border-gray-700 p-6 mb-6">
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-white mb-2 flex items-center">
                  <Bug className="w-5 h-5 mr-2 text-red-400" />
                  {errorType}
                </h3>
                <p className="text-gray-300 text-sm leading-relaxed">
                  {errorDescription}
                </p>
              </div>

              {/* Suggestions */}
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-white mb-2">
                  Try these solutions:
                </h4>
                <ul className="text-sm text-gray-300 space-y-1">
                  {suggestions.map((suggestion, index) => (
                    <li key={index} className="flex items-start">
                      <span className="text-[#4ECDC4] mr-2">•</span>
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Technical Details (expandable) */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <details className="mt-4">
                  <summary className="text-sm font-semibold text-gray-400 cursor-pointer hover:text-white">
                    Technical Details (Development)
                  </summary>
                  <div className="mt-2 p-3 bg-gray-900 rounded-lg border border-gray-600">
                    <p className="text-xs text-red-300 font-mono break-all">
                      {this.state.error.message}
                    </p>
                    {this.state.error.stack && (
                      <pre className="text-xs text-gray-400 mt-2 overflow-auto max-h-32">
                        {this.state.error.stack}
                      </pre>
                    )}
                  </div>
                </details>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={this.handleRetry}
                className="flex-1 inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-[#4ECDC4] to-[#44B8B5] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(78,205,196,0.3)] transition-all duration-300 transform hover:scale-105"
              >
                <RefreshCw className="w-5 h-5 mr-2" />
                Try Again
              </button>
              
              <button
                onClick={this.handleReload}
                className="flex-1 inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-[#FF6B47] to-[#E85555] text-white rounded-xl font-semibold hover:shadow-lg hover:shadow-[rgba(255,107,71,0.3)] transition-all duration-300 transform hover:scale-105"
              >
                <FileX className="w-5 h-5 mr-2" />
                Reload Page
              </button>
            </div>

            {/* Help Text */}
            <div className="text-center mt-6">
              <p className="text-sm text-gray-400">
                If this problem continues, please contact support with Error ID: {this.state.errorId}
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
