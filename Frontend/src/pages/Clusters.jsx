import { useState, useEffect } from 'react';
import { getClusters } from '../api/api';
import { Spinner, Badge, EmptyState } from '../components/UI';
import { useToast } from '../components/Toast';

function ClusterCard({ cluster }) {
  const [open, setOpen] = useState(false);
  const prices = cluster.materials.map(m => m.unit_price).filter(p => p > 0);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const spread = prices.length > 1 ? ((maxP - minP) / minP * 100).toFixed(1) : null;

  return (
    <div className="cluster-card">
      <div className="cluster-header" onClick={() => setOpen(o => !o)}>
        <div>
          <h3>{cluster.cnmc}</h3>
          <div style={{ display: 'flex', gap: 8, marginTop: 4, flexWrap: 'wrap' }}>
            <Badge color="blue">{cluster.total_duplicates} variants</Badge>
            {cluster.cpses_involved.map(c => <Badge key={c} color="gray">{c}</Badge>)}
            {spread && parseFloat(spread) > 5 && (
              <Badge color="red">⚠ {spread}% price spread</Badge>
            )}
          </div>
        </div>
        <span style={{ color: 'var(--text-muted)', fontSize: 18 }}>{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="cluster-members">
          <div className="cluster-member" style={{ fontWeight: 600, fontSize: 11, color: 'var(--text-muted)', background: 'transparent', padding: '4px 10px' }}>
            <span>CPSE</span>
            <span>Description</span>
            <span>UOM</span>
            <span style={{ textAlign: 'right' }}>Unit Price</span>
          </div>
          {cluster.materials.map((m, i) => (
            <div className="cluster-member" key={i} style={{ background: m.unit_price === minP && prices.length > 1 ? 'var(--success-light)' : m.unit_price === maxP && prices.length > 1 ? 'var(--danger-light)' : 'var(--bg)' }}>
              <div>
                <div className="cluster-member-code">{m.cpse}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{m.code}</div>
              </div>
              <div className="cluster-member-desc" title={m.description}>{m.description}</div>
              <div>{m.uom}</div>
              <div className="cluster-member-price">
                {m.unit_price > 0 ? `₹${m.unit_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
              </div>
            </div>
          ))}
          {prices.length > 1 && (
            <div style={{ padding: '8px 10px', fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg)', borderRadius: 6 }}>
              Price range: ₹{minP.toLocaleString('en-IN')} – ₹{maxP.toLocaleString('en-IN')}
              {spread && ` · Spread: ${spread}% · Potential saving per unit: ₹${(maxP - minP).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Clusters() {
  const [clusters, setClusters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(25);
  const toast = useToast();

  const load = async (lim) => {
    setLoading(true);
    try {
      const data = await getClusters(lim);
      setClusters(data);
    } catch {
      toast('Failed to load clusters', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(limit); }, [limit]);

  const totalDupes = clusters.reduce((s, c) => s + c.total_duplicates, 0);

  return (
    <div>
      <div className="page-header">
        <h1>Duplicate Clusters</h1>
        <p>Auto-grouped duplicate materials across CPSEs sharing the same CNMC code</p>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 20 }}>
        <div className="kpi-card">
          <div className="kpi-icon blue"><span style={{ fontSize: 20 }}>◎</span></div>
          <div><div className="kpi-value">{clusters.length}</div><div className="kpi-label">Clusters Shown</div></div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon red"><span style={{ fontSize: 20 }}>♻</span></div>
          <div><div className="kpi-value">{totalDupes.toLocaleString()}</div><div className="kpi-label">Total Duplicate Items</div></div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon yellow"><span style={{ fontSize: 20 }}>⚠</span></div>
          <div>
            <div className="kpi-value">{clusters.filter(c => {
              const prices = c.materials.map(m => m.unit_price).filter(p => p > 0);
              if (prices.length < 2) return false;
              const spread = (Math.max(...prices) - Math.min(...prices)) / Math.min(...prices) * 100;
              return spread > 10;
            }).length}</div>
            <div className="kpi-label">High Price Spread ({`>`}10%)</div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div className="text-sm text-muted">Showing top <strong>{clusters.length}</strong> duplicate clusters</div>
          <div className="input-row">
            <select className="input" style={{ width: 120 }} value={limit} onChange={e => setLimit(Number(e.target.value))}>
              {[10, 25, 50, 100].map(n => <option key={n}>{n}</option>)}
            </select>
            <button className="btn btn-ghost btn-sm" onClick={() => load(limit)}>↺ Refresh</button>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: 'center' }}><Spinner size={32} /></div>
      ) : clusters.length === 0 ? (
        <EmptyState title="No duplicate clusters found" desc="Upload data with CNMC codes to see clustering results." />
      ) : (
        <div>
          {clusters.map(c => <ClusterCard key={c.cnmc} cluster={c} />)}
        </div>
      )}
    </div>
  );
}
