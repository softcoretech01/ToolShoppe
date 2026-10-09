import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider, App as AntApp } from 'antd'

import '@fontsource/inter/400.css'
import '@fontsource/inter/500.css'
import '@fontsource/inter/600.css'
import '@fontsource/inter/700.css'

import App from './app/App.jsx'
import { AppProvider } from './store/AppContext.jsx'
import { antdTheme } from './theme/antdTheme.js'
import './styles/global.css'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled app error:', error, errorInfo)
    this.setState({ errorInfo })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, maxWidth: 800, margin: '40px auto', fontFamily: 'system-ui, sans-serif', background: '#fff', borderRadius: 12, border: '1px solid #e2e8f0', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
          <h2 style={{ color: '#dc2626', marginTop: 0 }}>Something went wrong</h2>
          <p style={{ color: '#475569' }}>An unexpected error occurred while rendering the page.</p>
          <pre style={{ background: '#f8fafc', padding: 12, borderRadius: 8, fontSize: 12, overflowX: 'auto', color: '#1e293b', maxHeight: 300 }}>
            {this.state.error?.message || String(this.state.error)}
            {'\n\n'}
            {this.state.error?.stack}
            {this.state.errorInfo?.componentStack ? '\n\nComponent Stack:' + this.state.errorInfo.componentStack : ''}
          </pre>
          <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
            <button
              onClick={() => {
                localStorage.clear()
                window.location.reload()
              }}
              style={{ padding: '8px 16px', background: '#4f46e5', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}
            >
              Reset Cache & Reload
            </button>
            <button
              onClick={() => window.location.reload()}
              style={{ padding: '8px 16px', background: '#f1f5f9', color: '#334155', border: '1px solid #cbd5e1', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}
            >
              Reload Page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ConfigProvider theme={antdTheme}>
        <AntApp message={{ maxCount: 3, duration: 3 }}>
          <BrowserRouter>
            <AppProvider>
              <App />
            </AppProvider>
          </BrowserRouter>
        </AntApp>
      </ConfigProvider>
    </ErrorBoundary>
  </React.StrictMode>
)
