import { useEffect, useState } from 'react';
import { getKPIs, getMLKPIs } from '../api/api';
import { Spinner } from '../components/UI';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';

const COLORS = ['#1a56db', '#059669', '#d97706', '#7c3aed', '#dc2626'];

function KPICard({ label, value, sub, color = 'blue', icon }) {
  return (
    <div className="kpi-card">
      <div className={`kpi-icon ${color}`}><span style={{ fontSize: 20 }}>{icon}</span></div>
      <div>
        <div className="kpi-value">{value ?? '—'}</div>
        <div className="kpi-label">{label}</div>
        {sub && <div className="kpi-sub">{sub}</div>}
      </div>
    </div>
  );
}

const fmtCrore = (n) => {
  if (!n && n !== 0) return '—';
  const cr = n / 1e7;
  if (cr >= 1000) return `₹${(cr / 1000).toFixed(1)}K Cr`;
  return `₹${cr.toFixed(1)} Cr`;
};

export default function Dashboard() {
  const [kpis, setKpis] = useState(null);
  const [mlKpis, setMlKpis] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getKPIs().catch(() => null),
      getMLKPIs().catch(() => null),
    ]).then(([b, m]) => {
      setKpis(b);
      setMlKpis(m);
      setLoading(false);
    });
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}><Spinner size={32} /></div>;

  const summary = kpis?.summary || kpis || {};
  const finance = kpis?.financial_impact_crores || {};

  // Sector breakdown for pie chart (mock categories)
  const sectorData = mlKpis ? [
    { name: 'Unique CNMC', value: mlKpis.unique_national_materials || 0 },
    { name: 'Rationalized', value: mlKpis.duplicates_rationalized || 0 },
  ] : [];

  // Financial bar chart (Empirical Price Arbitrage & 20% DPE Holding Cost)
  const financeBar = [
    {
      name: 'PDI Arbitrage Savings',
      value: kpis?.empirical_arbitrage_savings_inr != null
        ? kpis.empirical_arbitrage_savings_inr / 1e7
        : (kpis?.potential_procurement_savings_inr ? kpis.potential_procurement_savings_inr / 1e7 : 0)
    },
    {
      name: 'DPE Holding Cost (20%)',
      value: kpis?.inventory_holding_cost_inr != null
        ? kpis.inventory_holding_cost_inr / 1e7
        : (kpis?.potential_inventory_reduction_inr ? kpis.potential_inventory_reduction_inr / 1e7 : 0)
    },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>National Material Master Dashboard</h1>
        <p>Real-time overview of harmonization metrics across all CPSEs</p>
      </div>

      <div className="kpi-grid">
        <KPICard icon="📦" label="Total Materials Ingested" value={mlKpis?.total_materials_ingested?.toLocaleString() || summary?.total_materials?.toLocaleString() || kpis?.total_materials?.toLocaleString() || '—'} color="blue" />
        <KPICard icon="✅" label="Unique National Codes (CNMC)" value={mlKpis?.unique_national_materials?.toLocaleString() || summary?.unique_national_codes?.toLocaleString() || kpis?.unique_national_codes?.toLocaleString() || '—'} color="green" sub="AI Minted" />
        <KPICard icon="♻" label="Duplicates Rationalized" value={mlKpis?.duplicates_rationalized?.toLocaleString() || summary?.duplicates_eliminated?.toLocaleString() || kpis?.duplicate_materials?.toLocaleString() || '—'} color="red" />
        <KPICard icon="%" label="Rationalization Rate" value={mlKpis?.rationalization_percentage || summary?.rationalization_percentage || (kpis?.duplicate_percentage ? `${kpis.duplicate_percentage}%` : '—')} color="purple" sub="Catalog compression" />
        <KPICard icon="💰" label="Annual Procurement Spend" value={mlKpis?.total_annual_spend_inr ? fmtCrore(mlKpis.total_annual_spend_inr) : finance?.annual_procurement_spend || (kpis?.annual_procurement_value_inr ? fmtCrore(kpis.annual_procurement_value_inr) : '—')} color="yellow" />
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-header"><div className="card-title">Rationalization Breakdown</div></div>
          {sectorData.length > 0 ? (
            <div className="chart-wrap">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={sectorData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, value }) => `${name}: ${value?.toLocaleString()}`}>
                    {sectorData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={v => v?.toLocaleString()} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-state"><p>No ML data available. Run a harmonization batch to see analytics.</p></div>
          )}
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">Financial Impact (Crores INR)</div></div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={financeBar} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => `₹${v.toFixed(0)}Cr`} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={130} />
                <Tooltip formatter={v => `₹${v?.toFixed(2)} Cr`} />
                <Bar dataKey="value" fill="#1a56db" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header"><div className="card-title">📋 ML Pipeline Stages</div></div>
        <div className="pipeline-stages">
          {[
            { n: 1, label: 'Text Normalisation & UOM Harmonization', status: 'done' },
            { n: 2, label: 'Technical Attribute Extraction & Conflict Detection', status: 'done' },
            { n: 3, label: 'Dual-Layer Taxonomy Classification', status: 'done' },
            { n: 4, label: 'Deduplication Clustering & CNMC Generation', status: 'done' },
          ].map(s => (
            <div key={s.n} className={`pipeline-stage ${s.status}`}>
              <div className="stage-num">{s.n}</div>
              <div className="stage-label">{s.label}</div>
            </div>
          ))}
        </div>
        <p className="text-sm text-muted">All 4 ML pipeline stages completed. {mlKpis?.total_materials_ingested?.toLocaleString() || 0} items processed → {mlKpis?.unique_national_materials?.toLocaleString() || 0} CNMC codes minted.</p>
      </div>
    </div>
  );
}
