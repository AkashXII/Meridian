// Shared presentation helpers. No data fetching or app logic in here.

const BADGES = {
  approved: { label: 'Approved', dot: '#15803d' },
  denied: { label: 'Denied', dot: '#b91c1c' },
  needs_review: { label: 'Needs review', dot: '#c2410c' },
  pending: { label: 'Pending', dot: '#c2410c' },
  info: { label: 'More info needed', dot: '#a8a29e' },
};

const UNKNOWN = { label: 'Unknown', dot: '#a8a29e' };

export function badgeFor(decision) {
  return BADGES[decision] || UNKNOWN;
}

// Plain status text with a small coloured dot (dot drawn by .status in index.css).
export function badgeStyle(b) {
  return { '--dot': b.dot };
}

export function formatAmount(value) {
  if (value == null || value === '') return '—';
  return `$${Number(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
