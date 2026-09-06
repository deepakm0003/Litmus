import { HashRouter, Route, Routes } from 'react-router-dom';
import { Shell } from './components/Shell';
import { ToastProvider } from './components/Toast';
import ErrorBoundary from './components/ErrorBoundary';
import Home from './routes/Home';
import Console from './components/console/Console';
import { Pricing, Docs, Security, Company, Changelog } from './routes/Pages';

/**
 * HashRouter rather than BrowserRouter on purpose: the whole app is also
 * shipped as one static HTML file (served by the backend at /console, and
 * published as an Artifact), where there is no server to rewrite deep paths.
 * Hash routing works identically in both environments.
 */
export default function App() {
  return (
    <ToastProvider>
      <ErrorBoundary>
      <HashRouter>
        <Shell>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/console" element={<Console />} />
            <Route path="/pricing" element={<Pricing />} />
            <Route path="/docs" element={<Docs />} />
            <Route path="/security" element={<Security />} />
            <Route path="/company" element={<Company />} />
            <Route path="/changelog" element={<Changelog />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </Shell>
      </HashRouter>
      </ErrorBoundary>
    </ToastProvider>
  );
}
