import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('Frontend render failed.', error, info);
  }

  render() {
    if (this.state.error) {
      const message = this.state.error?.stack ?? String(this.state.error);
      return (
        <div className="boot-error-shell">
          <div className="boot-error-card">
            <p className="boot-error-kicker">Frontend boot error</p>
            <h1>Review workspace failed to render</h1>
            <pre>{message}</pre>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>,
);
