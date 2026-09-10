import { useState, useEffect, useCallback } from 'react';
import { getMaterials, updateMaterialStatus } from '../api/api';
import { Spinner, StatusBadge, EmptyState } from '../components/UI';
import { useToast } from '../components/Toast';

const SECTORS = ['Oil & Gas', 'Steel', 'Power', 'Mining', 'Heavy Engineering'];

export default function Materials() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState('');
  const [sector, setSector] = useState('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState(null);
  const toast = useToast();
  const limit = 20;

  const load = useCallback(async (q, sector, offset) => {
    setLoading(true);
    try {
      const data = await getMaterials({ q, sector, limit, offset });
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch {
      toast('Failed to load materials', 'error');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(q, sector, offset); }, [q, sector, offset]);

  const handleSearch = (e) => { setQ(e.target.value); setOffset(0); };
  const handleSector = (e) => { setSector(e.target.value); setOffset(0); };

  const handleAction = async (id, action) => {
    try {
      const res = await updateMaterialStatus(id, action);
      toast(res.message, 'success');
      setItems(prev => prev.map(m => m.id === id ? { ...m, status: res.status } : m));
      if (selected?.id === id) setSelected(s => ({ ...s, status: res.status }));
    } catch {
      toast('Action failed', 'error');
    }
  };

  const pages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <div>
      <div className="page-header">
        <h1>Materials Browser</h1>
        <p>Search, browse, and govern all materials across CPSEs · <strong>{total.toLocaleString()}</strong> total records</p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="input-row">
          <div className="search-wrap" style={{ flex: 1 }}>
            <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M9 3a6 6 0 100 12A6 6 0 009 3zM2 9a7 7 0 1112.452 4.391l3.328 3.329a1 1 0 11-1.414 1.414l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd"/></svg>
            <input className="input" placeholder="Search description, code, or CPSE…" value={q} onChange={handleSearch} />
          </div>
          <select className="input" style={{ width: 180 }} value={sector} onChange={handleSector}>
            <option value="">All Sectors</option>
            {SECTORS.map(s => <option key={s}>{s}</option>)}
          </select>
          <button className="btn btn-primary btn-sm" onClick={() => load(q, sector, offset)}>
            Refresh
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selected ? '1fr 380px' : '1fr', gap: 16 }}>
        <div className="card" style={{ padding: 0 }}>
          {loading ? (
            <div style={{ padding: 40, textAlign: 'center' }}><Spinner /></div>
          ) : items.length === 0 ? (
            <EmptyState title="No materials found" desc="Upload data or adjust your search filters." />
          ) : (
            <>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Code</th>
                      <th>Description</th>
                      <th>CPSE</th>
                      <th>Sector</th>
                      <th>UOM</th>
                      <th>Unit Price</th>
                      <th>CNMC</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(m => (
                      <tr key={m.id} style={{ cursor: 'pointer', background: selected?.id === m.id ? 'var(--primary-light)' : '' }} onClick={() => setSelected(m)}>
                        <td className="font-mono text-sm">{m.material_code}</td>
                        <td style={{ maxWidth: 220 }}><div className="truncate">{m.description}</div></td>
                        <td>{m.cpse_name}</td>
                        <td>{m.sector}</td>
                        <td>{m.uom}</td>
                        <td style={{ textAlign: 'right' }}>
                          {m.unit_price > 0 ? `₹${m.unit_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                        </td>
                        <td className="font-mono text-sm" style={{ color: 'var(--primary)' }}>{m.cnmc_code}</td>
                        <td><StatusBadge status={m.status} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={{ padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border)' }}>
                <span className="text-sm text-muted">Page {currentPage} of {pages} · {total.toLocaleString()} records</span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button className="btn btn-ghost btn-sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))}>← Prev</button>
                  <button className="btn btn-ghost btn-sm" disabled={offset + limit >= total} onClick={() => setOffset(offset + limit)}>Next →</button>
                </div>
              </div>
            </>
          )}
        </div>

        {selected && (
          <div className="card" style={{ position: 'sticky', top: 20, alignSelf: 'flex-start' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ fontWeight: 600 }}>Material Detail</div>
              <button className="btn btn-ghost btn-sm" onClick={() => setSelected(null)}>✕ Close</button>
            </div>
            <div className="font-mono" style={{ fontSize: 12, color: 'var(--primary)', marginBottom: 4 }}>{selected.material_code}</div>
            <div style={{ fontWeight: 600, marginBottom: 12 }}>{selected.description}</div>
            <div className="divider" />
            {[
              { label: 'CPSE', val: selected.cpse_name },
              { label: 'Sector', val: selected.sector },
              { label: 'UOM', val: selected.uom },
              { label: 'Unit Price', val: selected.unit_price > 0 ? `₹${selected.unit_price.toLocaleString('en-IN')}` : '—' },
              { label: 'Stock Qty', val: selected.stock_qty?.toLocaleString() },
              { label: 'Annual Qty', val: selected.annual_qty?.toLocaleString() },
              { label: 'CNMC Code', val: selected.cnmc_code },
              { label: 'Status', val: <StatusBadge status={selected.status} /> },
            ].map(r => (
              <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                <span className="text-muted">{r.label}</span>
                <span style={{ fontWeight: 500 }}>{r.val}</span>
              </div>
            ))}
            {Object.keys(selected.extra_attributes || {}).length > 0 && (
              <>
                <div className="divider" />
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Extra Attributes</div>
                {Object.entries(selected.extra_attributes).slice(0, 8).map(([k, v]) => (
                  <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, padding: '3px 0' }}>
                    <span className="text-muted font-mono">{k}</span>
                    <span style={{ maxWidth: 160, textAlign: 'right' }} className="truncate">{v}</span>
                  </div>
                ))}
              </>
            )}
            {(selected.status === 'PENDING_REVIEW' || selected.status === 'ACTIVE') && (
              <>
                <div className="divider" />
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-success" style={{ flex: 1 }} onClick={() => handleAction(selected.id, 'APPROVE')}>✓ Approve</button>
                  <button className="btn btn-danger" style={{ flex: 1 }} onClick={() => handleAction(selected.id, 'REJECT')}>✕ Reject</button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
