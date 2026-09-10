import { useState } from 'react';
import { matchSingle } from '../api/api';
import { Spinner, EmptyState } from '../components/UI';
import { useToast } from '../components/Toast';

const RELATIONSHIP_COLOR = {
  'Exact Duplicate': 'red',
  'Near Duplicate': 'yellow',
  'Functionally Equivalent': 'blue',
};

const SAMPLE_QUERIES = [
  'Gate Valve 150NB Class 150 Carbon Steel Flanged API 600',
  'SPH ROLLER BRG Bearing 22220',
  'Deep Groove Ball Bearing 25x52x15mm Rubber Sealed',
  'Induction Motor 30kW 4P TEFC 415V IE3',
  'XLPE Cable 3C 70 sqmm Aluminium Armoured',
];

export default function AIMatch() {
  const [query, setQuery] = useState('');
  const [specText, setSpecText] = useState('');
  const [uom, setUom] = useState('NOS');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const toast = useToast();

  const handleMatch = async () => {
    if (!query.trim()) { toast('Enter a material description', 'error'); return; }
    setLoading(true); setResult(null); setError(null);
    try {
      const res = await matchSingle({ query_description: query, query_spec_text: specText, query_uom: uom, top_k: topK });
      if (res.detail) throw new Error(res.detail);
      setResult(res);
    } catch (e) {
      setError(e.message);
      toast('ML service: ' + e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>AI Matching Engine</h1>
        <p>Real-time semantic matching against the golden CNMC catalog · ML Engine (port 8001)</p>
      </div>

      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <div className="card-header"><div className="card-title">✦ Query Material</div></div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Material Description *</label>
            <textarea
              className="input"
              rows={3}
              placeholder="e.g. Gate Valve 150NB Class 150 CS Flanged API 600"
              value={query}
              onChange={e => setQuery(e.target.value)}
              style={{ resize: 'vertical' }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Technical Specification (optional)</label>
            <textarea
              className="input"
              rows={2}
              placeholder="e.g. Body: ASTM A216 WCB | Trim: SS316 | ANSI Class 150"
              value={specText}
              onChange={e => setSpecText(e.target.value)}
              style={{ resize: 'vertical' }}
            />
          </div>

          <div className="input-row" style={{ marginBottom: 16 }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>UOM</label>
              <input className="input" value={uom} onChange={e => setUom(e.target.value)} placeholder="NOS, MTR, KG…" />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>Top K Results</label>
              <select className="input" value={topK} onChange={e => setTopK(Number(e.target.value))}>
                {[3, 5, 10].map(n => <option key={n}>{n}</option>)}
              </select>
            </div>
          </div>

          <button className="btn btn-primary" style={{ width: '100%' }} onClick={handleMatch} disabled={loading}>
            {loading ? <><Spinner size={14} /> Matching…</> : '✦ Run AI Match'}
          </button>

          {error && (
            <div style={{ marginTop: 12, padding: '10px 12px', background: 'var(--danger-light)', borderRadius: 8, color: 'var(--danger)', fontSize: 12 }}>
              {error}
            </div>
          )}

          <div className="divider" />
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Sample Queries</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {SAMPLE_QUERIES.map(s => (
              <button key={s} className="btn btn-ghost btn-sm" style={{ justifyContent: 'flex-start', fontSize: 11, textAlign: 'left' }} onClick={() => setQuery(s)}>
                {s}
              </button>
            ))}
          </div>
        </div>

        <div>
          {result ? (
            <div>
              <div className="card" style={{ marginBottom: 16 }}>
                <div style={{ fontWeight: 600, marginBottom: 12 }}>Query Analysis</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {[
                    { label: 'Original Query', val: result.query },
                    { label: 'Cleaned Query', val: result.cleaned_query, mono: true },
                    { label: 'Predicted Category', val: result.predicted_category, badge: 'blue' },
                  ].map(r => (
                    <div key={r.label} style={{ padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 2 }}>{r.label}</div>
                      <div style={{ fontSize: 13, fontFamily: r.mono ? 'monospace' : 'inherit' }}>{r.val}</div>
                    </div>
                  ))}
                  {result.extracted_attributes && Object.keys(result.extracted_attributes).length > 0 && (
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Extracted Attributes</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {Object.entries(result.extracted_attributes).flatMap(([k, v]) =>
                          Array.isArray(v) ? v.map((x, i) => (
                            <span key={`${k}${i}`} style={{ background: 'var(--primary-light)', color: 'var(--primary)', fontSize: 11, padding: '2px 8px', borderRadius: 99 }}>{k}: {x}</span>
                          )) : typeof v === 'object' && v !== null ? (
                            Object.entries(v).map(([sk, sv]) => (
                              <span key={`${k}-${sk}`} style={{ background: 'var(--bg)', fontSize: 11, padding: '2px 8px', borderRadius: 99 }}>{sk}: {sv}</span>
                            ))
                          ) : v ? [
                            <span key={k} style={{ background: 'var(--bg)', fontSize: 11, padding: '2px 8px', borderRadius: 99 }}>{k}: {String(v)}</span>
                          ] : []
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div className="card-title" style={{ marginBottom: 12 }}>Top {result.top_matches?.length || 0} Matches</div>
              {result.top_matches?.length === 0 ? (
                <EmptyState title="No matches found" desc="No CNMC clusters above the similarity threshold. Try a different description." />
              ) : (
                result.top_matches?.map((m, i) => (
                  <div key={i} className="match-result">
                    <div className="match-result-header">
                      <div>
                        <div style={{ fontFamily: 'monospace', color: 'var(--primary)', fontSize: 12 }}>{m.cnmc_code}</div>
                        <div style={{ fontWeight: 600, fontSize: 13, marginTop: 2 }}>{m.canonical_description}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div className="match-score">{m.match_confidence}%</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>confidence</div>
                      </div>
                    </div>
                    <div className="confidence-bar">
                      <div className="confidence-fill" style={{ width: `${m.match_confidence}%`, background: m.match_confidence >= 85 ? 'var(--success)' : m.match_confidence >= 70 ? 'var(--warning)' : 'var(--primary)' }} />
                    </div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                      <span className={`badge badge-${RELATIONSHIP_COLOR[m.relationship] || 'gray'}`}>{m.relationship}</span>
                      <span className="badge badge-gray">{m.category}</span>
                      {m.affected_cpses?.slice(0, 3).map(c => <span key={c} className="badge badge-blue">{c}</span>)}
                    </div>
                    {m.reasoning && (
                      <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                        🔍 {m.reasoning}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          ) : (
            <EmptyState
              title="No results yet"
              desc="Enter a material description and click 'Run AI Match' to find semantic duplicates in the golden CNMC catalog."
            />
          )}
        </div>
      </div>
    </div>
  );
}
