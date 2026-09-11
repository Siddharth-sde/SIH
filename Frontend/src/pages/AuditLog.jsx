import { useState, useEffect } from 'react';
import { getAuditLogs } from '../api/api';
import { Spinner, Badge, EmptyState } from '../components/UI';
import { useToast } from '../components/Toast';

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(50);
  const toast = useToast();

  const load = async (lim) => {
    setLoading(true);
    try {
      const data = await getAuditLogs(lim);
      setLogs(data.logs || []);
    } catch {
      toast('Failed to load audit logs', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(limit);
  }, [limit]);

  const exportCSV = () => {
    if (!logs.length) {
      toast('No audit logs to export', 'warning');
      return;
    }
    const headers = ['id', 'material_code', 'action', 'performed_by', 'notes', 'timestamp'];
    const rows = logs.map(l =>
      headers.map(h => `"${(l[h] !== undefined && l[h] !== null ? String(l[h]) : '').replace(/"/g, '""')}"`).join(',')
    );
    const blob = new Blob([headers.join(',') + '\n' + rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_logs_${logs.length}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast(`Exported ${logs.length} audit logs to CSV`, 'success');
  };

  return (
    <div>
      <div className="page-header">
        <h1>Governance & Audit Trail</h1>
        <p>Immutable record of all human approvals, rejections, overrides, and catalog modifications</p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="text-sm text-muted">Showing latest <strong>{logs.length}</strong> governance actions</div>
          <div className="input-row">
            <select className="input" style={{ width: 120 }} value={limit} onChange={e => setLimit(Number(e.target.value))}>
              {[25, 50, 100, 200].map(n => <option key={n} value={n}>{n} rows</option>)}
            </select>
            <button className="btn btn-ghost btn-sm" onClick={exportCSV} title="Export audit trail to CSV">
              ⬇ Export CSV
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => load(limit)}>
              ↺ Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: 'center' }}><Spinner size={32} /></div>
        ) : logs.length === 0 ? (
          <EmptyState title="No audit entries recorded" desc="Actions performed on materials (e.g. approvals, rejections) will appear here." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Material Code</th>
                  <th>Action</th>
                  <th>Actor / User</th>
                  <th>Notes & Rationalization</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(l => (
                  <tr key={l.id}>
                    <td className="text-sm text-muted" style={{ whiteSpace: 'nowrap' }}>
                      {l.timestamp ? new Date(l.timestamp).toLocaleString('en-IN') : '—'}
                    </td>
                    <td className="font-mono text-sm" style={{ fontWeight: 600 }}>
                      {l.material_code || '—'}
                    </td>
                    <td>
                      <Badge color={l.action === 'APPROVE' || l.action === 'AUTO_APPROVED' ? 'green' : l.action === 'REJECT' ? 'red' : 'blue'}>
                        {l.action}
                      </Badge>
                    </td>
                    <td className="text-sm">{l.performed_by || 'system'}</td>
                    <td className="text-sm text-muted">{l.notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
