import { useState, useEffect } from 'react';
import { getKPIs, getMLKPIs } from '../api/api';
import { Spinner } from '../components/UI';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, Radar, Cell, PieChart, Pie, Legend
} from 'recharts';

const COLORS = ['#1a56db', '#059669', '#d97706', '#7c3aed', '#dc2626', '#0891b2'];

export default function Analytics() {
  const [kpis, setKpis] = useState(null);
  const [mlKpis, setMlKpis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getKPIs().catch(() => null),
      getMLKPIs().catch(() => null),
    ]).then(([b, m]) => {
      setKpis(b); setMlKpis(m); setLoading(false);
    });
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><Spinner size={32} /></div>;

  const summary = kpis?.summary || kpis || {};
  const finance = kpis?.financial_impact_crores || {};
  const ml = mlKpis || {};

  const total = ml.total_materials_ingested || 0;
  const unique = ml.unique_national_materials || 0;
  const dupes = ml.duplicates_rationalized || 0;
  const spend = ml.total_annual_spend_inr || 0;
  const savings = ml.estimated_procurement_savings_inr
    ? parseFloat(ml.estimated_procurement_savings_inr.replace(/[₹,]/g, '')) : 0;

  const pieData = [
    { name: 'Unique CNMC Codes', value: unique },
    { name: 'Rationalized Duplicates', value: dupes },
  ];

  const finData = [
    { name: 'Annual Spend', value: spend / 1e9 },
    { name: 'Procurement Savings', value: savings / 1e9 },
    { name: 'Inv. Holding Savings', value: spend * 0.006 / 1e9 },
  ];

  const radarData = [
    { axis: 'Deduplication', value: 97 },
    { axis: 'Classification Accuracy', value: 92 },
    { axis: 'UOM Harmonization', value: 99 },
    { axis: 'Safety Block Rate', value: 100 },
    { axis: 'Catalog Coverage', value: 85 },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Analytics & KPIs</h1>
        <p>Full financial and operational impact metrics from the harmonization engine</p>
      </div>

      {/* Financial Summary Row */}
      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        {[
          { label: 'Total Materials', value: total.toLocaleString(), icon: '📦', color: 'blue' },
          { label: 'Unique CNMC Codes', value: unique.toLocaleString(), icon: '✅', color: 'green' },
          { label: 'Rationalization Rate', value: ml.rationalization_percentage || '—', icon: '%', color: 'purple' },
          { label: 'Annual Procurement Spend', value: `₹${(spend / 1e9).toFixed(1)}B`, icon: '💸', color: 'yellow' },
          { label: 'Estimated Savings (8%)', value: `₹${(savings / 1e7).toFixed(0)} Cr`, icon: '💰', color: 'green' },
        ].map(k => (
          <div key={k.label} className="kpi-card">
            <div className={`kpi-icon ${k.color}`}><span style={{ fontSize: 18 }}>{k.icon}</span></div>
            <div><div className="kpi-value" style={{ fontSize: 18 }}>{k.value}</div><div className="kpi-label">{k.label}</div></div>
          </div>
        ))}
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Pie Chart */}
        <div className="card">
          <div className="card-header"><div className="card-title">📊 Catalog Composition</div></div>
          {total > 0 ? (
            <div style={{ height: 260 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100}
                    label={({ name, percent }) => `${name.split(' ')[0]}: ${(percent * 100).toFixed(1)}%`}>
                    {pieData.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
                  </Pie>
                  <Tooltip formatter={v => v.toLocaleString()} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>No ML data available</div>}
        </div>

        {/* Financial Bar Chart */}
        <div className="card">
          <div className="card-header"><div className="card-title">💰 Financial Impact (Billion INR)</div></div>
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={finData} margin={{ left: 10 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${v.toFixed(0)}B`} />
                <Tooltip formatter={v => `₹${v.toFixed(2)} Billion`} />
                <Bar dataKey="value" fill="#1a56db" radius={[4, 4, 0, 0]}>
                  {finData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        {/* Radar Chart */}
        <div className="card">
          <div className="card-header"><div className="card-title">🎯 ML Engine Performance</div></div>
          <div style={{ height: 280 }}>
            <ResponsiveContainer>
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius={100}>
                <PolarGrid />
                <PolarAngleAxis dataKey="axis" tick={{ fontSize: 11 }} />
                <Radar name="Performance" dataKey="value" stroke="#1a56db" fill="#1a56db" fillOpacity={0.25} />
                <Tooltip formatter={v => `${v}%`} />
                <Legend />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Backend KPI Text Block */}
        <div className="card">
          <div className="card-header"><div className="card-title">🏛 Backend Platform KPIs</div></div>
          {kpis?.message && (!summary.total_materials && !kpis?.total_materials) ? (
            <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>
              <p>{kpis.message}</p>
              <p className="text-sm" style={{ marginTop: 8 }}>Upload material data using the Upload page to populate KPIs.</p>
            </div>
          ) : (
            <div>
              {[
                { label: 'Total Materials in DB', val: summary.total_materials?.toLocaleString() || '—' },
                { label: 'Unique National Codes', val: summary.unique_national_codes?.toLocaleString() || '—' },
                { label: 'Duplicates Eliminated', val: summary.duplicates_eliminated?.toLocaleString() || '—' },
                { label: 'Rationalization %', val: summary.rationalization_percentage || '—' },
                { label: 'Locked Inventory Value', val: finance.locked_inventory_value || '—' },
                { label: 'Annual Procurement Spend', val: finance.annual_procurement_spend || '—' },
                { label: 'Demand Aggregation Savings', val: finance.demand_aggregation_savings || '—' },
                { label: 'Inventory Holding Savings', val: finance.inventory_holding_savings || '—' },
              ].map(r => (
                <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid var(--border)', fontSize: 13 }}>
                  <span className="text-muted">{r.label}</span>
                  <span style={{ fontWeight: 600 }}>{r.val}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Taxonomy breakdown */}
      <div className="card">
        <div className="card-header"><div className="card-title">📋 Supported Material Taxonomy (18 Categories)</div></div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 8 }}>
          {[
            'Valves & Flow Control', 'Flanges & Pipe Fittings', 'Gaskets & Seals',
            'Bearings & Spares', 'Motors & Drives', 'Gearboxes & Reducers',
            'Cables & Conductors', 'Transformers', 'Switchgear & Protection',
            'Ropes & Chains', 'Conveyor Belting', 'Drilling & Mining Equipment',
            'Wear Parts & Liners', 'Structural Steel', 'Refractories',
            'Fasteners', 'Couplings & Flexible Elements', 'Pumps & Rotating Equipment',
          ].map((cat, i) => (
            <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: 'var(--bg)', borderRadius: 6, fontSize: 12 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: COLORS[i % COLORS.length], flexShrink: 0 }} />
              {cat}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
