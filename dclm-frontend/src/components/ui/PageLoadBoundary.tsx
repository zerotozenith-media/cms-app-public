import { Component } from 'react';
import type { ReactNode } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * A page that cannot be downloaded (no connection, or the app was updated
 * and reloading did not help) says so and offers to try again, instead of
 * leaving a blank screen.
 */
class Boundary extends Component<{ children: ReactNode; at: string }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidUpdate(prev: { at: string }) {
    if (prev.at !== this.props.at && this.state.failed) this.setState({ failed: false });
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div className="card" role="alert" style={{ maxWidth: 520 }}>
        <h3 style={{ marginBottom: 6 }}>This page could not load</h3>
        <p className="muted" style={{ marginBottom: 12 }}>
          The connection may have dropped, or the app has just been updated. Press Try again to load the latest version.
        </p>
        <button type="button" className="btn" onClick={() => window.location.reload()}>Try again</button>
      </div>
    );
  }
}

export function PageLoadBoundary({ children }: { children: ReactNode }) {
  const at = useLocation().pathname;
  return <Boundary at={at}>{children}</Boundary>;
}
