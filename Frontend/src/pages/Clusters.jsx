import { useState, useEffect, useCallback, useMemo } from 'react';
import { getClusters } from '../api/api';
import { Spinner, Badge, EmptyState } from '../components/UI';
import { useToast } from '../components/Toast';
import { formatINR, formatNumber } from '../utils/formatters';

function ClusterCard({ cluster, defaultOpen = false }) {
  const [userToggled, setUserToggled] = useState(null);
  const open = userToggled !== null ? userToggled : defaultOpen;

  const toggleOpen = () => {
    setUserToggled(prev => (prev !== null ? !prev : !defaultOpen));
  };

  const materials = cluster.materials || [];
  const prices = materials.map(m => m.unit_price).filter(p => typeof p === 'number' && p > 0);
  const minP = prices.length > 0 ? Math.min(...prices) : 0;
  const maxP = prices.length > 0 ? Math.max(...prices) : 0;
  const spread = (prices.length > 1 && minP > 0) ? (((maxP - minP) / minP) * 100).toFixed(1) : null;

  return (
    <div className="cluster-card">
      <div className="cluster-header" onClick={toggleOpen}>
        <div>
          <h3>{cluster.cnmc}</h3>
          <div style={{ display: 'flex', gap: 8, marginTop: 4, flexWrap: 'wrap', alignItems: 'center' }}>
            <Badge color="blue">{cluster.total_duplicates ?? cluster.material_count ?? materials.length} variants</Badge>
            {(cluster.cpses_involved || []).map(c => <Badge key={c} color="gray">{c}</Badge>)}
            {spread && parseFloat(spread) > 5 && (
              <Badge color="red">⚠ {spread}% price spread</Badge>
            )}
            {cluster.canonical_name && (
              <span className="text-sm text-muted" style={{ fontStyle: 'italic', maxWidth: 380, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {cluster.canonical_name}
              </span>
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
          {materials.map((m, i) => (
            <div className="cluster-member" key={i} style={{ background: m.unit_price === minP && prices.length > 1 ? 'var(--success-light)' : m.unit_price === maxP && prices.length > 1 ? 'var(--danger-light)' : 'var(--bg)' }}>
              <div>
                <div className="cluster-member-code">{m.cpse}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{m.code}</div>
              </div>
              <div className="cluster-member-desc" title={m.description}>{m.description}</div>
              <div>{m.uom}</div>
              <div className="cluster-member-price">
                {m.unit_price > 0 ? formatINR(m.unit_price) : '—'}
              </div>
            </div>
          ))}
          {prices.length > 1 && (
            <div style={{ padding: '8px 10px', fontSize: 12, color: 'var(--text-muted)', background: 'var(--bg)', borderRadius: 6, display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
              <span>
                Price range: {formatINR(minP)} – {formatINR(maxP)}
                {spread && ` · Max Spread: ${spread}%`}
              </span>
              <span style={{ color: 'var(--success)', fontWeight: 600 }}>
                Arbitrage per unit: {formatINR(maxP - minP)}
              </span>
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
  const [searchFilter, setSearchFilter] = useState('');
  const [allOpen, setAllOpen] = useState(false);
  const toast = useToast();

  const load = useCallback(async (lim) => {
    setLoading(true);
    try {
      const data = await getClusters(lim);
      const list = Array.isArray(data) ? data : (data?.clusters || []);
      setClusters(list);
    } catch {
      toast('Failed to load clusters', 'error');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(limit); }, [limit, load]);

  const clusterList = Array.isArray(clusters) ? clusters : [];

  const filteredClusters = useMemo(() => {
    if (!searchFilter.trim()) return clusterList;
    const q = searchFilter.toLowerCase().trim();
    return clusterList.filter(c => {
      const cnmcMatch = (c.cnmc || '').toLowerCase().includes(q);
      const nameMatch = (c.canonical_name || '').toLowerCase().includes(q);
      const cpseMatch = (c.cpses_involved || []).some(cp => cp.toLowerCase().includes(q));
      const matMatch = (c.materials || []).some(m => (m.description || '').toLowerCase().includes(q) || (m.code || '').toLowerCase().includes(q));
      return cnmcMatch || nameMatch || cpseMatch || matMatch;
    });
  }, [clusterList, searchFilter]);

  const totalDupes = filteredClusters.reduce((s, c) => s + (c.total_duplicates ?? c.material_count ?? (c.materials?.length || 0)), 0);

  const exportCSV = () => {
    if (!filteredClusters.length) {
      toast('No clusters to export', 'warning');
      return;
    }
    const headers = ['cnmc_code', 'canonical_name', 'material_code', 'cpse', 'description', 'uom', 'unit_price', 'stock_qty'];
    const rows = [];
    filteredClusters.forEach(c => {
      (c.materials || []).forEach(m => {
        rows.push([
          `"${c.cnmc || ''}"`,
          `"${(c.canonical_name || '').replace(/"/g, '""')}"`,
          `"${m.code || ''}"`,
          `"${m.cpse || ''}"`,
          `"${(m.description || '').replace(/"/g, '""')}"`,
          `"${m.uom || ''}"`,
          `"${m.unit_price || 0}"`,
          `"${m.stock_qty || 0}"`
        ].join(','));
      });
    });
    const blob = new Blob([headers.join(',') + '\n' + rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `clusters_export_${filteredClusters.length}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast(`Exported ${rows.length} items from ${filteredClusters.length} clusters to CSV`, 'success');
  };

  return (
    <div>
      <div className="page-header">
        <h1>Duplicate Clusters</h1>
        <p>Auto-grouped duplicate materials across CPSEs sharing the same CNMC code</p>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 20 }}>
        <div className="kpi-card">
          <div className="kpi-icon blue"><span style={{ fontSize: 20 }}>◎</span></div>
          <div><div className="kpi-value">{filteredClusters.length}</div><div className="kpi-label">Clusters Shown</div></div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon red"><span style={{ fontSize: 20 }}>♻</span></div>
          <div><div className="kpi-value">{formatNumber(totalDupes)}</div><div className="kpi-label">Total Duplicate Items</div></div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon yellow"><span style={{ fontSize: 20 }}>⚠</span></div>
          <div>
            <div className="kpi-value">{filteredClusters.filter(c => {
              const prices = (c.materials || []).map(m => m.unit_price).filter(p => typeof p === 'number' && p > 0);
              if (prices.length < 2) return false;
              const minP = Math.min(...prices);
              if (minP <= 0) return false;
              const maxP = Math.max(...prices);
              const spread = (maxP - minP) / minP * 100;
              return spread > 10;
            }).length}</div>
            <div className="kpi-label">High Price Spread ({`>`}10%)</div>
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div className="search-wrap" style={{ flex: 1, minWidth: 260 }}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M9 3a6 6 0 100 12A6 6 0 009 3zM2 9a7 7 0 1112.452 4.391l3.328 3.329a1 1 0 11-1.414 1.414l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd"/></svg>
            <input
              className="input"
              placeholder="Filter by CNMC, CPSE, or description…"
              value={searchFilter}
              onChange={e => setSearchFilter(e.target.value)}
            />
          </div>
          <div className="input-row">
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => setAllOpen(prev => !prev)}
              title="Expand or collapse all cluster cards"
            >
              {allOpen ? '▲ Collapse All' : '▼ Expand All'}
            </button>
            <select className="input" style={{ width: 120 }} value={limit} onChange={e => setLimit(Number(e.target.value))}>
              {[10, 25, 50, 100, 250].map(n => <option key={n} value={n}>{n} clusters</option>)}
            </select>
            <button className="btn btn-ghost btn-sm" onClick={exportCSV} title="Export clusters to CSV">
              ⬇ Export CSV
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => load(limit)}>↺ Refresh</button>
          </div>
        </div>
      </div>

      {loading ? (
        <div style={{ padding: 40, textAlign: 'center' }}><Spinner size={32} /></div>
      ) : filteredClusters.length === 0 ? (
        <EmptyState title="No duplicate clusters found" desc={searchFilter ? "No clusters match your filter criteria." : "Upload data with CNMC codes to see clustering results."} />
      ) : (
        <div>
          {filteredClusters.map(c => <ClusterCard key={c.cnmc} cluster={c} defaultOpen={allOpen} />)}
        </div>
      )}
    </div>
  );
}
