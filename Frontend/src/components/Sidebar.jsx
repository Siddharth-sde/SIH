export function Sidebar({ page, setPage, mlOnline, backendOnline }) {
  const links = [
    { section: 'Overview' },
    { id: 'dashboard', label: 'Dashboard', icon: '▦' },
    { section: 'Data Management' },
    { id: 'upload', label: 'Upload Data', icon: '⬆' },
    { id: 'materials', label: 'Materials Browser', icon: '☰' },
    { section: 'Harmonization' },
    { id: 'clusters', label: 'Duplicate Clusters', icon: '◎' },
    { id: 'ai-match', label: 'AI Matching', icon: '✦' },
    { section: 'Analytics' },
    { id: 'analytics', label: 'Analytics & KPIs', icon: '📊' },
    { section: 'Governance' },
    { id: 'audit', label: 'Audit Trail', icon: '📋' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        NMM Platform
        <span>Smart India Hackathon 2026</span>
      </div>
      {links.map((l, i) =>
        l.section ? (
          <div key={i} className="sidebar-section">{l.section}</div>
        ) : (
          <button
            key={l.id}
            className={`sidebar-link ${page === l.id ? 'active' : ''}`}
            onClick={() => setPage(l.id)}
          >
            <span style={{ fontSize: 14 }}>{l.icon}</span>
            {l.label}
          </button>
        )
      )}
      <div className="sidebar-status">
        <div className={`status-dot ${backendOnline ? '' : 'offline'}`} style={{ fontSize: 11 }}>
          Backend {backendOnline ? 'Online' : 'Offline'}
        </div>
        <div className={`status-dot ${mlOnline ? '' : 'offline'}`} style={{ fontSize: 11, marginTop: 6 }}>
          ML Engine {mlOnline ? 'Online' : 'Offline'}
        </div>
      </div>
    </aside>
  );
}
