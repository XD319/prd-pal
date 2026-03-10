import { Component } from 'react';
import '../styles/components.css';
import '../styles/panels.css';

class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
    };
  }

  static getDerivedStateFromError() {
    return {
      hasError: true,
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
      });
    }
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
    });
  };

  render() {
    const { children, fallback } = this.props;

    if (this.state.hasError) {
      if (typeof fallback === 'function') {
        return fallback({
          retry: this.handleRetry,
        });
      }

      return fallback ?? null;
    }

    return children;
  }
}

export default ErrorBoundary;
