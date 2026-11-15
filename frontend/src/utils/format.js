export const formatMoney = (value) => `₹${Number(value || 0).toFixed(2)}`;

export const formatDateTime = (iso) =>
  iso
    ? new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
    : '';

export const titleCase = (s) => (s || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
