import React from 'react';

interface ErrorBoundaryState { error?: Error }

export class ErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = {};
  static getDerivedStateFromError(error: Error): ErrorBoundaryState { return { error }; }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Placeholder: could send to logging infra / correlation ID pipeline
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', error, info);
  }
  render() {
    if (this.state.error) {
      return (
        <div role="alert" className="p-4 border border-red-700 bg-red-900/30 rounded text-sm">
          <p className="font-semibold mb-1">Something went wrong.</p>
          <pre className="text-xs whitespace-pre-wrap">{this.state.error.message}</pre>
          <button onClick={() => this.setState({ error: undefined })} className="mt-2 px-2 py-1 bg-neutral-800 border border-neutral-600 rounded text-xs">Reset</button>
        </div>
      );
    }
    return this.props.children as React.ReactElement;
  }
}

export default ErrorBoundary;
