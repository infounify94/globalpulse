import React from 'react'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px', textAlign: 'center', fontFamily: 'sans-serif' }}>
          <h1 style={{ color: '#dc2626' }}>Something went wrong.</h1>
          <p style={{ color: '#64748b' }}>An unexpected error occurred in the application.</p>
          <pre style={{ 
            background: '#f1f5f9', padding: '16px', borderRadius: '8px', 
            textAlign: 'left', maxWidth: '800px', margin: '20px auto', overflow: 'auto'
          }}>
            {this.state.error?.toString()}
          </pre>
          <button 
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 20px', background: '#3b5bdb', color: 'white', 
              border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 600
            }}
          >
            Reload Application
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
