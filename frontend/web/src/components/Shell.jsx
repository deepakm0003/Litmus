import { Link, NavLink, useLocation } from 'react-router-dom';
import { useEffect } from 'react';

const LINKS = [
  { to: '/', label: 'Product', end: true },
  { to: '/pricing', label: 'Pricing' },
  { to: '/docs', label: 'Docs' },
  { to: '/security', label: 'Security' },
  { to: '/company', label: 'Company' },
];

/** Shared chrome. Scroll resets on navigation so a route change starts at the top. */
export function Shell({ children }) {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);

  return (
    <>
      <header className="nav">
        <div className="nav-row">
          <Link className="brand" to="/">Litmus<span className="dot">.</span></Link>
          <nav className="nav-links">
            {LINKS.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end}
                className={({ isActive }) => (isActive ? 'active' : undefined)}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          <Link className="btn btn-primary btn-sm" to="/console">
            Open console <span className="arw">&#8594;</span>
          </Link>
        </div>
      </header>
      <main>{children}</main>
      <Footer />
    </>
  );
}

function Footer() {
  return (
    <footer>
      <div className="wrap foot-grid">
        <div>
          <div className="foot-brand">Litmus<span className="dot">.</span></div>
          <p className="foot-line">Every fake has a tell.</p>
          <p className="foot-small">
            Pre-pilot. Figures on this site are measured or cited, never projected.
          </p>
        </div>
        <FootCol title="Product" links={[
          ['/', 'Overview'], ['/console', 'Console'], ['/pricing', 'Pricing'],
        ]} />
        <FootCol title="Engineering" links={[
          ['/docs', 'API reference'], ['/security', 'Model card'], ['/changelog', 'Changelog'],
        ]} />
        <FootCol title="Company" links={[
          ['/company', 'About'], ['/company', 'Roadmap'], ['/security', 'Security'],
        ]} />
      </div>
      <div className="wrap foot-base">
        <span>&copy; 2026 Litmus</span>
        <span>Built for the TVS Credit E.P.I.C 8.0 IT Challenge</span>
      </div>
    </footer>
  );
}

function FootCol({ title, links }) {
  return (
    <div>
      <div className="foot-col-t">{title}</div>
      <ul className="foot-col">
        {links.map(([to, label]) => (
          <li key={label}><Link to={to}>{label}</Link></li>
        ))}
      </ul>
    </div>
  );
}
