import React, { useEffect, useState } from 'react';

export default function ReviewQueue({ authToken, setAuthToken, userRole, currentScreen, setCurrentScreen }) {
  const [queue, setQueue] = useState([]);
  const [selected, setSelected] = useState(null);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const loadQueue = () => {
    setLoading(true);
    fetch('http://localhost:8000/review/queue', {
      headers: { Authorization: `Bearer ${authToken}` },
    })
      .then((res) => res.json().then((data) => {
        if (!res.ok) throw new Error(data.detail || 'Could not load queue');
        return data;
      }))
      .then((data) => setQueue(data.queue || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(loadQueue, [authToken]);

  const resolve = async (decision) => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/review/${selected.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ decision, notes }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Could not resolve claim');
      setSelected(null);
      setNotes('');
      loadQueue();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="text-on-surface font-body-md min-h-screen flex flex-col bg-surface-container-lowest">
      <header className="bg-surface-container-lowest border-b border-outline-variant w-full">
        <div className="relative flex items-center w-full px-margin-desktop py-4">
          <div className="font-headline-sm text-headline-sm font-bold text-primary cursor-pointer" onClick={() => setCurrentScreen('submit')}>
            ClaimsPortal
          </div>
          <nav className="hidden md:flex gap-6 items-center absolute left-1/2 -translate-x-1/2">
            <button type="button" onClick={() => setCurrentScreen('submit')} className="font-body-md text-body-md pb-1 cursor-pointer text-on-surface-variant hover:text-primary transition-colors duration-150">
              Submit a Claim
            </button>
            <button type="button" onClick={() => setCurrentScreen('history')} className="font-body-md text-body-md pb-1 cursor-pointer text-on-surface-variant hover:text-primary transition-colors duration-150">
              Claim History
            </button>
            {userRole === 'reviewer' && (
              <button type="button" onClick={() => setCurrentScreen('review')} className="font-body-md text-body-md pb-1 cursor-pointer text-primary border-b-2 border-primary font-bold transition-colors duration-150">
                Review Queue
              </button>
            )}
          </nav>
          <button type="button" onClick={() => setAuthToken(null)} className="ml-auto font-body-md text-body-md text-primary cursor-pointer hover:text-on-surface-variant transition-all duration-150">
            Log Out
          </button>
        </div>
      </header>

      <main className="flex-grow w-full max-w-container-max mx-auto px-margin-desktop py-margin-desktop">
        <div className="mb-stack-lg">
          <h1 className="font-headline-md text-headline-md text-on-surface mb-unit">Review Queue</h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Claims escalated by the automated pipeline, awaiting a human decision.
          </p>
        </div>

        {error && <p className="mb-stack-md" style={{ color: '#9B1C1C' }}>{error}</p>}
        {loading && <p className="text-on-surface-variant">Loading queue...</p>}

        {!loading && queue.length === 0 && (
          <p className="text-on-surface-variant">Nothing pending review.</p>
        )}

        {!loading && queue.length > 0 && (
          <div className="w-full overflow-x-auto border border-[#E5E7EB]">
            <table className="w-full text-left border-collapse min-w-[800px]">
              <thead>
                <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant">Date</th>
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant">Policy</th>
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant">Type</th>
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant">Flagged For</th>
                  <th className="py-3 px-4 font-label-md text-label-md text-on-surface-variant text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="font-data-tabular text-data-tabular text-on-surface bg-surface-container-lowest">
                {queue.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => { setSelected(c); setNotes(''); }}
                    className={`border-b border-[#E5E7EB] hover:bg-surface-bright transition-colors cursor-pointer ${selected?.id === c.id ? 'bg-surface-bright' : ''}`}
                  >
                    <td className="py-3 px-4">{c.created_at?.slice(0, 10)}</td>
                    <td className="py-3 px-4">{c.policy_number || '-'}</td>
                    <td className="py-3 px-4 capitalize">{c.claim_type || '-'}</td>
                    <td className="py-3 px-4 text-sm">{c.fraud_reason || '-'}</td>
                    <td className="py-3 px-4 text-right">
                      {c.amount_requested != null ? `$${Number(c.amount_requested).toFixed(2)}` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selected && (
          <div className="mt-stack-lg border border-outline-variant p-stack-lg bg-surface-container-lowest">
            <h2 className="font-headline-sm text-headline-sm text-primary mb-stack-md">
              Reviewing claim #{selected.id}
            </h2>

            <div className="mb-stack-md">
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Pipeline assessment</span>
              <p className="font-body-md text-body-md text-on-surface mt-1">{selected.coverage_reasoning}</p>
            </div>

            <div className="mb-stack-md">
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Fraud flag</span>
              <p className="font-body-md text-body-md text-on-surface mt-1">{selected.fraud_reason || 'None'}</p>
            </div>

            <div className="mb-stack-md">
              <label className="block font-label-md text-label-md text-on-surface mb-stack-sm uppercase tracking-wider" htmlFor="notes">
                Reviewer notes
              </label>
              <textarea
                id="notes"
                rows="3"
                className="w-full border border-outline-variant p-stack-sm font-body-md text-body-md bg-surface-container-lowest text-on-surface"
                placeholder="Why are you approving or denying this?"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            <div className="flex gap-stack-md">
              <button
                type="button"
                disabled={submitting}
                onClick={() => resolve('approved')}
                className="px-6 py-2 font-label-md text-label-md cursor-pointer disabled:opacity-50"
                style={{ background: '#DEF7EC', color: '#03543F' }}
              >
                Approve
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={() => resolve('denied')}
                className="px-6 py-2 font-label-md text-label-md cursor-pointer disabled:opacity-50"
                style={{ background: '#FDE8E8', color: '#9B1C1C' }}
              >
                Deny
              </button>
              <button
                type="button"
                onClick={() => setSelected(null)}
                className="px-6 py-2 border border-outline-variant text-primary font-label-md text-label-md cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}