import { useEffect } from 'react';
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar';
import { useTheme } from './hooks/useTheme';
import HomePage from './pages/HomePage';
import RunDetailsPage from './pages/RunDetailsPage';
import './styles/layout.css';

function AppLayout() {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    if (location.hash) {
      const targetId = location.hash.slice(1);
      window.requestAnimationFrame(() => {
        document.getElementById(targetId)?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      });
      return;
    }

    window.scrollTo({
      top: 0,
      left: 0,
      behavior: 'auto',
    });
  }, [location.pathname, location.hash]);

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />
      <Navbar theme={theme} onToggleTheme={toggleTheme} />

      <div className="page-shell">
        <Outlet />
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="run/:runId" element={<RunDetailsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
