import { Component } from 'react';
import '../styles/components.css';
import '../styles/panels.css';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
    };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error) {
    if (typeof this.props.onError === 'function') {
      this.props.onError(error);
    }
  }

  componentDidUpdate(prevProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({
        hasError: false,
        error: null,
      });
    }
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
    });
  };

  render() {
    const { children, fallback } = this.props;

    if (this.state.hasError) {
      if (typeof fallback === 'function') {
        return fallback({
          retry: this.handleRetry,
          error: this.state.error,
        });
      }

      if (fallback) {
        return fallback;
      }

      return (
        <section className="panel panel-error-state" role="alert">
          <div className="empty-state empty-state-compact">
            <div className="empty-grid" />
            <h3>Something went wrong</h3>
            <p>{this.state.error?.message || 'An unexpected error occurred.'}</p>
            <button type="button" className="secondary-button" onClick={this.handleRetry}>
              Retry
            </button>
          </div>
        </section>
      );
    }

    return children;
  }
}

export default ErrorBoundary;
