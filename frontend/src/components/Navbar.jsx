import { Link, NavLink, useLocation } from 'react-router-dom';

function Navbar() {
  const location = useLocation();
  const isHistoryActive = location.pathname === '/' && location.hash === '#history';

  return (
    <header className="navbar-shell">
      <div className="navbar">
        <NavLink to="/" end className="navbar-brand" aria-label="Review Workspace home">
          <span className="navbar-logo" aria-hidden="true">RW</span>
          <span className="navbar-brand-copy">
            <strong>Review Workspace</strong>
            <small>Requirement review cockpit</small>
          </span>
        </NavLink>

        <div className="navbar-actions">
          <nav className="navbar-links" aria-label="Primary">
            <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? ' nav-link-active' : ''}`}>
              Home
            </NavLink>
            <Link
              to={{ pathname: '/', hash: '#history' }}
              className={`nav-link${isHistoryActive ? ' nav-link-active' : ''}`}
            >
              History
            </Link>
          </nav>

          <div className="navbar-avatar-slot" aria-label="Reserved user profile space" role="img">
            <span>U</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Navbar;

