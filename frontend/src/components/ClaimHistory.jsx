import React, { useEffect, useState } from 'react';
import Header from './Header.jsx';
import { badgeFor, badgeStyle, formatAmount } from './ui.js';

export default function ClaimHistory({
  authToken,
  setAuthToken,
  currentScreen,
  setCurrentScreen,
  setClaimResult,
  userRole,
}) {
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

  const filteredClaims = claims.filter((c) =>
    (c.policy_number || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const th = 'py-2.5 px-4 text-[12.5px] font-medium text-on-surface-variant';

  return (
    <div className="text-on-surface font-body-md antialiased min-h-screen flex flex-col bg-background">
      <Header
        currentScreen={currentScreen}
        setCurrentScreen={setCurrentScreen}
        setAuthToken={setAuthToken}
        userRole={userRole}
      />

      <main className="flex-grow w-full max-w-[1200px] mx-auto px-margin-mobile md:px-margin-desktop py-10">
        <div className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
          <div>
            <h1 className="font-headline-md text-headline-md text-on-surface">Claim history</h1>
            <p className="font-body-md text-body-md text-on-surface-variant mt-1">
              Every claim you've submitted and what was decided. Select a row to see the reasoning.
            </p>
          </div>

          <input
            className="w-full md:w-64 px-3 py-2 border border-outline-variant font-body-md text-body-md bg-white text-on-surface"
            placeholder="Search by policy number"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        {error && (
          <p className="mb-4" style={{ color: '#b91c1c' }}>
            {error}
          </p>
        )}

        {loading && <p className="text-on-surface-variant">Loading claims…</p>}

        {!loading && filteredClaims.length === 0 && (
          <div className="bg-white border border-outline-variant rounded-DEFAULT p-8 text-center">
            <p className="text-on-surface-variant">No claims yet. Submit one and it will appear here.</p>
          </div>
        )}

        {!loading && filteredClaims.length > 0 && (
          <div className="w-full overflow-x-auto bg-white border border-outline-variant rounded-DEFAULT">
            <table className="w-full text-left border-collapse min-w-[720px]">
              <thead>
                <tr className="border-b border-outline-variant bg-surface-container-low">
                  <th className={th}>Date</th>
                  <th className={th}>Policy number</th>
                  <th className={th}>Claim type</th>
                  <th className={th}>Decision</th>
                  <th className={`${th} text-right`}>Amount</th>
                </tr>
              </thead>

              <tbody className="text-on-surface">
                {filteredClaims.map((c) => {
                  const badge = badgeFor(c.final_decision);
                  return (
                    <tr
                      key={c.id}
                      onClick={() => handleRowClick(c.id)}
                      className="border-b border-outline-variant last:border-b-0 hover:bg-surface transition-colors cursor-pointer"
                    >
                      <td className="py-3 px-4 font-data-tabular text-data-tabular">{c.created_at?.slice(0, 10)}</td>
                      <td className="py-3 px-4 font-data-tabular text-data-tabular">{c.policy_number || '—'}</td>
                      <td className="py-3 px-4 text-[14px] capitalize">{c.claim_type || '—'}</td>
                      <td className="py-3 px-4">
                        <span className="status" style={badgeStyle(badge)}>{badge.label}</span>
                      </td>
                      <td className="py-3 px-4 text-right font-data-tabular text-data-tabular">
                        {formatAmount(c.amount_requested)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
