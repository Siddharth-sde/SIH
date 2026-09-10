import { useRef, useState } from 'react';
import { uploadFile, uploadAndHarmonize } from '../api/api';
import { Spinner } from '../components/UI';
import { useToast } from '../components/Toast';

export default function Upload() {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [harmonizeMode, setHarmonizeMode] = useState(true);
  const fileRef = useRef();
  const toast = useToast();

  const handleFile = async (file) => {
    if (!file) return;
    setLoading(true); setResult(null); setError(null);
    try {
      const uploader = harmonizeMode ? uploadAndHarmonize : uploadFile;
      const res = await uploader(file);
      if (res.detail) throw new Error(res.detail);
      setResult(res);
      toast(res.message || 'File uploaded successfully', 'success');
    } catch (e) {
      setError(e.message);
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div>
      <div className="page-header">
        <h1>Upload Material Data</h1>
        <p>Upload a CSV, Excel, or PDF file to ingest materials into the harmonization platform</p>
      </div>

      <div className="grid-2">
        <div>
          <div className="card">
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <button
                className={`btn ${harmonizeMode ? 'btn-primary' : 'btn-ghost'}`}
                style={{ flex: 1, fontSize: 12 }}
                onClick={() => setHarmonizeMode(true)}
              >
                ✦ Ingest & AI Harmonize
              </button>
              <button
                className={`btn ${!harmonizeMode ? 'btn-primary' : 'btn-ghost'}`}
                style={{ flex: 1, fontSize: 12 }}
                onClick={() => setHarmonizeMode(false)}
              >
                📁 Raw Ingest Only
              </button>
            </div>
            <div
              className={`dropzone ${dragging ? 'dragover' : ''}`}
              onClick={() => fileRef.current.click()}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              <div style={{ fontSize: 40, marginBottom: 12 }}>📁</div>
              <p>Drag & drop your file here</p>
              <span>or click to browse · CSV, XLSX, XLS, PDF supported</span>
              <input
                ref={fileRef} type="file"
                accept=".csv,.xlsx,.xls,.pdf"
                style={{ display: 'none' }}
                onChange={e => handleFile(e.target.files[0])}
              />
            </div>
            {loading && (
              <div style={{ textAlign: 'center', padding: '20px 0' }}>
                <Spinner size={28} />
                <p className="text-sm text-muted" style={{ marginTop: 8 }}>Uploading & ingesting…</p>
              </div>
            )}
            {error && (
              <div style={{ marginTop: 16, padding: '12px 14px', background: 'var(--danger-light)', borderRadius: 8, color: 'var(--danger)', fontSize: 13 }}>
                ✕ {error}
              </div>
            )}
            {result && (
              <div style={{ marginTop: 16, padding: '14px 16px', background: 'var(--success-light)', borderRadius: 8 }}>
                <div style={{ color: 'var(--success)', fontWeight: 600, marginBottom: 8 }}>✓ {result.message}</div>
                {result.detected_columns && (
                  <>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Detected columns:</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {result.detected_columns.map(c => (
                        <span key={c} style={{ background: '#fff', border: '1px solid var(--border)', borderRadius: 4, padding: '2px 6px', fontSize: 11 }}>{c}</span>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <div className="card-header"><div className="card-title">📋 Supported Column Schemas</div></div>
          <p className="text-sm text-muted" style={{ marginBottom: 14 }}>
            The platform auto-detects and normalizes column names using an alias system:
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { key: 'Material Code', aliases: 'material_code, legacy_material_code, matnr, item_code' },
              { key: 'Description', aliases: 'material_description, description, maktx, item_desc' },
              { key: 'CPSE Name', aliases: 'cpse_name, cpse_id, company, enterprise' },
              { key: 'Sector', aliases: 'sector, industry, domain' },
              { key: 'UOM', aliases: 'uom, meins, unit' },
              { key: 'Unit Price', aliases: 'unit_price_inr, unit_price, price, rate, cost' },
              { key: 'Stock Qty', aliases: 'current_stock_qty, stock_qty, stock, quantity' },
              { key: 'CNMC Code', aliases: 'common_national_material_code, cnmc_code, true_cluster_id' },
            ].map(r => (
              <div key={r.key} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                <div style={{ minWidth: 120, fontSize: 12, fontWeight: 600, color: 'var(--primary)' }}>{r.key}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>{r.aliases}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, padding: '10px 12px', background: 'var(--primary-light)', borderRadius: 8, fontSize: 12 }}>
            <strong>Tip:</strong> Any extra columns beyond the core schema will be automatically stored as JSON attributes for full traceability.
          </div>
        </div>
      </div>
    </div>
  );
}
