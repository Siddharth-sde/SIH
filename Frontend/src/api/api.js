const defaultHost = typeof window !== 'undefined' && window.location.hostname ? window.location.hostname : 'localhost';
const isProxied = typeof window !== 'undefined' && window.location.port === '5173';
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || (isProxied ? '' : `http://${defaultHost}:8000`);

// ── Backend APIs ──────────────────────────────────────────────────────────────

export const getKPIs = () =>
  fetch(`${BACKEND_URL}/api/analytics/kpis`).then(r => r.json());

export const getMaterials = (params = {}) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== '' && v !== null))
  );
  return fetch(`${BACKEND_URL}/api/materials?${qs}`).then(r => r.json());
};

export const getClusters = (limit = 25) =>
  fetch(`${BACKEND_URL}/api/duplicates/clusters?limit=${limit}`)
    .then(r => r.json())
    .then(d => (Array.isArray(d) ? d : (d.clusters || [])));

export const uploadFile = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return fetch(`${BACKEND_URL}/api/upload`, { method: 'POST', body: fd }).then(r => r.json());
};

export const uploadAndHarmonize = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return fetch(`${BACKEND_URL}/api/upload-and-harmonize`, { method: 'POST', body: fd })
    .then(r => {
      if (!r.ok) return r.json().then(err => Promise.reject(new Error(err.detail || 'Harmonization failed')));
      return r.json();
    });
};

export const updateMaterialStatus = (id, action) =>
  fetch(`${BACKEND_URL}/api/materials/${id}/action?action=${action}`, { method: 'POST' }).then(r => r.json());

export const getAuditLogs = (limit = 50) =>
  fetch(`${BACKEND_URL}/api/audit?limit=${limit}`).then(r => r.json());

// ── ML Service APIs (Routed through Backend Gateway) ──────────────────────────

export const getMLHealth = () =>
  fetch(`${BACKEND_URL}/api/ml/health`).then(r => r.json()).catch(() => ({ status: 'unreachable' }));

export const getMLKPIs = () =>
  fetch(`${BACKEND_URL}/api/ml/kpis`).then(r => r.json()).catch(() => null);

export const matchSingle = (payload) =>
  fetch(`${BACKEND_URL}/api/ml/match-single`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then(r => { if (!r.ok) throw new Error('ML service error'); return r.json(); });

export const harmonizeBatch = (file) => {
  const fd = new FormData();
  fd.append('file', file);
  return fetch(`${BACKEND_URL}/api/upload-and-harmonize`, { method: 'POST', body: fd }).then(r => r.json());
};
