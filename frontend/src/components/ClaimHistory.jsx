import React, { useEffect, useState } from 'react';

export default function ClaimHistory({ authToken, setAuthToken, currentScreen, setCurrentScreen, setClaimResult }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [claims, setClaims] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('http://localhost:8000/claims', {
      headers: { Authorization: `Bearer ${authToken}` },
    })
      .then((res) => res.json())
      .then((data) => setClaims(data.claims || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [authToken]);

  const handleRowClick = async (claimId) => {
    try {
      const res = await fetch(`http://localhost:8000/claims/${claimId}`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not load claim');
      setClaimResult(data);
      setCurrentScreen('result');
    } catch (err) {
      setError(err.message);
    }
  };

  const badgeStyle = (decision) => {
    if (decision === 'approved') return { bg: '#DEF7EC', text: '#03543F', label: 'Approved' };
    if (decision === 'denied') return { bg: '#FDE8E8', text: '#9B1C1C', label: 'Denied' };
    return { bg: '#FDF6B2', text: '#723B13', label: 'Needs Review' };
  };

  const filteredClaims = claims.filter((c) =>
    (c.policy_number || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="text-on-surface font-body-md antialiased min-h-screen flex flex-col bg-surface-container-lowest">
<header className="bg-surface-container-lowest border-b border-outline-variant w-full">
  <div className="relative flex items-center w-full px-margin-desktop py-4">
    <div
      className="font-headline-sm text-headline-sm font-bold text-primary cursor-pointer"
      onClick={() => setCurrentScreen('submit')}
    >
      Meridian
    </div>
    <nav className="hidden md:flex gap-6 items-center absolute left-1/2 -translate-x-1/2">
      <button
        type="button"
        onClick={() => setCurrentScreen('submit')}
        className={`font-body-md text-body-md pb-1 cursor-pointer transition-colors duration-150 ${
          currentScreen === 'submit'
            ? 'text-primary border-b-2 border-primary font-bold'
            : 'text-on-surface-variant hover:text-primary'
        }`}
      >
        Submit a Claim
      </button>
      <button
        type="button"
        onClick={() => setCurrentScreen('history')}
        className={`font-body-md text-body-md pb-1 cursor-pointer transition-colors duration-150 ${
          currentScreen === 'history'
            ? 'text-primary border-b-2 border-primary font-bold'
            : 'text-on-surface-variant hover:text-primary'
        }`}
      >
        Claim History
      </button>
    </nav>
    <button
      type="button"
      onClick={() => setAuthToken(null)}
      className="ml-auto font-body-md text-body-md text-primary cursor-pointer hover:text-on-surface-variant transition-all duration-150"
    >
      Log Out
    </button>
  </div>
</header>

      <main className="flex-grow w-full max-w-container-max mx-auto px-margin-mobile md:px-margin-desktop py-margin-desktop">
        <div className="mb-stack-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-stack-md">
          <div>
            <h1 className="font-headline-md text-headline-md text-on-surface mb-unit">Claim History</h1>
            <p className="font-body-md text-body-md text-on-surface-variant">Review and manage past and pending insurance claims.</p>
          </div>
          <div className="flex items-center gap-stack-sm w-full md:w-auto">
            <input
              className="w-full md:w-64 px-3 py-2 border border-[#D1D5DB] rounded font-body-md text-body-md bg-surface-container-lowest text-on-surface outline-none transition-colors"
              placeholder="Search by policy number..."
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {error && <p className="mb-stack-md" style={{ color: '#9B1C1C' }}>{error}</p>}
        {loading && <p className="text-on-surface-variant">Loading claims...</p>}

        {!loading && filteredClaims.length === 0 && (
          <p className="text-on-surface-variant">No claims yet — submit one to see it here.</p>
        )}

        {!loading && filteredClaims.length > 0 && (
          <div className="w-full overflow-x-auto border border-[#E5E7EB] rounded-DEFAULT">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead>
                <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant">Date</th>
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant">Policy Number</th>
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant">Claim Type</th>
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant">Decision</th>
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="font-data-tabular text-data-tabular text-on-surface bg-surface-container-lowest">
                {filteredClaims.map((c) => {
                  const badge = badgeStyle(c.final_decision);
                  return (
                    <tr
                      key={c.id}
                      onClick={() => handleRowClick(c.id)}
                      className="border-b border-[#E5E7EB] hover:bg-surface-bright transition-colors cursor-pointer"
                    >
                      <td className="py-3 px-4">{c.created_at?.slice(0, 10)}</td>
                      <td className="py-3 px-4">{c.policy_number || '—'}</td>
                      <td className="py-3 px-4 capitalize">{c.claim_type || '—'}</td>
                      <td className="py-3 px-4">
                        <span className="inline-flex items-center px-2 py-1 rounded font-label-md text-label-md" style={{ background: badge.bg, color: badge.text }}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        {c.amount_requested != null ? `$${Number(c.amount_requested).toFixed(2)}` : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>

      <footer className="bg-surface-container w-full bottom-0 border-t border-outline-variant mt-auto">

      </footer>
    </div>
  );
}