import { Component } from 'react';

/**
 * Catches render-time crashes so a bug shows a readable panel instead of a
 * blank white page.
 *
 * Added after exactly that failure: the API returned an HTML page with a 200
 * status, the client accepted it as data, and the first `.map()` over an
 * undefined field unmounted the whole tree. The underlying cause is fixed in
 * lib/api.js, but a console that goes blank in front of an audience is bad
 * enough that it deserves a floor under it regardless.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Keep the detail in the console for whoever is debugging.
    console.error('Litmus UI crashed:', error, info?.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="wrap crash">
        <div className="crash-card">
          <div className="crash-tag">Interface error</div>
          <h2>This panel failed to render.</h2>
          <p>
            Something threw while drawing the page. The rest of the app is fine — reload, or
            switch tabs, to continue.
          </p>
          <pre className="crash-detail">{String(error?.message || error)}</pre>
          <div className="row-actions">
            <button className="btn btn-primary" onClick={() => this.setState({ error: null })}>
              Try again
            </button>
            <button className="btn btn-ghost" onClick={() => window.location.reload()}>
              Reload the page
            </button>
          </div>
        </div>
      </div>
    );
  }
}
