import { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { ToastProvider } from './components/Toast';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Materials from './pages/Materials';
import Clusters from './pages/Clusters';
import AIMatch from './pages/AIMatch';
import Analytics from './pages/Analytics';
import './index.css';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
const ML_URL = import.meta.env.VITE_ML_URL || 'http://localhost:8001';

function App() {
  const [page, setPage] = useState('dashboard');
  const [backendOnline, setBackendOnline] = useState(false);
  const [mlOnline, setMlOnline] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        await fetch(`${BACKEND_URL}/`);
        setBackendOnline(true);
      } catch { setBackendOnline(false); }
      try {
        const r = await fetch(`${ML_URL}/health`);
        const j = await r.json();
        setMlOnline(j.status === 'healthy');
      } catch { setMlOnline(false); }
    };
    check();
    const t = setInterval(check, 15000);
    return () => clearInterval(t);
  }, []);

  const pages = { dashboard: Dashboard, upload: Upload, materials: Materials, clusters: Clusters, 'ai-match': AIMatch, analytics: Analytics };
  const PageComponent = pages[page] || Dashboard;

  return (
    <ToastProvider>
      <div className="layout">
        <Sidebar page={page} setPage={setPage} backendOnline={backendOnline} mlOnline={mlOnline} />
        <main className="main-content">
          <PageComponent />
        </main>
      </div>
    </ToastProvider>
  );
}

export default App;
