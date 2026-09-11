/**
 * Indian Public Sector & DPE standard currency and number formatting utilities.
 * Mandates ₹ Crores (Cr) and ₹ Lakhs (L) in place of Western notation (Billions/Millions).
 */

export function formatCrores(amount, decimals = 2) {
  if (amount === null || amount === undefined || isNaN(amount)) return '—';
  const val = Number(amount) / 1e7;
  return `₹${val.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} Cr`;
}

export function formatLakhs(amount, decimals = 2) {
  if (amount === null || amount === undefined || isNaN(amount)) return '—';
  const val = Number(amount) / 1e5;
  return `₹${val.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })} L`;
}

export function formatINR(amount, decimals = 2) {
  if (amount === null || amount === undefined || isNaN(amount)) return '—';
  return `₹${Number(amount).toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}`;
}

export function formatNumber(val) {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return Number(val).toLocaleString('en-IN');
}

export function formatSmartCurrency(amount) {
  if (amount === null || amount === undefined || isNaN(amount)) return '—';
  const num = Number(amount);
  if (num >= 1e7) return formatCrores(num, 2);
  if (num >= 1e5) return formatLakhs(num, 2);
  return formatINR(num, 2);
}

export function formatPercent(val, decimals = 1) {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'string' && val.includes('%')) return val;
  const num = Number(val);
  if (isNaN(num)) return '—';
  return `${num.toFixed(decimals)}%`;
}
