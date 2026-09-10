export function Spinner({ size = 20 }) {
  return <span className="spinner" style={{ width: size, height: size }} />;
}

export function Badge({ children, color = 'gray' }) {
  return <span className={`badge badge-${color}`}>{children}</span>;
}

export function StatusBadge({ status }) {
  const map = {
    ACTIVE: 'green',
    APPROVED: 'green',
    PENDING_REVIEW: 'yellow',
    REJECTED: 'red',
    PENDING_HARMONIZATION: 'gray',
  };
  return <Badge color={map[status] || 'gray'}>{status?.replace(/_/g, ' ')}</Badge>;
}

export function Card({ children, className = '' }) {
  return <div className={`card ${className}`}>{children}</div>;
}

export function EmptyState({ icon, title, desc }) {
  return (
    <div className="empty-state">
      {icon && <div>{icon}</div>}
      <h3>{title}</h3>
      {desc && <p className="text-sm">{desc}</p>}
    </div>
  );
}
